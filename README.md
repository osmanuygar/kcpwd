# kcpwd

**Keychain Password Manager CLI & Library** - A simple, secure password manager for macOS that uses the native macOS Keychain. Can be used as both a command-line tool and a Python library.

## Features

-  Secure storage using macOS Keychain
-  Automatic clipboard copying
-  Simple CLI interface
-  Python library for programmatic access
-  Decorator support for automatic password injection
-  No passwords stored in plain text
-  Native macOS integration

## Installation

### From PyPI
```bash
pip install kcpwd
```

### From Source
```bash
git clone https://github.com/osmanuygar/kcpwd.git
cd kcpwd
pip install -e .
```

## Usage

### CLI Usage

#### Store a password
```bash
kcpwd set dbadmin asd123
```

#### Retrieve a password (copies to clipboard)
```bash
kcpwd get dbadmin
```

#### Delete a password
```bash
kcpwd delete dbadmin
```

#### List stored keys
```bash
kcpwd list
```

### Library Usage

#### Basic Functions

```python
from kcpwd import set_password, get_password, delete_password

# Store a password
set_password("my_database", "secret123")

# Retrieve a password
password = get_password("my_database")
print(password)  # Output: secret123

# Retrieve and copy to clipboard
password = get_password("my_database", copy_to_clip=True)

# Delete a password
delete_password("my_database")
```

#### Using Decorators (Recommended!)

The `@require_password` decorator automatically injects passwords from keychain:

```python
from kcpwd import require_password, set_password

# First, store your password
set_password("my_db", "secret123")

# Use the decorator to auto-inject password
@require_password('my_db')
def connect_to_database(host, username, password=None):
    print(f"Connecting to {host} as {username}")
    print(f"Password: {password}")
    # Your database connection code here
    return f"Connected with password: {password}"

# Call without password - it's automatically retrieved!
result = connect_to_database("localhost", "admin")
# Output: Connected with password: secret123
```

#### Advanced Decorator Usage

You can specify different parameter names:

```python
from kcpwd import require_password, set_password

# Store API key
set_password("github_api", "ghp_xxxxxxxxxxxx")

# Inject into custom parameter name
@require_password('github_api', param_name='api_key')
def call_github_api(endpoint, api_key=None):
    print(f"Calling GitHub API: {endpoint}")
    print(f"Using key: {api_key}")
    # Your API call code here
    return {"status": "success"}

# API key automatically retrieved from keychain
response = call_github_api("/user/repos")
```

#### Real-World Examples

**Database Connection:**
```python
#import psycopg2
from kcpwd import require_password, set_password

# Setup: Store password once
set_password("prod_db", "my_secure_password")

# Use in your code
@require_password('prod_db')
def get_db_connection(host, user, database, password=None):
    return psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )

# No need to handle password manually!
conn = get_db_connection(
    host="prod.example.com",
    user="dbuser",
    database="myapp"
)
```

**API Client:**
```python
import requests
from kcpwd import require_password, set_password

# Setup
set_password("api_token", "sk-xxxxxxxxxx")

@require_password('api_token', param_name='token')
def make_api_request(endpoint, token=None):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"https://api.example.com{endpoint}", headers=headers)
    return response.json()

# Token is automatically injected
data = make_api_request("/users")
```

**Email Sender:**
```python
import smtplib
from kcpwd import require_password, set_password

# Store email password
set_password("email_password", "your_email_password")

@require_password('email_password')
def send_email(to, subject, body, password=None):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login("your_email@gmail.com", password)
    
    message = f"Subject: {subject}\n\n{body}"
    server.sendmail("your_email@gmail.com", to, message)
    server.quit()
    
    return "Email sent!"

# Password automatically retrieved
send_email("friend@example.com", "Hello", "How are you?")
```

## How It Works

`kcpwd` stores your passwords in the **macOS Keychain** - the same secure, encrypted storage that Safari and other macOS apps use. This means:

-  Passwords are encrypted with your Mac's security
-  They persist across reboots
-  They're protected by your Mac's login password
-  No plain text files or databases
-  Can be accessed programmatically via Python

### Viewing Your Passwords

Open **Keychain Access** app and search for "kcpwd" to see all stored passwords.

Or use Terminal:
```bash
security find-generic-password -s "kcpwd" -a "dbadmin" -w
```

## API Reference

### Functions

#### `set_password(key: str, password: str) -> bool`
Store a password in macOS Keychain.
- Returns `True` if successful, `False` otherwise

#### `get_password(key: str, copy_to_clip: bool = False) -> Optional[str]`
Retrieve a password from macOS Keychain.
- `copy_to_clip`: If `True`, also copies password to clipboard
- Returns password string if found, `None` otherwise

#### `delete_password(key: str) -> bool`
Delete a password from macOS Keychain.
- Returns `True` if successful, `False` otherwise

#### `copy_to_clipboard(text: str) -> bool`
Copy text to macOS clipboard.
- Returns `True` if successful, `False` otherwise

### Decorators

#### `@require_password(key: str, param_name: str = 'password')`
Decorator that automatically injects password from keychain into function parameter.
- `key`: Keychain key to retrieve password from
- `param_name`: Parameter name to inject password into (default: `'password'`)
- Raises `ValueError` if password not found in keychain

## Security Notes

**Important Security Considerations:**

-  Passwords are stored in macOS Keychain (encrypted)
-  Passwords remain in clipboard until you copy something else
-  Consider clearing clipboard after use for sensitive passwords
-  Designed for personal use on trusted devices
-  Always use strong, unique passwords
-  Decorator usage means password is in memory during function execution

## Requirements

- **macOS only** (uses native Keychain)
- Python 3.8+

## Development

### Setup development environment
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Run tests
```bash
pytest
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## Disclaimer

This is a personal password manager tool. While it uses secure storage (macOS Keychain), please use at your own risk. For enterprise or critical password management, consider established solutions like 1Password, Bitwarden, or similar.

## Roadmap

- [x] Python library support
- [x] Decorator for automatic password injection
- [ ] Master password protection
- [ ] Auto-clear clipboard after X seconds
- [ ] Password generation
- [ ] Import/export functionality
- [ ] Password strength indicator
- [ ] Cross-platform support (Linux, Windows)

## Changelog

### v0.2.0
- Added Python library support
- Added `@require_password` decorator
- Refactored code into modular structure
- Enhanced API with better return types

### v0.1.0
- Initial CLI release
- Basic password storage and retrieval
- macOS Keychain integration