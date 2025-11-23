"""
kcpwd - Cross-platform Keychain Password Manager
Supports macOS and Linux
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
    import_passwords,
    get_backend_info
)
from .decorators import require_password, require_master_password
from .master_protection import (
    set_master_password,
    get_master_password,
    delete_master_password,
    has_master_password,
    list_master_keys
)
from .strength import check_password_strength, PasswordStrength
from .platform_utils import (
    get_platform,
    get_platform_name,
    is_platform_supported,
    check_platform_requirements,
    check_clipboard_support
)

__version__ = "0.5.0"
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
    'require_master_password',
    'set_master_password',
    'get_master_password',
    'delete_master_password',
    'has_master_password',
    'list_master_keys',
    'check_password_strength',
    'PasswordStrength',
    'get_platform',
    'get_platform_name',
    'is_platform_supported',
    'check_platform_requirements',
    'check_clipboard_support',
    'get_backend_info'
]