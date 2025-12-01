"""
kcpwd - Cross-platform Keychain Password Manager
Supports macOS, Linux, and Windows
Can be used as both CLI tool and Python library
NEW: Kubernetes integration for secret management
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

# Kubernetes integration (optional - requires kubectl)
try:
    from .k8s import (
        sync_to_k8s,
        sync_all_to_k8s,
        import_from_k8s,
        list_k8s_secrets,
        delete_k8s_secret,
        watch_and_sync,
        K8sError,
        K8sClient
    )
    __k8s_available__ = True
except ImportError:
    __k8s_available__ = False

__version__ = "0.8.0"
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
    'get_backend_info',
]

# Add K8s functions if available
if __k8s_available__:
    __all__.extend([
        'sync_to_k8s',
        'sync_all_to_k8s',
        'import_from_k8s',
        'list_k8s_secrets',
        'delete_k8s_secret',
        'watch_and_sync',
        'K8sError',
        'K8sClient',
    ])