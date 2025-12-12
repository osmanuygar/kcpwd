"""
kcpwd.helm - Helm Values Integration
Enables using kcpwd passwords directly in Helm values.yaml files

Two approaches:
1. Template processor - Pre-process values.yaml
2. Helm plugin - Native Helm integration

Usage:
    # Template approach
    kcpwd helm template values.yaml -o values-with-secrets.yaml

    # Plugin approach (via helm-kcpwd plugin)
    helm template myapp ./chart --kcpwd-fetch
"""

import re
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
import getpass


class HelmError(Exception):
    """Helm integration error"""
    pass


def _get_kcpwd_password(key: str, use_master: bool = False, master_password: Optional[str] = None) -> str:
    """Get password from kcpwd

    Args:
        key: Password key
        use_master: Whether to use master password
        master_password: Master password if needed

    Returns:
        Password string

    Raises:
        HelmError: If password not found
    """
    from .core import get_password
    from .master_protection import get_master_password, has_master_password

    if has_master_password(key) or use_master:
        if not master_password:
            master_password = getpass.getpass(f"Enter master password for '{key}': ")
        password = get_master_password(key, master_password)
    else:
        password = get_password(key)

    if password is None:
        raise HelmError(f"Password '{key}' not found in kcpwd")

    return password


def process_helm_template(
    values_content: str,
    master_passwords: Optional[Dict[str, str]] = None,
    strict: bool = True
) -> str:
    """Process Helm values template and replace kcpwd references

    Supports these syntaxes:
    - {{ kcpwd('key') }}
    - {{ kcpwd_get('key') }}
    - {{ kcpwd('key', master='password') }}
    - {{ kcpwd('key', master=true) }}  # Will prompt

    Args:
        values_content: YAML content as string
        master_passwords: Dict of key -> master_password mappings
        strict: If True, fail on missing passwords. If False, leave template as-is

    Returns:
        Processed YAML content
    """
    master_passwords = master_passwords or {}

    # Pattern to match kcpwd() and kcpwd_get() calls
    # Matches: {{ kcpwd('key') }}, {{ kcpwd_get('key') }}, etc.
    pattern = r"{{\s*kcpwd(?:_get)?\s*\(\s*['\"]([^'\"]+)['\"]\s*(?:,\s*master\s*=\s*(?:['\"]([^'\"]+)['\"]|true))?\s*\)\s*}}"

    def replace_func(match):
        key = match.group(1)
        master_arg = match.group(2)  # Can be password string or None

        try:
            # Determine if master password is needed
            use_master = master_arg is not None
            master_password = None

            if use_master:
                # If master_arg is set, it's either the password or 'true'
                if master_arg and master_arg != 'true':
                    master_password = master_arg
                elif key in master_passwords:
                    master_password = master_passwords[key]
                # else: will prompt in _get_kcpwd_password

            password = _get_kcpwd_password(key, use_master, master_password)
            return password

        except HelmError as e:
            if strict:
                raise
            else:
                # Leave template as-is
                return match.group(0)

    processed = re.sub(pattern, replace_func, values_content)
    return processed


def process_helm_values_file(
    input_file: str,
    output_file: Optional[str] = None,
    master_passwords: Optional[Dict[str, str]] = None,
    strict: bool = True,
    validate_yaml: bool = True
) -> Dict[str, Any]:
    """Process Helm values file and replace kcpwd references

    Args:
        input_file: Input values.yaml file path
        output_file: Output file path (if None, returns dict only)
        master_passwords: Dict of key -> master_password mappings
        strict: If True, fail on missing passwords
        validate_yaml: If True, validate YAML syntax

    Returns:
        Processed values as dictionary
    """
    input_path = Path(input_file)

    if not input_path.exists():
        raise HelmError(f"Input file not found: {input_file}")

    # Read input
    with open(input_path, 'r') as f:
        content = f.read()

    # Process template
    processed_content = process_helm_template(content, master_passwords, strict)

    # Validate YAML if requested
    if validate_yaml:
        try:
            processed_values = yaml.safe_load(processed_content)
        except yaml.YAMLError as e:
            raise HelmError(f"Invalid YAML after processing: {e}")
    else:
        processed_values = {}

    # Write output if specified
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(processed_content)

    return yaml.safe_load(processed_content) if validate_yaml else {}


def scan_values_for_kcpwd_refs(values_content: str) -> List[Dict[str, Any]]:
    """Scan Helm values for kcpwd references

    Args:
        values_content: YAML content as string

    Returns:
        List of found references with details
    """
    pattern = r"{{\s*kcpwd(?:_get)?\s*\(\s*['\"]([^'\"]+)['\"]\s*(?:,\s*master\s*=\s*(?:['\"]([^'\"]+)['\"]|true))?\s*\)\s*}}"

    references = []
    for match in re.finditer(pattern, values_content):
        key = match.group(1)
        master_arg = match.group(2)

        references.append({
            'key': key,
            'needs_master': master_arg is not None,
            'master_inline': master_arg if master_arg and master_arg != 'true' else None,
            'full_match': match.group(0),
            'position': match.span()
        })

    return references


def generate_example_values() -> str:
    """Generate example Helm values with kcpwd integration

    Returns:
        Example YAML content
    """
    example = """# Helm values.yaml with kcpwd integration
# Process with: kcpwd helm template values.yaml -o values-processed.yaml

# Simple password reference
database:
  host: postgres.example.com
  port: 5432
  name: myapp
  # kcpwd will fetch this password
  password: "{{ kcpwd('db_password') }}"
  
# Master-protected password with inline master password
api:
  endpoint: https://api.example.com
  # Using master password (inline - not recommended for production)
  key: "{{ kcpwd('api_key', master='my_master_pass') }}"
  
# Master-protected password (will prompt)
production:
  secret: "{{ kcpwd('prod_secret', master=true) }}"

# Multiple passwords
redis:
  host: redis.example.com
  password: "{{ kcpwd('redis_password') }}"
  
cache:
  host: memcached.example.com
  password: "{{ kcpwd('cache_password') }}"

# Can be used anywhere in YAML
jwt:
  secret: "{{ kcpwd('jwt_secret') }}"
  issuer: "myapp"
  
encryption:
  key: "{{ kcpwd('encryption_key') }}"
  algorithm: "AES256"

# Nested structures work too
services:
  auth:
    credentials:
      client_id: "my-app"
      client_secret: "{{ kcpwd('oauth_client_secret') }}"
"""
    return example


def sync_helm_chart_secrets(
    chart_dir: str,
    namespace: str = "default",
    values_file: str = "values.yaml",
    release_name: Optional[str] = None,
    kubeconfig: Optional[str] = None
) -> Dict[str, Any]:
    """Scan Helm chart values and sync all kcpwd refs to K8s secrets

    This is useful for GitOps workflows where you want to:
    1. Keep passwords in kcpwd
    2. Reference them in Helm values
    3. Auto-sync them to K8s secrets

    Args:
        chart_dir: Path to Helm chart directory
        namespace: K8s namespace
        values_file: Values file name (relative to chart_dir)
        release_name: Helm release name (for naming secrets)
        kubeconfig: Path to kubeconfig

    Returns:
        Sync results
    """
    from .k8s import sync_to_k8s

    chart_path = Path(chart_dir)
    values_path = chart_path / values_file

    if not values_path.exists():
        raise HelmError(f"Values file not found: {values_path}")

    # Read values
    with open(values_path, 'r') as f:
        content = f.read()

    # Find all kcpwd references
    refs = scan_values_for_kcpwd_refs(content)

    if not refs:
        return {
            "success": True,
            "message": "No kcpwd references found",
            "synced": 0,
            "references": []
        }

    # Sync each referenced password to K8s
    results = {
        "success": True,
        "synced": 0,
        "failed": 0,
        "references": [],
        "errors": []
    }

    for ref in refs:
        key = ref['key']

        # Generate secret name
        if release_name:
            secret_name = f"{release_name}-{key.replace('_', '-')}"
        else:
            secret_name = key.replace('_', '-')

        try:
            result = sync_to_k8s(
                key=key,
                namespace=namespace,
                secret_name=secret_name,
                kubeconfig=kubeconfig,
                create_if_missing=True
            )

            results["synced"] += 1
            results["references"].append({
                "key": key,
                "secret_name": result["k8s_secret"],
                "namespace": namespace,
                "status": "synced"
            })

        except Exception as e:
            results["failed"] += 1
            results["success"] = False
            results["errors"].append({
                "key": key,
                "error": str(e)
            })

    return results


def create_helm_plugin_yaml() -> str:
    """Generate plugin.yaml for Helm plugin

    Returns:
        plugin.yaml content
    """
    plugin_yaml = """name: "kcpwd"
version: "0.8.1"
usage: "Fetch secrets from kcpwd password manager"
description: |-
  Helm plugin to integrate with kcpwd password manager.
  Automatically fetches passwords from kcpwd during helm install/upgrade.
  
  Usage:
    helm kcpwd template ./chart
    helm install myapp ./chart --kcpwd-fetch
    
command: "$HELM_PLUGIN_DIR/kcpwd-helm.sh"
hooks:
  install: "cd $HELM_PLUGIN_DIR; chmod +x kcpwd-helm.sh"
"""
    return plugin_yaml


def create_helm_plugin_script() -> str:
    """Generate shell script for Helm plugin

    Returns:
        Shell script content
    """
    script = """#!/usr/bin/env bash
# Helm kcpwd plugin script

set -e

# Colors
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

# Check if kcpwd is installed
if ! command -v kcpwd &> /dev/null; then
    echo -e "${RED}Error: kcpwd is not installed${NC}"
    echo "Install with: pip install kcpwd"
    exit 1
fi

# Parse command
COMMAND="$1"
shift

case "$COMMAND" in
    template)
        VALUES_FILE="${1:-values.yaml}"
        OUTPUT_FILE="${2:-values-processed.yaml}"
        
        echo -e "${GREEN}Processing Helm values with kcpwd...${NC}"
        kcpwd helm template "$VALUES_FILE" -o "$OUTPUT_FILE"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Values processed: $OUTPUT_FILE${NC}"
        else
            echo -e "${RED}✗ Failed to process values${NC}"
            exit 1
        fi
        ;;
    
    sync)
        CHART_DIR="${1:-.}"
        NAMESPACE="${2:-default}"
        
        echo -e "${GREEN}Syncing kcpwd passwords to K8s...${NC}"
        kcpwd helm sync "$CHART_DIR" --namespace "$NAMESPACE"
        ;;
    
    scan)
        VALUES_FILE="${1:-values.yaml}"
        
        echo -e "${GREEN}Scanning for kcpwd references...${NC}"
        kcpwd helm scan "$VALUES_FILE"
        ;;
    
    *)
        echo "Helm kcpwd plugin"
        echo ""
        echo "Commands:"
        echo "  template <values.yaml> [output.yaml]  - Process values file"
        echo "  sync <chart-dir> [namespace]          - Sync passwords to K8s"
        echo "  scan <values.yaml>                    - Scan for kcpwd refs"
        echo ""
        echo "Examples:"
        echo "  helm kcpwd template values.yaml"
        echo "  helm kcpwd sync ./mychart production"
        echo "  helm kcpwd scan values.yaml"
        exit 1
        ;;
esac
"""
    return script


def create_helm_plugin_package() -> Dict[str, str]:
    """Create complete Helm plugin package

    Returns:
        Dictionary with filename -> content mappings
    """
    return {
        "plugin.yaml": create_helm_plugin_yaml(),
        "kcpwd-helm.sh": create_helm_plugin_script(),
        "README.md": """# Helm kcpwd Plugin

Integrate kcpwd password manager with Helm.

## Installation

```bash
helm plugin install https://github.com/osmanuygar/helm-kcpwd
```

## Usage

### Process values file
```bash
helm kcpwd template values.yaml values-processed.yaml
```

### Sync passwords to K8s
```bash
helm kcpwd sync ./mychart production
```

### Scan for references
```bash
helm kcpwd scan values.yaml
```

## Values Syntax

```yaml
database:
  password: "{{ kcpwd('db_password') }}"
  
api:
  key: "{{ kcpwd('api_key', master=true) }}"
```

## More Info

See: https://github.com/osmanuygar/kcpwd
"""
    }