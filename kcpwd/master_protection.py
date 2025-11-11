"""
kcpwd.master - Master password protection for individual passwords
Each password can optionally be protected with an additional master password layer
"""

import keyring
import hashlib
import base64
from typing import Optional
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
    """Encrypt password with master password

    Returns base64-encoded encrypted data with salt and nonce
    Format: base64(salt + nonce + encrypted_data)
    """
    # Generate random salt and nonce
    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)

    # Derive key and encrypt
    key = _derive_key(master_password, salt)
    aesgcm = AESGCM(key)
    encrypted = aesgcm.encrypt(nonce, password.encode('utf-8'), None)

    # Combine and encode
    combined = salt + nonce + encrypted
    return base64.b64encode(combined).decode('ascii')


def _decrypt_password(encrypted_data: str, master_password: str) -> Optional[str]:
    """Decrypt password with master password"""
    try:
        # Decode
        combined = base64.b64decode(encrypted_data)

        # Extract components
        salt = combined[:SALT_SIZE]
        nonce = combined[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
        encrypted = combined[SALT_SIZE + NONCE_SIZE:]

        # Derive key and decrypt
        key = _derive_key(master_password, salt)
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(nonce, encrypted, None)

        return decrypted.decode('utf-8')
    except Exception:
        return None


def set_master_password(key: str, password: str, master_password: str) -> bool:
    """Store password encrypted with master password

    Args:
        key: Password identifier
        password: The actual password to store
        master_password: Master password to encrypt with

    Returns:
        bool: True if successful

    Example:
        >>> set_master_password("prod_db", "secret123", "MyMasterPass!")
        True
    """
    try:
        # Encrypt password
        encrypted_data = _encrypt_password(password, master_password)

        # Store encrypted data in separate service
        keyring.set_password(MASTER_SERVICE_NAME, key, encrypted_data)
        return True
    except Exception:
        return False


def get_master_password(key: str, master_password: str) -> Optional[str]:
    """Retrieve password protected with master password

    Args:
        key: Password identifier
        master_password: Master password to decrypt with

    Returns:
        str: Decrypted password if successful, None otherwise

    Example:
        >>> password = get_master_password("prod_db", "MyMasterPass!")
        >>> print(password)
        'secret123'
    """
    try:
        # Get encrypted data
        encrypted_data = keyring.get_password(MASTER_SERVICE_NAME, key)
        if not encrypted_data:
            return None

        # Decrypt
        return _decrypt_password(encrypted_data, master_password)
    except Exception:
        return None


def has_master_password(key: str) -> bool:
    """Check if a key is protected with master password

    Args:
        key: Password identifier

    Returns:
        bool: True if key has master password protection

    Example:
        >>> has_master_password("prod_db")
        True
    """
    try:
        encrypted_data = keyring.get_password(MASTER_SERVICE_NAME, key)
        return encrypted_data is not None
    except Exception:
        return False


def delete_master_password(key: str) -> bool:
    """Delete master-protected password

    Args:
        key: Password identifier

    Returns:
        bool: True if successful

    Example:
        >>> delete_master_password("prod_db")
        True
    """
    try:
        encrypted_data = keyring.get_password(MASTER_SERVICE_NAME, key)
        if encrypted_data is None:
            return False

        keyring.delete_password(MASTER_SERVICE_NAME, key)
        return True
    except Exception:
        return False


def list_master_keys() -> list:
    """List all keys protected with master password

    Returns:
        list: List of master-protected keys

    Example:
        >>> keys = list_master_keys()
        >>> print(keys)
        ['prod_db', 'api_key']
    """
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