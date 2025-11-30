"""
kcpwd.master_protection - UNIVERSAL master password protection
Works with ALL backends: macOS Keychain, Linux SecretService, Windows Credential Locker, AND File Backend

IMPORTANT: This is SEPARATE from file storage encryption
"""

import base64
from typing import Optional, List
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

# Service name for master-protected passwords
MASTER_SERVICE_NAME = "kcpwd-master"

# Security parameters
PBKDF2_ITERATIONS = 600000  # OWASP 2023
SALT_SIZE = 16  # 128 bits
KEY_SIZE = 32   # 256 bits
NONCE_SIZE = 12  # 96 bits


def _get_storage_backend():
    """Get the appropriate storage backend for master-protected passwords

    Uses same backend detection as core, ensures consistency
    """
    from .core import _detect_backend, _get_backend

    backend_type = _detect_backend()

    if backend_type == 'keyring':
        import keyring
        return ('keyring', keyring)
    else:
        # Use file backend
        backend = _get_backend()
        return ('file', backend)


def _derive_key(master_password: str, salt: bytes) -> bytes:
    """Derive encryption key from master password"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend()
    )
    return kdf.derive(master_password.encode('utf-8'))


def _encrypt_password(password: str, master_password: str) -> str:
    """Encrypt password with master password"""
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)

    key = _derive_key(master_password, salt)
    aesgcm = AESGCM(key)
    encrypted = aesgcm.encrypt(nonce, password.encode('utf-8'), None)

    combined = salt + nonce + encrypted
    return base64.b64encode(combined).decode('ascii')


def _decrypt_password(encrypted_data: str, master_password: str) -> Optional[str]:
    """Decrypt password with master password"""
    try:
        combined = base64.b64decode(encrypted_data)

        salt = combined[:SALT_SIZE]
        nonce = combined[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
        encrypted = combined[SALT_SIZE + NONCE_SIZE:]

        key = _derive_key(master_password, salt)
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(nonce, encrypted, None)

        return decrypted.decode('utf-8')
    except Exception:
        return None


def set_master_password(key: str, password: str, master_password: str) -> bool:
    """Store password with master protection

    Works with ALL backends (keyring or file)
    Supports macOS, Linux, and Windows
    """
    try:
        encrypted_data = _encrypt_password(password, master_password)

        backend_type, backend = _get_storage_backend()

        if backend_type == 'keyring':
            backend.set_password(MASTER_SERVICE_NAME, key, encrypted_data)
        else:
            # File backend
            backend.set_password(MASTER_SERVICE_NAME, key, encrypted_data)

        return True
    except Exception:
        return False


def get_master_password(key: str, master_password: str) -> Optional[str]:
    """Retrieve master-protected password

    Works with ALL backends (keyring or file)
    Supports macOS, Linux, and Windows
    """
    try:
        backend_type, backend = _get_storage_backend()

        if backend_type == 'keyring':
            encrypted_data = backend.get_password(MASTER_SERVICE_NAME, key)
        else:
            # File backend
            encrypted_data = backend.get_password(MASTER_SERVICE_NAME, key)

        if not encrypted_data:
            return None

        return _decrypt_password(encrypted_data, master_password)
    except Exception:
        return None


def has_master_password(key: str) -> bool:
    """Check if key has master protection

    Works with ALL backends (keyring or file)
    Supports macOS, Linux, and Windows
    """
    try:
        backend_type, backend = _get_storage_backend()

        if backend_type == 'keyring':
            encrypted_data = backend.get_password(MASTER_SERVICE_NAME, key)
        else:
            # File backend
            encrypted_data = backend.get_password(MASTER_SERVICE_NAME, key)

        return encrypted_data is not None
    except Exception:
        return False


def delete_master_password(key: str) -> bool:
    """Delete master-protected password

    Works with ALL backends (keyring or file)
    Supports macOS, Linux, and Windows
    """
    try:
        backend_type, backend = _get_storage_backend()

        if backend_type == 'keyring':
            encrypted_data = backend.get_password(MASTER_SERVICE_NAME, key)
            if encrypted_data is None:
                return False
            backend.delete_password(MASTER_SERVICE_NAME, key)
        else:
            # File backend
            return backend.delete_password(MASTER_SERVICE_NAME, key)

        return True
    except Exception:
        return False


def list_master_keys() -> List[str]:
    """List all master-protected keys

    Works with ALL backends (keyring or file)
    Supports macOS, Linux, and Windows
    """
    backend_type, backend = _get_storage_backend()

    if backend_type == 'keyring':
        # Use platform-specific listing
        from .platform_utils import get_platform
        current_platform = get_platform()

        if current_platform == 'macos':
            return _list_master_keys_macos()
        elif current_platform == 'linux':
            return _list_master_keys_linux()
        elif current_platform == 'windows':
            return _list_master_keys_windows()
        else:
            return []
    else:
        # File backend - direct list
        try:
            return backend.list_keys(MASTER_SERVICE_NAME)
        except Exception:
            return []


def _list_master_keys_macos() -> List[str]:
    """List master keys on macOS using security command"""
    import subprocess
    import re

    try:
        result = subprocess.run(
            ['security', 'dump-keychain'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return []

        keys = []
        output = result.stdout
        entries = output.split('keychain:')

        for entry in entries:
            if f'"{MASTER_SERVICE_NAME}"' in entry:
                acct_match = re.search(r'"acct"<blob>="([^"]+)"', entry)
                if acct_match:
                    key = acct_match.group(1)
                    if key and key not in keys:
                        keys.append(key)

        return sorted(keys)
    except Exception:
        return []


def _list_master_keys_linux() -> List[str]:
    """List master keys on Linux

    Tries secretstorage first, falls back to file backend
    """
    try:
        import secretstorage

        connection = secretstorage.dbus_init()
        collection = secretstorage.get_default_collection(connection)

        keys = []
        for item in collection.get_all_items():
            attributes = item.get_attributes()
            if attributes.get('service') == MASTER_SERVICE_NAME:
                key = attributes.get('username')
                if key and key not in keys:
                    keys.append(key)

        connection.close()
        return sorted(keys)

    except ImportError:
        # No secretstorage, try file backend
        try:
            from .core import _get_backend
            backend = _get_backend()
            return backend.list_keys(MASTER_SERVICE_NAME)
        except:
            return []
    except Exception:
        # SecretStorage failed, try file backend
        try:
            from .core import _get_backend
            backend = _get_backend()
            return backend.list_keys(MASTER_SERVICE_NAME)
        except:
            return []


def _list_master_keys_windows() -> List[str]:
    """List master keys on Windows

    Uses cmdkey to list credentials from Windows Credential Manager
    """
    import subprocess
    import re

    keys = []

    try:
        # Use cmdkey to list Windows credentials
        result = subprocess.run(
            ['cmdkey', '/list'],
            capture_output=True,
            text=True,
            shell=True,
            timeout=10
        )

        if result.returncode == 0:
            output = result.stdout

            # Look for kcpwd-master credentials
            # Pattern to match master-protected entries
            pattern = rf'Target:\s*{MASTER_SERVICE_NAME}[:_](\S+)'
            matches = re.findall(pattern, output, re.IGNORECASE)

            for match in matches:
                key = match.strip()
                if key and key not in keys:
                    keys.append(key)

        return sorted(keys)

    except subprocess.TimeoutExpired:
        return []
    except Exception:
        # If Windows-specific method fails, try file backend
        try:
            from .core import _get_backend
            backend = _get_backend()
            return backend.list_keys(MASTER_SERVICE_NAME)
        except:
            return []