"""
kcpwd.decorators - Decorators for automatic password management
"""

import functools
import getpass
from typing import Callable, Any, Optional
from .core import get_password
from .master_protection import get_master_password


def require_password(key: str, param_name: str = 'password'):
    """Decorator to automatically inject password from keychain into function

    Args:
        key: Keychain key to retrieve password from
        param_name: Parameter name to inject password into (default: 'password')

    Example:
        >>> from kcpwd import require_password
        >>>
        >>> @require_password('my_db')
        >>> def connect_to_db(host, password=None):
        ...     print(f"Connecting with password: {password}")
        ...     # your db connection code here
        >>>
        >>> connect_to_db("localhost")  # Password automatically retrieved

        >>> @require_password('api_key', param_name='api_key')
        >>> def call_api(endpoint, api_key=None):
        ...     print(f"Calling {endpoint} with key: {api_key}")
        ...     # your API call code here
        >>>
        >>> call_api("/users")  # API key automatically retrieved
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Only inject if password not already provided
            if param_name not in kwargs or kwargs[param_name] is None:
                password = get_password(key)
                if password is None:
                    raise ValueError(f"Password not found in keychain for key: '{key}'")
                kwargs[param_name] = password

            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_master_password(
    key: str,
    param_name: str = 'password',
    master_password: Optional[str] = None,
    prompt_message: Optional[str] = None
):
    """Decorator to automatically inject master-protected password from keychain

    Args:
        key: Keychain key to retrieve password from
        param_name: Parameter name to inject password into (default: 'password')
        master_password: Master password (if None, will prompt user)
        prompt_message: Custom prompt message (default: "Enter master password for '<key>': ")

    Example:
        >>> from kcpwd import require_master_password
        >>>
        >>> # Will prompt for master password at runtime
        >>> @require_master_password('prod_db')
        >>> def connect_to_prod(host, password=None):
        ...     print(f"Connecting to production: {host}")
        ...     # your db connection code here
        >>>
        >>> connect_to_prod("prod.example.com")  # Will prompt for master password

        >>> # With custom parameter name
        >>> @require_master_password('prod_api', param_name='api_key')
        >>> def call_prod_api(endpoint, api_key=None):
        ...     print(f"Calling production API: {endpoint}")
        ...     # your API call code here
        >>>
        >>> call_prod_api("/users")  # Will prompt for master password

        >>> # Pre-configured master password (use with caution!)
        >>> import os
        >>> MASTER_PASSWORD = os.getenv('MASTER_PASSWORD')
        >>> @require_master_password('prod_db', master_password=MASTER_PASSWORD)
        >>> def automated_backup(password=None):
        ...     # Automated task that needs master-protected password
        ...     pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Only inject if password not already provided
            if param_name not in kwargs or kwargs[param_name] is None:
                # Get master password (prompt if not provided)
                mp = master_password
                if mp is None:
                    prompt = prompt_message or f"Enter master password for '{key}': "
                    mp = getpass.getpass(prompt)

                # Retrieve password
                password = get_master_password(key, mp)
                if password is None:
                    raise ValueError(
                        f"Master-protected password not found for key '{key}' "
                        f"or incorrect master password"
                    )
                kwargs[param_name] = password

            return func(*args, **kwargs)

        return wrapper

    return decorator