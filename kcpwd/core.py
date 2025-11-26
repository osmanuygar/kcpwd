"""
kcpwd.core - Core password management functions
FIXED: Persistent backend cache for session

Changes:
- Added _get_backend() with module-level cache
- All functions use same backend instance
- Master password asked ONCE per session
"""

import keyring
import subprocess
import secrets
import string
import json
from typing import Optional, Dict, List
from datetime import datetime
from .platform_utils import copy_to_clipboard as _platform_copy_to_clipboard

SERVICE_NAME = "kcpwd"

# Backend detection
_backend_type: Optional[str] = None
_backend_error: Optional[str] = None

# CRITICAL: Cached backend instance for session persistence
_cached_backend = None


def _detect_backend() -> str:
    """Detect available backend"""
    global _backend_type, _backend_error

    if _backend_type is not None:
        return _backend_type

    try:
        backend = keyring.get_keyring()
        backend_class = backend.__class__.__name__
        backend_module = backend.__class__.__module__

        if 'fail' in backend_module.lower():
            raise Exception("Fail backend detected")

        test_key = "_kcpwd_backend_test_"
        keyring.set_password("_kcpwd_test_", test_key, "test")
        result = keyring.get_password("_kcpwd_test_", test_key)

        if result == "test":
            try:
                keyring.delete_password("_kcpwd_test_", test_key)
            except:
                pass
            _backend_type = 'keyring'
            return 'keyring'
        else:
            raise Exception("Backend test failed")

    except Exception as e:
        _backend_error = str(e)
        _backend_type = 'file'
        return 'file'


def _get_backend():
    """Get cached backend instance

    CRITICAL FIX: Returns SAME instance across all operations.
    This preserves the master password cache in file backend.

    Without this, every operation creates new instance and asks password again!
    """
    global _cached_backend

    # Return cached if available
    if _cached_backend is not None:
        return _cached_backend

    # Detect and cache
    backend_type = _detect_backend()

    if backend_type == 'file':
        from .file_backend import get_file_backend
        _cached_backend = get_file_backend()
    else:
        _cached_backend = 'keyring'

    return _cached_backend


def get_backend_info() -> Dict:
    """Get information about current backend"""
    backend_type = _detect_backend()

    info = {
        'type': backend_type,
        'available': True
    }

    if backend_type == 'keyring':
        try:
            backend = keyring.get_keyring()
            info['name'] = backend.__class__.__name__
            info['description'] = 'System keyring (OS-native secure storage)'
        except:
            info['name'] = 'Unknown'
            info['description'] = 'System keyring'
    else:
        info['name'] = 'EncryptedFileBackend'
        info['description'] = 'Encrypted file storage (fallback)'
        info['note'] = 'Using file backend because no system keyring detected'
        if _backend_error:
            info['reason'] = _backend_error

    return info


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard"""
    return _platform_copy_to_clipboard(text)


def set_password(key: str, password: str) -> bool:
    """Store a password

    Uses cached backend - master password asked only ONCE per session
    """
    try:
        backend = _get_backend()

        if backend == 'keyring':
            keyring.set_password(SERVICE_NAME, key, password)
            return True
        else:
            # File backend (cached instance)
            return backend.set_password(SERVICE_NAME, key, password)
    except Exception:
        return False


def get_password(key: str, copy_to_clip: bool = False) -> Optional[str]:
    """Retrieve a password

    Uses cached backend - master password asked only ONCE per session
    """
    try:
        backend = _get_backend()

        if backend == 'keyring':
            password = keyring.get_password(SERVICE_NAME, key)
        else:
            # File backend (cached instance)
            password = backend.get_password(SERVICE_NAME, key)

        if password and copy_to_clip:
            clipboard_success = copy_to_clipboard(password)

        return password
    except Exception:
        return None


def delete_password(key: str) -> bool:
    """Delete a password

    Uses cached backend - master password asked only ONCE per session
    """
    try:
        backend = _get_backend()

        if backend == 'keyring':
            password = keyring.get_password(SERVICE_NAME, key)
            if password is None:
                return False
            keyring.delete_password(SERVICE_NAME, key)
            return True
        else:
            # File backend (cached instance)
            return backend.delete_password(SERVICE_NAME, key)
    except Exception:
        return False


def list_all_keys() -> List[str]:
    """List all stored password keys

    Uses cached backend - master password asked only ONCE per session
    """
    backend = _get_backend()

    if backend == 'keyring':
        from .platform_utils import get_platform
        current_platform = get_platform()

        if current_platform == 'macos':
            return _list_all_keys_macos()
        elif current_platform == 'linux':
            return _list_all_keys_linux()
        else:
            return []
    else:
        # File backend (cached instance)
        try:
            return backend.list_keys(SERVICE_NAME)
        except Exception:
            return []


def _list_all_keys_macos() -> List[str]:
    """List all keys on macOS"""
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
            if f'"{SERVICE_NAME}"' in entry or f'svce.*{SERVICE_NAME}' in entry:
                acct_match = re.search(r'"acct"<blob>="([^"]+)"', entry)
                if acct_match:
                    key = acct_match.group(1)
                    if key and key not in keys:
                        keys.append(key)

        return sorted(keys)

    except subprocess.TimeoutExpired:
        return []
    except Exception:
        return []


def _list_all_keys_linux() -> List[str]:
    """List all keys on Linux"""
    try:
        import secretstorage

        connection = secretstorage.dbus_init()
        collection = secretstorage.get_default_collection(connection)

        keys = []
        for item in collection.get_all_items():
            attributes = item.get_attributes()
            if attributes.get('service') == SERVICE_NAME:
                key = attributes.get('username')
                if key and key not in keys:
                    keys.append(key)

        connection.close()
        return sorted(keys)

    except ImportError:
        return []
    except Exception:
        return []


def export_passwords(filepath: str, include_passwords: bool = True) -> Dict:
    """Export all passwords to JSON file"""
    try:
        keys = list_all_keys()

        if not keys:
            return {
                'success': False,
                'exported_count': 0,
                'failed_keys': [],
                'message': 'No passwords found in keychain'
            }

        export_data = {
            'exported_at': datetime.now().isoformat(),
            'service': SERVICE_NAME,
            'version': '0.6.1',
            'include_passwords': include_passwords,
            'passwords': []
        }

        failed_keys = []

        for key in keys:
            if include_passwords:
                password = get_password(key)
                if password is None:
                    failed_keys.append(key)
                    continue

                export_data['passwords'].append({
                    'key': key,
                    'password': password
                })
            else:
                export_data['passwords'].append({
                    'key': key
                })

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return {
            'success': True,
            'exported_count': len(export_data['passwords']),
            'failed_keys': failed_keys,
            'message': f"Successfully exported {len(export_data['passwords'])} passwords to {filepath}"
        }

    except Exception as e:
        return {
            'success': False,
            'exported_count': 0,
            'failed_keys': [],
            'message': f"Export failed: {str(e)}"
        }


def import_passwords(filepath: str, overwrite: bool = False, dry_run: bool = False) -> Dict:
    """Import passwords from JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            import_data = json.load(f)

        if 'passwords' not in import_data:
            return {
                'success': False,
                'imported_count': 0,
                'skipped_keys': [],
                'failed_keys': [],
                'message': 'Invalid import file format: missing "passwords" field'
            }

        has_passwords = import_data.get('include_passwords', True)
        if not has_passwords:
            return {
                'success': False,
                'imported_count': 0,
                'skipped_keys': [],
                'failed_keys': [],
                'message': 'Cannot import: file contains only keys without passwords'
            }

        passwords = import_data['passwords']
        imported_count = 0
        skipped_keys = []
        failed_keys = []

        existing_keys = set(list_all_keys())

        for entry in passwords:
            key = entry.get('key')
            password = entry.get('password')

            if not key or not password:
                failed_keys.append(key or 'unknown')
                continue

            if key in existing_keys and not overwrite:
                skipped_keys.append(key)
                continue

            if dry_run:
                imported_count += 1
                continue

            if set_password(key, password):
                imported_count += 1
            else:
                failed_keys.append(key)

        mode = "Would import" if dry_run else "Imported"
        message = f"{mode} {imported_count} passwords"

        if skipped_keys:
            message += f", skipped {len(skipped_keys)} existing"
        if failed_keys:
            message += f", failed {len(failed_keys)}"

        return {
            'success': True,
            'imported_count': imported_count,
            'skipped_keys': skipped_keys,
            'failed_keys': failed_keys,
            'message': message
        }

    except FileNotFoundError:
        return {
            'success': False,
            'imported_count': 0,
            'skipped_keys': [],
            'failed_keys': [],
            'message': f"File not found: {filepath}"
        }
    except json.JSONDecodeError:
        return {
            'success': False,
            'imported_count': 0,
            'skipped_keys': [],
            'failed_keys': [],
            'message': 'Invalid JSON file format'
        }
    except Exception as e:
        return {
            'success': False,
            'imported_count': 0,
            'skipped_keys': [],
            'failed_keys': [],
            'message': f"Import failed: {str(e)}"
        }


def generate_password(
    length: int = 16,
    use_uppercase: bool = True,
    use_lowercase: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    exclude_ambiguous: bool = False
) -> str:
    """Generate a cryptographically secure random password"""
    if length < 4:
        raise ValueError("Password length must be at least 4 characters")

    if not any([use_uppercase, use_lowercase, use_digits, use_symbols]):
        raise ValueError("At least one character type must be enabled")

    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    symbols = "!@#$%^&*()-_=+[]{}|;:,.<>?"

    if exclude_ambiguous:
        uppercase = uppercase.replace('O', '').replace('I', '')
        lowercase = lowercase.replace('l', '')
        digits = digits.replace('0', '').replace('1', '')

    char_pool = ""
    required_chars = []

    if use_uppercase:
        char_pool += uppercase
        required_chars.append(secrets.choice(uppercase))

    if use_lowercase:
        char_pool += lowercase
        required_chars.append(secrets.choice(lowercase))

    if use_digits:
        char_pool += digits
        required_chars.append(secrets.choice(digits))

    if use_symbols:
        char_pool += symbols
        required_chars.append(secrets.choice(symbols))

    if not char_pool:
        raise ValueError("Character pool is empty")

    remaining_length = length - len(required_chars)
    password_chars = required_chars + [
        secrets.choice(char_pool) for _ in range(remaining_length)
    ]

    secrets.SystemRandom().shuffle(password_chars)

    return ''.join(password_chars)