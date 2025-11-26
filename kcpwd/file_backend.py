"""
kcpwd.file_backend - Encrypted file-based keyring backend
Used as fallback when no system keyring is available (Docker, headless, etc.)

IMPORTANT: This master password is ONLY for encrypting the storage file itself.
For protecting individual passwords, use master_protection.py instead.
"""

import os
import json
import base64
from typing import Optional, Dict
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import getpass
import hashlib

# Security parameters (same as master_protection for consistency)
PBKDF2_ITERATIONS = 600000  # OWASP 2023
SALT_SIZE = 16  # 128 bits
KEY_SIZE = 32  # 256 bits
NONCE_SIZE = 12  # 96 bits


class EncryptedFileBackend:
    """Encrypted file-based storage backend

    Uses AES-256-GCM for encryption with PBKDF2-SHA256 key derivation.
    Stores all passwords in a single encrypted JSON file.

    Security:
    - AES-256-GCM authenticated encryption
    - PBKDF2-SHA256 with 600,000 iterations
    - Unique salt per file
    - Master password derived encryption key

    IMPORTANT NOTE:
    This "master password" is ONLY for encrypting the storage file.
    It is NOT the same as "master protection password" for individual passwords.

    Two types of protection:
    1. File Storage Password (this class) - Protects the entire storage file
    2. Master Protection Password (master_protection.py) - Protects specific passwords
    """

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize backend

        Args:
            storage_path: Path to storage file (default: ~/.kcpwd/keyring.enc)
        """
        if storage_path is None:
            storage_path = os.path.expanduser("~/.kcpwd/keyring.enc")

        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Master password file (stores hash only, for verification)
        self.master_hash_path = self.storage_path.parent / "master.hash"

        # Cache for current session - CRITICAL for user experience
        # Without cache, user would be prompted for file password on every operation
        self._master_password: Optional[str] = None
        self._cache: Optional[Dict] = None

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        return kdf.derive(password.encode('utf-8'))

    def _hash_password(self, password: str) -> str:
        """Hash password for verification (not for encryption)"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def _get_or_create_master_password(self) -> str:
        """Get master password from user (with caching)

        This is the FILE STORAGE password, not the master protection password!
        """
        # Return cached if available (avoids asking multiple times)
        if self._master_password:
            return self._master_password

        # Check if master password already set
        if self.master_hash_path.exists():
            # Verify existing password
            with open(self.master_hash_path, 'r') as f:
                stored_hash = f.read().strip()

            # Ask for password with CLEAR terminology
            password = getpass.getpass("🔐 Enter file storage password: ")

            if self._hash_password(password) != stored_hash:
                raise ValueError("Incorrect file storage password")

            # Cache it for this session
            self._master_password = password
            return password

        else:
            # First time setup
            print("\n" + "=" * 60)
            print("🔐 kcpwd File Storage Setup")
            print("=" * 60)
            print("No system keyring detected. Setting up encrypted file storage.")
            print()
            print("⚠️  IMPORTANT: This password protects your storage FILE.")
            print("   (This is NOT the same as 'master protection' for passwords)")
            print()
            print("You'll need this password to access your stored passwords.")
            print("=" * 60)
            print()

            password = getpass.getpass("Create file storage password: ")
            password_confirm = getpass.getpass("Confirm file storage password: ")

            if password != password_confirm:
                raise ValueError("Passwords do not match")

            if len(password) < 8:
                raise ValueError("File storage password must be at least 8 characters")

            # Save hash
            self.master_hash_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with open(self.master_hash_path, 'w') as f:
                f.write(self._hash_password(password))

            # Set restrictive permissions
            self.master_hash_path.chmod(0o600)

            print("\n✅ File storage password set successfully!")
            print(f"📁 Storage location: {self.storage_path}")
            print()
            print("💡 Tip: This password will be cached during your session")
            print("   to avoid asking multiple times.")
            print()

            # Cache it
            self._master_password = password
            return password

    def _load_storage(self) -> Dict:
        """Load and decrypt storage file"""
        if self._cache is not None:
            return self._cache

        if not self.storage_path.exists():
            return {}

        master_password = self._get_or_create_master_password()

        try:
            with open(self.storage_path, 'rb') as f:
                encrypted_data = f.read()

            # Extract components
            salt = encrypted_data[:SALT_SIZE]
            nonce = encrypted_data[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
            ciphertext = encrypted_data[SALT_SIZE + NONCE_SIZE:]

            # Decrypt
            key = self._derive_key(master_password, salt)
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)

            # Parse JSON
            data = json.loads(plaintext.decode('utf-8'))
            self._cache = data
            return data

        except Exception as e:
            raise ValueError(f"Failed to decrypt storage: {e}")

    def _save_storage(self, data: Dict) -> None:
        """Encrypt and save storage file"""
        master_password = self._get_or_create_master_password()

        # Generate salt and nonce
        salt = os.urandom(SALT_SIZE)
        nonce = os.urandom(NONCE_SIZE)

        # Encrypt
        key = self._derive_key(master_password, salt)
        aesgcm = AESGCM(key)

        plaintext = json.dumps(data, indent=2).encode('utf-8')
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # Combine components
        encrypted_data = salt + nonce + ciphertext

        # Write atomically (write to temp, then rename)
        temp_path = self.storage_path.with_suffix('.tmp')
        with open(temp_path, 'wb') as f:
            f.write(encrypted_data)

        # Set restrictive permissions
        temp_path.chmod(0o600)

        # Atomic rename
        temp_path.replace(self.storage_path)

        # Update cache
        self._cache = data

    def set_password(self, service: str, key: str, password: str) -> bool:
        """Store a password"""
        try:
            data = self._load_storage()

            if service not in data:
                data[service] = {}

            data[service][key] = password
            self._save_storage(data)
            return True

        except Exception as e:
            print(f"Error storing password: {e}")
            return False

    def get_password(self, service: str, key: str) -> Optional[str]:
        """Retrieve a password"""
        try:
            data = self._load_storage()
            return data.get(service, {}).get(key)
        except Exception:
            return None

    def delete_password(self, service: str, key: str) -> bool:
        """Delete a password"""
        try:
            data = self._load_storage()

            if service not in data or key not in data[service]:
                return False

            del data[service][key]

            # Clean up empty services
            if not data[service]:
                del data[service]

            self._save_storage(data)
            return True

        except Exception:
            return False

    def list_keys(self, service: str) -> list:
        """List all keys for a service"""
        try:
            data = self._load_storage()
            return list(data.get(service, {}).keys())
        except Exception:
            return []

    def clear_cache(self):
        """Clear password cache (for security)

        Call this when you want to force password prompt on next access.
        """
        self._master_password = None
        self._cache = None


# Global instance (lazy initialized)
_file_backend: Optional[EncryptedFileBackend] = None


def get_file_backend() -> EncryptedFileBackend:
    """Get or create file backend instance"""
    global _file_backend
    if _file_backend is None:
        _file_backend = EncryptedFileBackend()
    return _file_backend