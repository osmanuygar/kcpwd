"""
kcpwd.k8s - Kubernetes Secret Management Integration (FIXED)
Native Kubernetes support for syncing passwords to/from K8s secrets
"""

import base64
import json
import subprocess
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import getpass


class K8sError(Exception):
    """Kubernetes operation error"""
    pass


class K8sClient:
    """Kubernetes client for secret management"""

    def __init__(self, namespace: str = "default", kubeconfig: Optional[str] = None):
        """Initialize K8s client

        Args:
            namespace: Kubernetes namespace
            kubeconfig: Path to kubeconfig file (uses default if None)
        """
        self.namespace = namespace
        self.kubeconfig = kubeconfig
        self._verify_kubectl()

    def _verify_kubectl(self):
        """Verify kubectl is available"""
        try:
            result = subprocess.run(
                ['kubectl', 'version', '--client', '--short'],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                raise K8sError("kubectl not found or not working")
        except FileNotFoundError:
            raise K8sError("kubectl not installed. Install from: https://kubernetes.io/docs/tasks/tools/")
        except subprocess.TimeoutExpired:
            raise K8sError("kubectl command timed out")

    def _kubectl_cmd(self, *args, input=None) -> Tuple[int, str, str]:
        """Run kubectl command

        Returns:
            (returncode, stdout, stderr)
        """
        cmd = ['kubectl']

        if self.kubeconfig:
            cmd.extend(['--kubeconfig', self.kubeconfig])

        cmd.extend(['-n', self.namespace])
        cmd.extend(args)

        try:
            kwargs = {
                'capture_output': True,
                'text': True,
                'timeout': 30
            }

            if input:
                kwargs['input'] = input

            result = subprocess.run(cmd, **kwargs)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            raise K8sError(f"kubectl command timed out: {' '.join(args)}")
        except Exception as e:
            raise K8sError(f"kubectl command failed: {e}")

    def secret_exists(self, name: str) -> bool:
        """Check if secret exists - more robust implementation"""
        code, stdout, _ = self._kubectl_cmd('get', 'secret', name, '-o', 'name', '--ignore-not-found')
        # Secret exists if we got output and return code is 0
        return code == 0 and stdout.strip() != ""

    def create_secret(
        self,
        name: str,
        data: Dict[str, str],
        labels: Optional[Dict[str, str]] = None,
        secret_type: str = "Opaque"
    ) -> bool:
        """Create Kubernetes secret

        Args:
            name: Secret name
            data: Dictionary of key-value pairs (values will be base64 encoded)
            labels: Optional labels
            secret_type: Secret type (default: Opaque)

        Returns:
            True if successful

        Raises:
            K8sError: If creation fails
        """
        # Build secret manifest
        manifest = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": name,
                "namespace": self.namespace,
                "labels": labels or {},
            },
            "type": secret_type,
            "data": {}
        }

        # Add managed-by label
        manifest["metadata"]["labels"]["app.kubernetes.io/managed-by"] = "kcpwd"
        manifest["metadata"]["labels"]["kcpwd.io/synced"] = "true"

        # Base64 encode all values
        for key, value in data.items():
            encoded = base64.b64encode(value.encode('utf-8')).decode('utf-8')
            manifest["data"][key] = encoded

        # Apply manifest
        manifest_json = json.dumps(manifest)
        code, stdout, stderr = self._kubectl_cmd('apply', '-f', '-', input=manifest_json)

        if code != 0:
            # Check if it's because secret already exists
            if "AlreadyExists" in stderr or "already exists" in stderr:
                raise K8sError(f"Secret '{name}' already exists")
            raise K8sError(f"Failed to create secret: {stderr}")

        return True

    def update_secret(self, name: str, data: Dict[str, str]) -> bool:
        """Update existing secret - simplified without exists check"""
        # Get existing secret
        code, stdout, stderr = self._kubectl_cmd('get', 'secret', name, '-o', 'json')

        if code != 0:
            raise K8sError(f"Failed to get secret '{name}': {stderr}")

        try:
            existing = json.loads(stdout)
        except json.JSONDecodeError:
            raise K8sError("Failed to parse secret JSON")

        # Update data
        if "data" not in existing:
            existing["data"] = {}

        for key, value in data.items():
            encoded = base64.b64encode(value.encode('utf-8')).decode('utf-8')
            existing["data"][key] = encoded

        # Update timestamp
        if "metadata" not in existing:
            existing["metadata"] = {}
        if "annotations" not in existing["metadata"]:
            existing["metadata"]["annotations"] = {}

        existing["metadata"]["annotations"]["kcpwd.io/last-updated"] = datetime.now().isoformat()

        # Apply updated manifest
        manifest_json = json.dumps(existing)
        code, stdout, stderr = self._kubectl_cmd('apply', '-f', '-', input=manifest_json)

        if code != 0:
            raise K8sError(f"Failed to update secret: {stderr}")

        return True

    def get_secret(self, name: str) -> Optional[Dict[str, str]]:
        """Get secret data

        Returns:
            Dictionary of decoded key-value pairs, or None if not found
        """
        code, stdout, stderr = self._kubectl_cmd('get', 'secret', name, '-o', 'json')

        if code != 0:
            return None

        try:
            secret = json.loads(stdout)
            data = secret.get('data', {})

            # Decode all values
            decoded = {}
            for key, encoded_value in data.items():
                decoded_value = base64.b64decode(encoded_value).decode('utf-8')
                decoded[key] = decoded_value

            return decoded
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise K8sError(f"Failed to parse secret: {e}")

    def delete_secret(self, name: str) -> bool:
        """Delete secret"""
        code, stdout, stderr = self._kubectl_cmd('delete', 'secret', name, '--ignore-not-found')

        if code != 0:
            raise K8sError(f"Failed to delete secret: {stderr}")

        return True

    def list_secrets(self, labels: Optional[Dict[str, str]] = None) -> List[str]:
        """List secrets in namespace

        Args:
            labels: Filter by labels

        Returns:
            List of secret names
        """
        cmd_args = ['get', 'secrets', '-o', 'json']

        if labels:
            label_selector = ','.join([f"{k}={v}" for k, v in labels.items()])
            cmd_args.extend(['-l', label_selector])

        code, stdout, stderr = self._kubectl_cmd(*cmd_args)

        if code != 0:
            raise K8sError(f"Failed to list secrets: {stderr}")

        try:
            result = json.loads(stdout)
            items = result.get('items', [])
            return [item['metadata']['name'] for item in items]
        except (json.JSONDecodeError, KeyError) as e:
            raise K8sError(f"Failed to parse secrets list: {e}")


def sync_to_k8s(
    key: str,
    namespace: str = "default",
    secret_name: Optional[str] = None,
    secret_key: Optional[str] = None,
    master_password: Optional[str] = None,
    labels: Optional[Dict[str, str]] = None,
    kubeconfig: Optional[str] = None,
    create_if_missing: bool = True
) -> Dict:
    """Sync a kcpwd password to Kubernetes secret - FIXED version

    Uses create-first approach for better reliability

    Args:
        key: kcpwd password key
        namespace: K8s namespace
        secret_name: K8s secret name (defaults to key)
        secret_key: Key in K8s secret (defaults to "password")
        master_password: Master password if needed
        labels: Additional labels for secret
        kubeconfig: Path to kubeconfig
        create_if_missing: Create secret if doesn't exist

    Returns:
        Result dictionary with status
    """
    from .core import get_password
    from .master_protection import get_master_password, has_master_password

    # Get password from kcpwd
    if has_master_password(key):
        if not master_password:
            master_password = getpass.getpass(f"Enter master password for '{key}': ")
        password = get_master_password(key, master_password)
    else:
        password = get_password(key)

    if password is None:
        raise K8sError(f"Password '{key}' not found in kcpwd")

    # Default names
    if secret_name is None:
        secret_name = key.replace('_', '-').lower()
    if secret_key is None:
        secret_key = "password"

    # Create K8s client
    client = K8sClient(namespace=namespace, kubeconfig=kubeconfig)

    # Prepare data
    data = {secret_key: password}

    # Add metadata
    if labels is None:
        labels = {}
    labels["kcpwd.io/source-key"] = key
    labels["kcpwd.io/synced-at"] = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Create or update - simplified approach
    # Try to create first, if exists then update
    action = "created"
    try:
        client.create_secret(secret_name, data, labels=labels)
    except K8sError as e:
        error_msg = str(e)
        # If secret already exists, update it
        if "already exists" in error_msg.lower():
            client.update_secret(secret_name, data)
            action = "updated"
        elif not create_if_missing and ("not found" in error_msg.lower()):
            raise K8sError(f"Secret '{secret_name}' does not exist and create_if_missing=False")
        else:
            raise

    return {
        "success": True,
        "action": action,
        "kcpwd_key": key,
        "k8s_secret": secret_name,
        "namespace": namespace,
        "secret_key": secret_key
    }


def sync_all_to_k8s(
    namespace: str = "default",
    prefix: Optional[str] = None,
    labels: Optional[Dict[str, str]] = None,
    kubeconfig: Optional[str] = None,
    skip_master_protected: bool = False
) -> Dict:
    """Sync all kcpwd passwords to Kubernetes

    Args:
        namespace: K8s namespace
        prefix: Only sync keys with this prefix
        labels: Additional labels
        kubeconfig: Path to kubeconfig
        skip_master_protected: Skip master-protected passwords

    Returns:
        Summary dictionary
    """
    from .core import list_all_keys
    from .master_protection import list_master_keys

    keys = list_all_keys()

    if not skip_master_protected:
        master_keys = list_master_keys()
        print(f"\n⚠️  Found {len(master_keys)} master-protected passwords")
        print("These will be skipped. To sync them, use individual sync with --master-password")
        keys = [k for k in keys if k not in master_keys]

    if prefix:
        keys = [k for k in keys if k.startswith(prefix)]

    results = {
        "total": len(keys),
        "synced": 0,
        "failed": 0,
        "errors": []
    }

    for key in keys:
        try:
            result = sync_to_k8s(
                key,
                namespace=namespace,
                labels=labels,
                kubeconfig=kubeconfig
            )
            results["synced"] += 1
            print(f"✓ Synced: {key} → {result['k8s_secret']}")
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({"key": key, "error": str(e)})
            print(f"✗ Failed: {key} - {e}")

    return results


def import_from_k8s(
    secret_name: str,
    namespace: str = "default",
    kcpwd_key: Optional[str] = None,
    secret_key: str = "password",
    use_master: bool = False,
    master_password: Optional[str] = None,
    kubeconfig: Optional[str] = None,
    overwrite: bool = False
) -> Dict:
    """Import Kubernetes secret to kcpwd

    Args:
        secret_name: K8s secret name
        namespace: K8s namespace
        kcpwd_key: kcpwd key name (defaults to secret_name)
        secret_key: Key in K8s secret to import
        use_master: Store with master password protection
        master_password: Master password if use_master=True
        kubeconfig: Path to kubeconfig
        overwrite: Overwrite if exists in kcpwd

    Returns:
        Result dictionary
    """
    from .core import set_password, get_password
    from .master_protection import set_master_password, has_master_password

    # Get from K8s
    client = K8sClient(namespace=namespace, kubeconfig=kubeconfig)
    secret_data = client.get_secret(secret_name)

    if secret_data is None:
        raise K8sError(f"Secret '{secret_name}' not found in namespace '{namespace}'")

    if secret_key not in secret_data:
        available_keys = ", ".join(secret_data.keys())
        raise K8sError(
            f"Key '{secret_key}' not found in secret. "
            f"Available keys: {available_keys}"
        )

    password = secret_data[secret_key]

    # Default kcpwd key
    if kcpwd_key is None:
        kcpwd_key = secret_name.replace('-', '_')

    # Check if exists
    existing = get_password(kcpwd_key) or has_master_password(kcpwd_key)
    if existing and not overwrite:
        raise K8sError(
            f"Password '{kcpwd_key}' already exists in kcpwd. "
            f"Use --overwrite to replace it."
        )

    # Store in kcpwd
    if use_master:
        if not master_password:
            master_password = getpass.getpass("Enter master password: ")
            confirm = getpass.getpass("Confirm master password: ")
            if master_password != confirm:
                raise K8sError("Passwords do not match")

        success = set_master_password(kcpwd_key, password, master_password)
    else:
        success = set_password(kcpwd_key, password)

    if not success:
        raise K8sError("Failed to store password in kcpwd")

    return {
        "success": True,
        "k8s_secret": secret_name,
        "namespace": namespace,
        "kcpwd_key": kcpwd_key,
        "master_protected": use_master
    }


def list_k8s_secrets(
    namespace: str = "default",
    managed_only: bool = False,
    kubeconfig: Optional[str] = None
) -> List[Dict]:
    """List Kubernetes secrets

    Args:
        namespace: K8s namespace
        managed_only: Only show kcpwd-managed secrets
        kubeconfig: Path to kubeconfig

    Returns:
        List of secret information
    """
    client = K8sClient(namespace=namespace, kubeconfig=kubeconfig)

    labels = {"app.kubernetes.io/managed-by": "kcpwd"} if managed_only else None
    secret_names = client.list_secrets(labels=labels)

    secrets = []
    for name in secret_names:
        try:
            data = client.get_secret(name)
            if data:
                secrets.append({
                    "name": name,
                    "namespace": namespace,
                    "keys": list(data.keys()),
                    "key_count": len(data)
                })
        except Exception as e:
            print(f"Warning: Failed to get secret '{name}': {e}")

    return secrets


def delete_k8s_secret(
    secret_name: str,
    namespace: str = "default",
    kubeconfig: Optional[str] = None
) -> bool:
    """Delete Kubernetes secret

    Args:
        secret_name: Secret name
        namespace: K8s namespace
        kubeconfig: Path to kubeconfig

    Returns:
        True if successful
    """
    client = K8sClient(namespace=namespace, kubeconfig=kubeconfig)
    return client.delete_secret(secret_name)


def watch_and_sync(
    namespace: str = "default",
    interval: int = 60,
    prefix: Optional[str] = None,
    kubeconfig: Optional[str] = None
):
    """Watch kcpwd passwords and auto-sync to Kubernetes

    Args:
        namespace: K8s namespace
        interval: Check interval in seconds
        prefix: Only sync keys with this prefix
        kubeconfig: Path to kubeconfig
    """
    print(f"🔄 Starting watch mode...")
    print(f"   Namespace: {namespace}")
    print(f"   Interval: {interval}s")
    if prefix:
        print(f"   Prefix filter: {prefix}")
    print(f"\n   Press Ctrl+C to stop\n")

    try:
        while True:
            try:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Syncing...")

                result = sync_all_to_k8s(
                    namespace=namespace,
                    prefix=prefix,
                    kubeconfig=kubeconfig,
                    skip_master_protected=True
                )

                print(f"   Synced: {result['synced']}, Failed: {result['failed']}")

                if result['failed'] > 0:
                    print(f"   Errors:")
                    for error in result['errors'][:5]:  # Show first 5
                        print(f"     • {error['key']}: {error['error']}")

            except Exception as e:
                print(f"   Error during sync: {e}")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n✓ Watch mode stopped")