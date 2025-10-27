"""
kcpwd.core - Core password management functions
Can be used directly as a library
"""

import keyring
import subprocess
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