"""
kcpwd.core - Core password management functions
Can be used directly as a library
"""

import keyring
import subprocess
import secrets
import string
import json
from typing import Optional, Dict, List
from datetime import datetime

SERVICE_NAME = "kcpwd"


def copy_to_clipboard(text: str) -> bool:
    """Copy text to macOS clipboard using pbcopy

    Args:
        text: Text to copy to clipboard

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        process = subprocess.Popen(
            ['pbcopy'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        process.communicate(text.encode('utf-8'))
        return True
    except Exception:
        return False


def set_password(key: str, password: str) -> bool:
    """Store a password for a given key in macOS Keychain

    Args:
        key: Identifier for the password
        password: Password to store

    Returns:
        bool: True if successful, False otherwise

    Example:
        >>> from kcpwd import set_password
        >>> set_password("my_db", "secret123")
        True
    """
    try:
        keyring.set_password(SERVICE_NAME, key, password)
        return True
    except Exception:
        return False


def get_password(key: str, copy_to_clip: bool = False) -> Optional[str]:
    """Retrieve a password from macOS Keychain

    Args:
        key: Identifier for the password
        copy_to_clip: If True, also copy password to clipboard

    Returns:
        str: The password if found, None otherwise

    Example:
        >>> from kcpwd import get_password
        >>> password = get_password("my_db")
        >>> print(password)
        'secret123'

        >>> password = get_password("my_db", copy_to_clip=True)
        # Password is now in clipboard
    """
    try:
        password = keyring.get_password(SERVICE_NAME, key)

        if password and copy_to_clip:
            clipboard_success = copy_to_clipboard(password)
            if not clipboard_success:
                # Still return password even if clipboard fails
                pass

        return password
    except Exception:
        return None


def delete_password(key: str) -> bool:
    """Delete a password from macOS Keychain

    Args:
        key: Identifier for the password to delete

    Returns:
        bool: True if successful, False otherwise

    Example:
        >>> from kcpwd import delete_password
        >>> delete_password("my_db")
        True
    """
    try:
        password = keyring.get_password(SERVICE_NAME, key)

        if password is None:
            return False

        keyring.delete_password(SERVICE_NAME, key)
        return True
    except Exception:
        return False


def list_all_keys() -> List[str]:
    """List all stored password keys from macOS Keychain

    Note: This uses the security command-line tool to query Keychain.
    Returns empty list if unable to retrieve keys.

    Returns:
        List[str]: List of all stored keys

    Example:
        >>> from kcpwd import list_all_keys
        >>> keys = list_all_keys()
        >>> print(keys)
        ['my_db', 'api_key', 'email_password']
    """
    import re

    try:
        # Use security dump-keychain to get all keychain entries
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

        # Split into keychain entries (each entry starts with 'keychain:')
        entries = output.split('keychain:')

        for entry in entries:
            # Check if this entry is for kcpwd service
            if f'"{SERVICE_NAME}"' in entry or f'svce.*{SERVICE_NAME}' in entry:
                # Extract account name using regex
                # Look for patterns like: "acct"<blob>="keyname"
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


def export_passwords(filepath: str, include_passwords: bool = True) -> Dict:
    """Export all passwords to a JSON file

    WARNING: Exported file contains passwords in PLAIN TEXT. Keep secure!

    Args:
        filepath: Path to the output JSON file
        include_passwords: If True, include actual passwords; if False, only export keys

    Returns:
        dict: Export result with keys 'success', 'exported_count', 'failed_keys', 'message'

    Example:
        >>> from kcpwd import export_passwords
        >>> result = export_passwords('passwords_backup.json')
        >>> print(f"Exported {result['exported_count']} passwords")

        >>> # Export only keys (without passwords)
        >>> result = export_passwords('keys_only.json', include_passwords=False)
    """
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
            'version': '0.4.0',
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

        # Write to file
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
    """Import passwords from a JSON file

    Args:
        filepath: Path to the JSON file to import
        overwrite: If True, overwrite existing passwords; if False, skip existing keys
        dry_run: If True, only check what would be imported without making changes

    Returns:
        dict: Import result with keys 'success', 'imported_count', 'skipped_keys',
              'failed_keys', 'message'

    Example:
        >>> from kcpwd import import_passwords
        >>> # Dry run first to see what would be imported
        >>> result = import_passwords('backup.json', dry_run=True)
        >>> print(result['message'])

        >>> # Actually import
        >>> result = import_passwords('backup.json', overwrite=False)
        >>> print(f"Imported {result['imported_count']} passwords")

        >>> # Import and overwrite existing
        >>> result = import_passwords('backup.json', overwrite=True)
    """
    try:
        # Read JSON file
        with open(filepath, 'r', encoding='utf-8') as f:
            import_data = json.load(f)

        # Validate format
        if 'passwords' not in import_data:
            return {
                'success': False,
                'imported_count': 0,
                'skipped_keys': [],
                'failed_keys': [],
                'message': 'Invalid import file format: missing "passwords" field'
            }

        # Check if file has passwords or just keys
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

        # Get existing keys
        existing_keys = set(list_all_keys())

        for entry in passwords:
            key = entry.get('key')
            password = entry.get('password')

            if not key or not password:
                failed_keys.append(key or 'unknown')
                continue

            # Check if key already exists
            if key in existing_keys and not overwrite:
                skipped_keys.append(key)
                continue

            # Dry run: don't actually import
            if dry_run:
                imported_count += 1
                continue

            # Import password
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
    """Generate a cryptographically secure random password

    Args:
        length: Length of the password (default: 16)
        use_uppercase: Include uppercase letters (default: True)
        use_lowercase: Include lowercase letters (default: True)
        use_digits: Include digits (default: True)
        use_symbols: Include symbols (default: True)
        exclude_ambiguous: Exclude ambiguous characters like 0/O, 1/l/I (default: False)

    Returns:
        str: Generated password

    Example:
        >>> from kcpwd import generate_password
        >>> password = generate_password(length=20)
        >>> print(password)
        'aB3#xK9!mL2$nP5@qR7'

        >>> # Simple alphanumeric password
        >>> password = generate_password(length=12, use_symbols=False)
        >>> print(password)
        'aB3xK9mL2nP5'

        >>> # Only digits (PIN)
        >>> pin = generate_password(length=6, use_uppercase=False,
        ...                         use_lowercase=False, use_symbols=False)
        >>> print(pin)
        '384729'
    """
    if length < 4:
        raise ValueError("Password length must be at least 4 characters")

    if not any([use_uppercase, use_lowercase, use_digits, use_symbols]):
        raise ValueError("At least one character type must be enabled")

    # Define character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    symbols = "!@#$%^&*()-_=+[]{}|;:,.<>?"

    # Exclude ambiguous characters if requested
    if exclude_ambiguous:
        uppercase = uppercase.replace('O', '').replace('I', '')
        lowercase = lowercase.replace('l', '')
        digits = digits.replace('0', '').replace('1', '')

    # Build character pool
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

    # Generate remaining characters
    remaining_length = length - len(required_chars)
    password_chars = required_chars + [
        secrets.choice(char_pool) for _ in range(remaining_length)
    ]

    # Shuffle to avoid predictable patterns
    secrets.SystemRandom().shuffle(password_chars)

    return ''.join(password_chars)