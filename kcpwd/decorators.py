"""
kcpwd.decorators - Decorators for automatic password management
"""

import functools
from typing import Callable, Any
from .core import get_password


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