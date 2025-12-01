"""
Tests for Helm integration
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import with fallback for testing
try:
    from kcpwd.helm import (
        process_helm_template,
        process_helm_values_file,
        scan_values_for_kcpwd_refs,
        sync_helm_chart_secrets,
        generate_example_values,
        HelmError
    )

    HELM_AVAILABLE = True
except ImportError:
    HELM_AVAILABLE = False


@pytest.mark.skipif(not HELM_AVAILABLE, reason="Helm module not available")
class TestProcessHelmTemplate:
    """Tests for process_helm_template function"""

    def test_simple_password_replacement(self):
        """Test basic password replacement"""
        template = """
database:
  host: postgres
  password: "{{ kcpwd('db_password') }}"
"""

        with patch('kcpwd.helm._get_kcpwd_password', return_value='secret123'):
            result = process_helm_template(template)

        assert 'secret123' in result
        assert "{{ kcpwd('db_password') }}" not in result

    def test_multiple_passwords(self):
        """Test multiple password replacements"""
        template = """
database:
  password: "{{ kcpwd('db_password') }}"
redis:
  password: "{{ kcpwd('redis_password') }}"
api:
  key: "{{ kcpwd('api_key') }}"
"""

        def mock_get_password(key, *args, **kwargs):
            passwords = {
                'db_password': 'db_secret',
                'redis_password': 'redis_secret',
                'api_key': 'api_secret'
            }
            return passwords.get(key, 'default')

        with patch('kcpwd.helm._get_kcpwd_password', side_effect=mock_get_password):
            result = process_helm_template(template)

        assert 'db_secret' in result
        assert 'redis_secret' in result
        assert 'api_secret' in result

    def test_master_password_true(self):
        """Test master password with master=true syntax"""
        template = 'secret: "{{ kcpwd(\'prod_secret\', master=true) }}"'

        with patch('kcpwd.helm._get_kcpwd_password', return_value='master_protected') as mock:
            result = process_helm_template(template)

            # Verify it was called with use_master=True
            mock.assert_called_once()
            assert mock.call_args[1]['use_master'] == True

        assert 'master_protected' in result

    def test_master_password_inline(self):
        """Test master password with inline password"""
        template = 'secret: "{{ kcpwd(\'prod_secret\', master=\'mypass\') }}"'

        with patch('kcpwd.helm._get_kcpwd_password', return_value='secret') as mock:
            result = process_helm_template(template)

            # Verify it was called with master password
            assert mock.call_args[1]['master_password'] == 'mypass'

        assert 'secret' in result

    def test_kcpwd_get_alias(self):
        """Test kcpwd_get() alias"""
        template = 'password: "{{ kcpwd_get(\'db_password\') }}"'

        with patch('kcpwd.helm._get_kcpwd_password', return_value='secret'):
            result = process_helm_template(template)

        assert 'secret' in result

    def test_strict_mode_missing_password(self):
        """Test strict mode with missing password"""
        template = 'password: "{{ kcpwd(\'missing_key\') }}"'

        with patch('kcpwd.helm._get_kcpwd_password', side_effect=HelmError("Not found")):
            with pytest.raises(HelmError):
                process_helm_template(template, strict=True)

    def test_non_strict_mode_missing_password(self):
        """Test non-strict mode leaves template as-is"""
        template = 'password: "{{ kcpwd(\'missing_key\') }}"'

        with patch('kcpwd.helm._get_kcpwd_password', side_effect=HelmError("Not found")):
            result = process_helm_template(template, strict=False)

        # Template should be unchanged
        assert "{{ kcpwd('missing_key') }}" in result

    def test_whitespace_handling(self):
        """Test various whitespace patterns"""
        templates = [
            '{{kcpwd("key")}}',
            '{{ kcpwd("key") }}',
            '{{  kcpwd(  "key"  )  }}',
            "{{ kcpwd('key') }}",
        ]

        for template in templates:
            with patch('kcpwd.helm._get_kcpwd_password', return_value='secret'):
                result = process_helm_template(template)
                assert 'secret' in result


@pytest.mark.skipif(not HELM_AVAILABLE, reason="Helm module not available")
class TestProcessHelmValuesFile:
    """Tests for process_helm_values_file function"""

    def test_process_file_with_output(self):
        """Test processing file and writing output"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as input_file:
            input_file.write("""
database:
  password: "{{ kcpwd('db_password') }}"
""")
            input_path = input_file.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as output_file:
            output_path = output_file.name

        try:
            with patch('kcpwd.helm._get_kcpwd_password', return_value='secret123'):
                result = process_helm_values_file(input_path, output_path)

            # Check output file exists and contains processed values
            with open(output_path, 'r') as f:
                content = f.read()

            assert 'secret123' in content
            assert 'database' in content

            # Check returned dict
            assert 'database' in result
            assert result['database']['password'] == 'secret123'

        finally:
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)

    def test_process_file_no_output(self):
        """Test processing file without output (returns dict only)"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as input_file:
            input_file.write("""
api:
  key: "{{ kcpwd('api_key') }}"
""")
            input_path = input_file.name

        try:
            with patch('kcpwd.helm._get_kcpwd_password', return_value='my_api_key'):
                result = process_helm_values_file(input_path, output_file=None)

            assert 'api' in result
            assert result['api']['key'] == 'my_api_key'

        finally:
            Path(input_path).unlink(missing_ok=True)

    def test_invalid_yaml_validation(self):
        """Test YAML validation catches errors"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as input_file:
            input_file.write("""
invalid: yaml: syntax: here
  - bad indent
""")
            input_path = input_file.name

        try:
            with pytest.raises(HelmError, match="Invalid YAML"):
                process_helm_values_file(input_path, validate_yaml=True)
        finally:
            Path(input_path).unlink(missing_ok=True)

    def test_file_not_found(self):
        """Test error when input file doesn't exist"""
        with pytest.raises(HelmError, match="not found"):
            process_helm_values_file('/nonexistent/file.yaml')


@pytest.mark.skipif(not HELM_AVAILABLE, reason="Helm module not available")
class TestScanValuesForKcpwdRefs:
    """Tests for scan_values_for_kcpwd_refs function"""

    def test_scan_single_reference(self):
        """Test scanning single reference"""
        content = 'password: "{{ kcpwd(\'db_password\') }}"'

        refs = scan_values_for_kcpwd_refs(content)

        assert len(refs) == 1
        assert refs[0]['key'] == 'db_password'
        assert refs[0]['needs_master'] == False

    def test_scan_multiple_references(self):
        """Test scanning multiple references"""
        content = """
db: "{{ kcpwd('db_password') }}"
redis: "{{ kcpwd('redis_password') }}"
api: "{{ kcpwd('api_key') }}"
"""

        refs = scan_values_for_kcpwd_refs(content)

        assert len(refs) == 3
        keys = [ref['key'] for ref in refs]
        assert 'db_password' in keys
        assert 'redis_password' in keys
        assert 'api_key' in keys

    def test_scan_master_password_references(self):
        """Test scanning master password references"""
        content = """
normal: "{{ kcpwd('normal_key') }}"
master_bool: "{{ kcpwd('master_key', master=true) }}"
master_inline: "{{ kcpwd('master_key2', master='mypass') }}"
"""

        refs = scan_values_for_kcpwd_refs(content)

        assert len(refs) == 3

        # Check normal
        normal_ref = [r for r in refs if r['key'] == 'normal_key'][0]
        assert normal_ref['needs_master'] == False

        # Check master=true
        master_bool_ref = [r for r in refs if r['key'] == 'master_key'][0]
        assert master_bool_ref['needs_master'] == True
        assert master_bool_ref['master_inline'] is None

        # Check master='password'
        master_inline_ref = [r for r in refs if r['key'] == 'master_key2'][0]
        assert master_inline_ref['needs_master'] == True
        assert master_inline_ref['master_inline'] == 'mypass'

    def test_scan_no_references(self):
        """Test scanning content with no references"""
        content = """
database:
  host: postgres
  port: 5432
  name: myapp
"""

        refs = scan_values_for_kcpwd_refs(content)

        assert len(refs) == 0

    def test_scan_kcpwd_get_alias(self):
        """Test scanning kcpwd_get() alias"""
        content = 'password: "{{ kcpwd_get(\'my_password\') }}"'

        refs = scan_values_for_kcpwd_refs(content)

        assert len(refs) == 1
        assert refs[0]['key'] == 'my_password'


@pytest.mark.skipif(not HELM_AVAILABLE, reason="Helm module not available")
class TestSyncHelmChartSecrets:
    """Tests for sync_helm_chart_secrets function"""

    def test_sync_no_references(self):
        """Test sync when no kcpwd references found"""
        with tempfile.TemporaryDirectory() as temp_dir:
            chart_dir = Path(temp_dir)
            values_file = chart_dir / 'values.yaml'

            # Create values without kcpwd references
            with open(values_file, 'w') as f:
                f.write("""
database:
  host: postgres
  port: 5432
""")

            result = sync_helm_chart_secrets(str(chart_dir))

            assert result['success'] == True
            assert result['synced'] == 0
            assert len(result['references']) == 0

    def test_sync_with_references(self):
        """Test sync with kcpwd references"""
        with tempfile.TemporaryDirectory() as temp_dir:
            chart_dir = Path(temp_dir)
            values_file = chart_dir / 'values.yaml'

            # Create values with kcpwd references
            with open(values_file, 'w') as f:
                f.write("""
database:
  password: "{{ kcpwd('db_password') }}"
redis:
  password: "{{ kcpwd('redis_password') }}"
""")

            # Mock sync_to_k8s
            mock_sync_result = {
                'success': True,
                'k8s_secret': 'test-secret',
                'namespace': 'default'
            }

            with patch('kcpwd.helm.sync_to_k8s', return_value=mock_sync_result):
                result = sync_helm_chart_secrets(str(chart_dir))

            assert result['synced'] == 2
            assert result['failed'] == 0
            assert len(result['references']) == 2

    def test_sync_with_release_name(self):
        """Test sync with release name (for secret naming)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            chart_dir = Path(temp_dir)
            values_file = chart_dir / 'values.yaml'

            with open(values_file, 'w') as f:
                f.write('password: "{{ kcpwd(\'my_password\') }}"')

            mock_sync = MagicMock(return_value={
                'success': True,
                'k8s_secret': 'myapp-my-password',
                'namespace': 'default'
            })

            with patch('kcpwd.helm.sync_to_k8s', mock_sync):
                result = sync_helm_chart_secrets(
                    str(chart_dir),
                    release_name='myapp'
                )

                # Verify sync_to_k8s was called with correct secret name
                call_args = mock_sync.call_args
                assert 'myapp-my-password' in str(call_args)

    def test_sync_handles_errors(self):
        """Test sync handles errors gracefully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            chart_dir = Path(temp_dir)
            values_file = chart_dir / 'values.yaml'

            with open(values_file, 'w') as f:
                f.write("""
db: "{{ kcpwd('db_password') }}"
redis: "{{ kcpwd('redis_password') }}"
""")

            # Mock one success, one failure
            def mock_sync(key, **kwargs):
                if key == 'db_password':
                    return {'success': True, 'k8s_secret': 'db', 'namespace': 'default'}
                else:
                    raise Exception("Sync failed")

            with patch('kcpwd.helm.sync_to_k8s', side_effect=mock_sync):
                result = sync_helm_chart_secrets(str(chart_dir))

            assert result['synced'] == 1
            assert result['failed'] == 1
            assert len(result['errors']) == 1


@pytest.mark.skipif(not HELM_AVAILABLE, reason="Helm module not available")
class TestGenerateExampleValues:
    """Tests for generate_example_values function"""

    def test_example_is_valid_yaml(self):
        """Test generated example is valid YAML"""
        example = generate_example_values()

        # Should be parseable as YAML
        parsed = yaml.safe_load(example)

        assert isinstance(parsed, dict)
        assert 'database' in parsed

    def test_example_contains_kcpwd_refs(self):
        """Test example contains kcpwd references"""
        example = generate_example_values()

        # Should contain kcpwd() calls
        assert 'kcpwd(' in example

        # Should have various examples
        assert 'master=true' in example
        assert 'master=' in example


@pytest.mark.skipif(not HELM_AVAILABLE, reason="Helm module not available")
class TestHelmPluginGeneration:
    """Tests for Helm plugin generation"""

    def test_plugin_yaml_generation(self):
        """Test plugin.yaml generation"""
        from kcpwd.helm import create_helm_plugin_yaml

        plugin_yaml = create_helm_plugin_yaml()

        assert 'name: "kcpwd"' in plugin_yaml
        assert 'version:' in plugin_yaml

        # Should be valid YAML
        parsed = yaml.safe_load(plugin_yaml)
        assert parsed['name'] == 'kcpwd'

    def test_plugin_script_generation(self):
        """Test plugin script generation"""
        from kcpwd.helm import create_helm_plugin_script

        script = create_helm_plugin_script()

        assert '#!/usr/bin/env bash' in script
        assert 'template)' in script
        assert 'sync)' in script
        assert 'scan)' in script

    def test_plugin_package_generation(self):
        """Test complete plugin package generation"""
        from kcpwd.helm import create_helm_plugin_package

        package = create_helm_plugin_package()

        assert 'plugin.yaml' in package
        assert 'kcpwd-helm.sh' in package
        assert 'README.md' in package

        # All files should have content
        for filename, content in package.items():
            assert len(content) > 0


# Integration test (requires kcpwd to be installed)
@pytest.mark.skipif(not HELM_AVAILABLE, reason="Helm module not available")
@pytest.mark.integration
class TestHelmIntegration:
    """Integration tests (require real kcpwd installation)"""

    def test_end_to_end_workflow(self):
        """Test complete workflow: set password → process values"""
        from kcpwd import set_password

        # Setup
        test_key = 'test_helm_password'
        test_value = 'test_secret_123'

        try:
            # Store password
            set_password(test_key, test_value)

            # Create temp values file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(f'password: "{{{{ kcpwd(\'{test_key}\') }}}}"')
                values_path = f.name

            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                output_path = f.name

            # Process
            result = process_helm_values_file(values_path, output_path)

            # Verify
            assert result['password'] == test_value

            with open(output_path, 'r') as f:
                content = f.read()

            assert test_value in content

        finally:
            # Cleanup
            from kcpwd import delete_password
            delete_password(test_key)
            Path(values_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])