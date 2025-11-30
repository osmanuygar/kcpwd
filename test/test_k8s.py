"""
Tests for Kubernetes integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from kcpwd.k8s import (
    K8sClient,
    K8sError,
    sync_to_k8s,
    sync_all_to_k8s,
    import_from_k8s,
    list_k8s_secrets,
    delete_k8s_secret
)


class TestK8sClient:
    """Test K8sClient class"""

    def test_init_default(self):
        """Test default initialization"""
        with patch('kcpwd.k8s.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='Client Version: v1.28.0')

            client = K8sClient()
            assert client.namespace == "default"
            assert client.kubeconfig is None

    def test_init_custom_namespace(self):
        """Test initialization with custom namespace"""
        with patch('kcpwd.k8s.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            client = K8sClient(namespace="production")
            assert client.namespace == "production"

    def test_kubectl_not_found(self):
        """Test error when kubectl not found"""
        with patch('kcpwd.k8s.subprocess.run', side_effect=FileNotFoundError):
            with pytest.raises(K8sError, match="kubectl not installed"):
                K8sClient()

    def test_secret_exists_true(self):
        """Test secret_exists when secret exists"""
        with patch('kcpwd.k8s.subprocess.run') as mock_run:
            # Setup: kubectl version succeeds, get secret succeeds
            mock_run.side_effect = [
                Mock(returncode=0),  # version check
                Mock(returncode=0)  # get secret
            ]

            client = K8sClient()
            assert client.secret_exists("test-secret") is True

    def test_secret_exists_false(self):
        """Test secret_exists when secret doesn't exist"""
        with patch('kcpwd.k8s.subprocess.run') as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0),  # version check
                Mock(returncode=1)  # get secret fails
            ]

            client = K8sClient()
            assert client.secret_exists("missing-secret") is False

    def test_create_secret(self):
        """Test creating a secret"""
        with patch('kcpwd.k8s.subprocess.run') as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0),  # version check
                Mock(returncode=0, stdout='secret/test created')  # create
            ]

            client = K8sClient()
            result = client.create_secret(
                "test-secret",
                {"password": "test123"},
                labels={"app": "myapp"}
            )

            assert result is True

    def test_get_secret(self):
        """Test getting a secret"""
        with patch('kcpwd.k8s.subprocess.run') as mock_run:
            secret_json = '''
            {
                "data": {
                    "password": "dGVzdDEyMw==",
                    "username": "YWRtaW4="
                }
            }
            '''

            mock_run.side_effect = [
                Mock(returncode=0),  # version check
                Mock(returncode=0, stdout=secret_json)  # get secret
            ]

            client = K8sClient()
            data = client.get_secret("test-secret")

            assert data is not None
            assert data["password"] == "test123"
            assert data["username"] == "admin"

    def test_get_secret_not_found(self):
        """Test getting non-existent secret"""
        with patch('kcpwd.k8s.subprocess.run') as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0),  # version check
                Mock(returncode=1, stderr="NotFound")  # get fails
            ]

            client = K8sClient()
            data = client.get_secret("missing")

            assert data is None

    def test_delete_secret(self):
        """Test deleting a secret"""
        with patch('kcpwd.k8s.subprocess.run') as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0),  # version check
                Mock(returncode=0, stdout='secret "test" deleted')  # delete
            ]

            client = K8sClient()
            result = client.delete_secret("test-secret")

            assert result is True

    def test_list_secrets(self):
        """Test listing secrets"""
        with patch('kcpwd.k8s.subprocess.run') as mock_run:
            secrets_json = '''
            {
                "items": [
                    {"metadata": {"name": "secret1"}},
                    {"metadata": {"name": "secret2"}}
                ]
            }
            '''

            mock_run.side_effect = [
                Mock(returncode=0),  # version check
                Mock(returncode=0, stdout=secrets_json)  # list
            ]

            client = K8sClient()
            secrets = client.list_secrets()

            assert len(secrets) == 2
            assert "secret1" in secrets
            assert "secret2" in secrets


class TestSyncToK8s:
    """Test sync_to_k8s function"""

    @patch('kcpwd.k8s.K8sClient')
    @patch('kcpwd.k8s.get_password')
    @patch('kcpwd.k8s.has_master_password')
    def test_sync_regular_password(self, mock_has_master, mock_get_pass, mock_client_class):
        """Test syncing regular password"""
        # Setup
        mock_has_master.return_value = False
        mock_get_pass.return_value = "test_password"

        mock_client = Mock()
        mock_client.secret_exists.return_value = False
        mock_client.create_secret.return_value = True
        mock_client_class.return_value = mock_client

        # Execute
        result = sync_to_k8s("test_key", namespace="default")

        # Assert
        assert result["success"] is True
        assert result["action"] == "created"
        assert result["kcpwd_key"] == "test_key"
        assert result["k8s_secret"] == "test-key"

        mock_client.create_secret.assert_called_once()

    @patch('kcpwd.k8s.K8sClient')
    @patch('kcpwd.k8s.get_master_password')
    @patch('kcpwd.k8s.has_master_password')
    def test_sync_master_protected(self, mock_has_master, mock_get_master, mock_client_class):
        """Test syncing master-protected password"""
        # Setup
        mock_has_master.return_value = True
        mock_get_master.return_value = "secure_password"

        mock_client = Mock()
        mock_client.secret_exists.return_value = True
        mock_client.update_secret.return_value = True
        mock_client_class.return_value = mock_client

        # Execute
        result = sync_to_k8s(
            "prod_key",
            namespace="production",
            master_password="master123"
        )

        # Assert
        assert result["success"] is True
        assert result["action"] == "updated"

        mock_get_master.assert_called_once_with("prod_key", "master123")
        mock_client.update_secret.assert_called_once()

    @patch('kcpwd.k8s.get_password')
    @patch('kcpwd.k8s.has_master_password')
    def test_sync_password_not_found(self, mock_has_master, mock_get_pass):
        """Test syncing non-existent password"""
        mock_has_master.return_value = False
        mock_get_pass.return_value = None

        with pytest.raises(K8sError, match="not found in kcpwd"):
            sync_to_k8s("missing_key")

    @patch('kcpwd.k8s.K8sClient')
    @patch('kcpwd.k8s.get_password')
    @patch('kcpwd.k8s.has_master_password')
    def test_sync_custom_names(self, mock_has_master, mock_get_pass, mock_client_class):
        """Test syncing with custom secret and key names"""
        mock_has_master.return_value = False
        mock_get_pass.return_value = "password"

        mock_client = Mock()
        mock_client.secret_exists.return_value = False
        mock_client.create_secret.return_value = True
        mock_client_class.return_value = mock_client

        result = sync_to_k8s(
            "my_key",
            secret_name="custom-secret",
            secret_key="custom_password"
        )

        assert result["k8s_secret"] == "custom-secret"
        assert result["secret_key"] == "custom_password"


class TestSyncAllToK8s:
    """Test sync_all_to_k8s function"""

    @patch('kcpwd.k8s.sync_to_k8s')
    @patch('kcpwd.k8s.list_master_keys')
    @patch('kcpwd.k8s.list_all_keys')
    def test_sync_all_success(self, mock_list_keys, mock_list_master, mock_sync):
        """Test syncing all passwords successfully"""
        # Setup
        mock_list_keys.return_value = ["key1", "key2", "key3"]
        mock_list_master.return_value = []
        mock_sync.return_value = {"success": True, "k8s_secret": "test"}

        # Execute
        result = sync_all_to_k8s(namespace="default")

        # Assert
        assert result["total"] == 3
        assert result["synced"] == 3
        assert result["failed"] == 0
        assert len(result["errors"]) == 0

    @patch('kcpwd.k8s.sync_to_k8s')
    @patch('kcpwd.k8s.list_master_keys')
    @patch('kcpwd.k8s.list_all_keys')
    def test_sync_all_with_failures(self, mock_list_keys, mock_list_master, mock_sync):
        """Test syncing all with some failures"""
        mock_list_keys.return_value = ["key1", "key2"]
        mock_list_master.return_value = []

        # First succeeds, second fails
        mock_sync.side_effect = [
            {"success": True, "k8s_secret": "key1"},
            K8sError("Failed to sync")
        ]

        result = sync_all_to_k8s()

        assert result["total"] == 2
        assert result["synced"] == 1
        assert result["failed"] == 1
        assert len(result["errors"]) == 1

    @patch('kcpwd.k8s.sync_to_k8s')
    @patch('kcpwd.k8s.list_master_keys')
    @patch('kcpwd.k8s.list_all_keys')
    def test_sync_all_with_prefix(self, mock_list_keys, mock_list_master, mock_sync):
        """Test syncing with prefix filter"""
        mock_list_keys.return_value = ["prod_db", "prod_api", "dev_db"]
        mock_list_master.return_value = []
        mock_sync.return_value = {"success": True, "k8s_secret": "test"}

        result = sync_all_to_k8s(prefix="prod_")

        assert result["total"] == 2  # Only prod_ keys
        assert mock_sync.call_count == 2


class TestImportFromK8s:
    """Test import_from_k8s function"""

    @patch('kcpwd.k8s.K8sClient')
    @patch('kcpwd.k8s.set_password')
    @patch('kcpwd.k8s.get_password')
    @patch('kcpwd.k8s.has_master_password')
    def test_import_success(self, mock_has_master, mock_get, mock_set, mock_client_class):
        """Test successful import"""
        # Setup
        mock_has_master.return_value = False
        mock_get.return_value = None  # Doesn't exist
        mock_set.return_value = True

        mock_client = Mock()
        mock_client.get_secret.return_value = {"password": "imported_pass"}
        mock_client_class.return_value = mock_client

        # Execute
        result = import_from_k8s("test-secret", namespace="default")

        # Assert
        assert result["success"] is True
        assert result["k8s_secret"] == "test-secret"
        assert result["kcpwd_key"] == "test_secret"

        mock_set.assert_called_once_with("test_secret", "imported_pass")

    @patch('kcpwd.k8s.K8sClient')
    def test_import_secret_not_found(self, mock_client_class):
        """Test importing non-existent secret"""
        mock_client = Mock()
        mock_client.get_secret.return_value = None
        mock_client_class.return_value = mock_client

        with pytest.raises(K8sError, match="not found"):
            import_from_k8s("missing-secret")

    @patch('kcpwd.k8s.K8sClient')
    @patch('kcpwd.k8s.get_password')
    @patch('kcpwd.k8s.has_master_password')
    def test_import_overwrite_protection(self, mock_has_master, mock_get, mock_client_class):
        """Test overwrite protection"""
        mock_has_master.return_value = False
        mock_get.return_value = "existing"  # Already exists

        mock_client = Mock()
        mock_client.get_secret.return_value = {"password": "new"}
        mock_client_class.return_value = mock_client

        with pytest.raises(K8sError, match="already exists"):
            import_from_k8s("test-secret", overwrite=False)

    @patch('kcpwd.k8s.K8sClient')
    @patch('kcpwd.k8s.set_master_password')
    @patch('kcpwd.k8s.get_password')
    @patch('kcpwd.k8s.has_master_password')
    def test_import_with_master_password(self, mock_has_master, mock_get, mock_set_master, mock_client_class):
        """Test importing with master password"""
        mock_has_master.return_value = False
        mock_get.return_value = None
        mock_set_master.return_value = True

        mock_client = Mock()
        mock_client.get_secret.return_value = {"password": "secure"}
        mock_client_class.return_value = mock_client

        result = import_from_k8s(
            "test-secret",
            use_master=True,
            master_password="master123"
        )

        assert result["master_protected"] is True
        mock_set_master.assert_called_once()


class TestListK8sSecrets:
    """Test list_k8s_secrets function"""

    @patch('kcpwd.k8s.K8sClient')
    def test_list_all_secrets(self, mock_client_class):
        """Test listing all secrets"""
        mock_client = Mock()
        mock_client.list_secrets.return_value = ["secret1", "secret2"]
        mock_client.get_secret.side_effect = [
            {"password": "pass1"},
            {"password": "pass2", "username": "user2"}
        ]
        mock_client_class.return_value = mock_client

        secrets = list_k8s_secrets(namespace="default")

        assert len(secrets) == 2
        assert secrets[0]["name"] == "secret1"
        assert secrets[0]["key_count"] == 1
        assert secrets[1]["name"] == "secret2"
        assert secrets[1]["key_count"] == 2

    @patch('kcpwd.k8s.K8sClient')
    def test_list_managed_only(self, mock_client_class):
        """Test listing only kcpwd-managed secrets"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        list_k8s_secrets(managed_only=True)

        # Verify labels parameter was passed
        mock_client.list_secrets.assert_called_once()
        call_args = mock_client.list_secrets.call_args
        assert call_args[1]["labels"] == {"app.kubernetes.io/managed-by": "kcpwd"}


class TestDeleteK8sSecret:
    """Test delete_k8s_secret function"""

    @patch('kcpwd.k8s.K8sClient')
    def test_delete_success(self, mock_client_class):
        """Test successful deletion"""
        mock_client = Mock()
        mock_client.delete_secret.return_value = True
        mock_client_class.return_value = mock_client

        result = delete_k8s_secret("test-secret", namespace="production")

        assert result is True
        mock_client.delete_secret.assert_called_once_with("test-secret")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])