"""
kcpwd.core - Core password management functions
Can be used directly as a library
"""

import keyring
import subprocess
import secrets
import string
from typing import Optional

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