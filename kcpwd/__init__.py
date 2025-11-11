"""
kcpwd - macOS Keychain Password Manager
Can be used as both CLI tool and Python library
"""

from .core import (
    set_password,
    get_password,
    delete_password,
    copy_to_clipboard,
    generate_password,
    list_all_keys,
    export_passwords,
    import_passwords
)
from .decorators import require_password
from .master_protection import (
    set_master_password,
    get_master_password,
    delete_master_password,
    has_master_password,
    list_master_keys
)

__version__ = "0.4.0"
__all__ = [
    'set_password',
    'get_password',
    'delete_password',
    'copy_to_clipboard',
    'generate_password',
    'list_all_keys',
    'export_passwords',
    'import_passwords',
    'require_password',
    'set_master_password',
    'get_master_password',
    'delete_master_password',
    'has_master_password',
    'list_master_keys'
]