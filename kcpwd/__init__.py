"""
kcpwd - macOS Keychain Password Manager
Can be used as both CLI tool and Python library
"""

from .core import set_password, get_password, delete_password, copy_to_clipboard, generate_password
from .decorators import require_password

__version__ = "0.2.1"
__all__ = [
    'set_password',
    'get_password',
    'delete_password',
    'copy_to_clipboard',
    'generate_password',
    'require_password'
]