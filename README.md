# kcpwd

**Keychain Password Manager CLI & Library** - A simple, secure password manager for macOS that uses the native macOS Keychain. Can be used as both a command-line tool and a Python library.

## Features

-  Secure storage using macOS Keychain
-  Automatic clipboard copying
-  Cryptographically secure password generation
-  **Import/Export functionality for backups**
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

#### List all stored passwords
```bash
kcpwd list
```

**Note:** The `list` command uses `security dump-keychain` which may take a few seconds and requires access to your keychain. If it shows "No passwords stored" but you know you have passwords, try using Keychain Access app to verify.

#### Generate a secure password
```bash
# Generate a 16-character password (default)
kcpwd generate

# Generate a 20-character password
kcpwd generate -l 20

# Generate without symbols (alphanumeric only)
kcpwd generate --no-symbols

# Generate and save immediately
kcpwd generate -s myapi

# Generate a 6-digit PIN
kcpwd generate -l 6 --no-uppercase --no-lowercase --no-symbols

# Generate without ambiguous characters (no 0/O, 1/l/I)
kcpwd generate --exclude-ambiguous
```

#### Export passwords (NEW!)
```bash
# Export all passwords to a JSON file
kcpwd export backup.json

# Export only key names (without passwords)
kcpwd export keys.json --keys-only

# Force overwrite existing file
kcpwd export backup.json -f
```

** Security Warning**: Exported files contain passwords in **PLAIN TEXT**. Keep them secure!

#### Import passwords (NEW!)
```bash
# Import passwords (skip existing keys)
kcpwd import backup.json

# Import and overwrite existing passwords
kcpwd import backup.json --overwrite

# Preview what would be imported without making changes
kcpwd import backup.json --dry-run
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

#### Password Generation

```python
from kcpwd import generate_password

# Generate a secure password
password = generate_password(length=20)
print(password)  # Output: 'aB3#xK9!mL2$nP5@qR7&'

# Generate alphanumeric password (no symbols)
password = generate_password(length=16, use_symbols=False)
print(password)  # Output: 'aB3xK9mL2nP5qR7t'

# Generate a 6-digit PIN
pin = generate_password(
    length=6, 
    use_uppercase=False, 
    use_lowercase=False, 
    use_symbols=False
)
print(pin)  # Output: '384729'
```

#### List All Keys (NEW!)

```python
from kcpwd import list_all_keys

# Get all stored password keys
keys = list_all_keys()
print(keys)  # Output: ['my_database', 'api_key', 'email_password']

# Check if a specific key exists
if 'my_database' in list_all_keys():
    print("Database password exists!")
```

#### Export/Import (NEW!)

```python
from kcpwd import export_passwords, import_passwords

# Export all passwords
result = export_passwords('backup.json')
print(f"Exported {result['exported_count']} passwords")

# Export only keys (without passwords)
result = export_passwords('keys_only.json', include_passwords=False)

# Import passwords (skip existing)
result = import_passwords('backup.json')
print(f"Imported {result['imported_count']} passwords")
print(f"Skipped {len(result['skipped_keys'])} existing keys")

# Import with overwrite
result = import_passwords('backup.json', overwrite=True)

# Dry run to preview import
result = import_passwords('backup.json', dry_run=True)
print(result['message'])
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

**Backup Script:**
```python
from kcpwd import export_passwords, import_passwords
import os
from datetime import datetime

def backup_passwords():
    """Create a timestamped backup of all passwords"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'passwords_backup_{timestamp}.json'
    
    result = export_passwords(backup_file)
    
    if result['success']:
        print(f"✓ Backup created: {backup_file}")
        print(f"  Exported {result['exported_count']} passwords")
        
        # Move to secure location
        secure_dir = os.path.expanduser('~/Documents/Backups')
        os.makedirs(secure_dir, exist_ok=True)
        os.rename(backup_file, os.path.join(secure_dir, backup_file))
    else:
        print(f"✗ Backup failed: {result['message']}")

def restore_passwords(backup_file):
    """Restore passwords from a backup"""
    # Preview first
    result = import_passwords(backup_file, dry_run=True)
    print(f"Preview: {result['message']}")
    
    # Confirm
    if input("Continue with import? (y/n): ").lower() == 'y':
        result = import_passwords(backup_file, overwrite=True)
        print(f"✓ {result['message']}")
    else:
        print("Import cancelled")
```

**Migration Script:**
```python
from kcpwd import export_passwords, import_passwords, list_all_keys

def migrate_to_new_machine(export_path='~/migration.json'):
    """Export passwords for migration to a new machine"""
    export_path = os.path.expanduser(export_path)
    
    result = export_passwords(export_path)
    
    if result['success']:
        print(f"✓ Exported {result['exported_count']} passwords")
        print(f"  File: {export_path}")
        print("\nOn your new machine, run:")
        print(f"  kcpwd import {export_path}")
    else:
        print(f"✗ Export failed: {result['message']}")

def complete_migration(import_path='~/migration.json'):
    """Complete migration on new machine"""
    import_path = os.path.expanduser(import_path)
    
    # Check existing passwords
    existing = list_all_keys()
    if existing:
        print(f"Found {len(existing)} existing passwords")
        print("Use --overwrite to replace them")
    
    # Import
    result = import_passwords(import_path)
    
    if result['success']:
        print(f"✓ {result['message']}")
        
        # Clean up migration file
        if input("Delete migration file? (y/n): ").lower() == 'y':
            os.remove(import_path)
            print("✓ Migration file deleted")
    else:
        print(f"✗ Import failed: {result['message']}")
```

## Export File Format

The export JSON file has the following structure:

```json
{
  "exported_at": "2025-01-15T10:30:00.123456",
  "service": "kcpwd",
  "version": "0.3.0",
  "include_passwords": true,
  "passwords": [
    {
      "key": "my_database",
      "password": "secret123"
    },
    {
      "key": "api_key",
      "password": "sk-xxxxxxxxxxxxx"
    }
  ]
}
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

#### `list_all_keys() -> List[str]`
List all stored password keys from macOS Keychain.
- Returns list of key names

#### `export_passwords(filepath: str, include_passwords: bool = True) -> Dict`
Export all passwords to a JSON file.
- `filepath`: Path to output JSON file
- `include_passwords`: If `True`, include passwords; if `False`, only keys
- Returns dict with `success`, `exported_count`, `failed_keys`, `message`

#### `import_passwords(filepath: str, overwrite: bool = False, dry_run: bool = False) -> Dict`
Import passwords from a JSON file.
- `filepath`: Path to JSON file to import
- `overwrite`: If `True`, overwrite existing passwords
- `dry_run`: If `True`, preview without importing
- Returns dict with `success`, `imported_count`, `skipped_keys`, `failed_keys`, `message`

#### `copy_to_clipboard(text: str) -> bool`
Copy text to macOS clipboard.
- Returns `True` if successful, `False` otherwise

#### `generate_password(length=16, use_uppercase=True, use_lowercase=True, use_digits=True, use_symbols=True, exclude_ambiguous=False) -> str`
Generate a cryptographically secure random password.
- `length`: Password length (minimum 4)
- `use_uppercase`: Include uppercase letters
- `use_lowercase`: Include lowercase letters  
- `use_digits`: Include digits
- `use_symbols`: Include symbols (!@#$%^&*...)
- `exclude_ambiguous`: Exclude ambiguous characters (0/O, 1/l/I)
- Returns generated password string


### Decorators

#### `@require_password(key: str, param_name: str = 'password')`
Decorator that automatically injects password from keychain into function parameter.
- `key`: Keychain key to retrieve password from
- `param_name`: Parameter name to inject password into (default: `'password'`)
- Raises `ValueError` if password not found in keychain

## Security Notes

**Important Security Considerations:**

-  Passwords are stored in macOS Keychain (encrypted)
-  **Export files contain passwords in PLAIN TEXT** - keep them secure!
-  Passwords remain in clipboard until you copy something else
-  Consider clearing clipboard after use for sensitive passwords
-  Designed for personal use on trusted devices
-  Always use strong, unique passwords
-  Decorator usage means password is in memory during function execution
-  Delete export files after use or store them encrypted
-  Never commit export files to version control

## Requirements

- **macOS only** (uses native Keychain)
- Python 3.8+ 

## Development

### Setup development environment
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
```

### Run tests
```bash
pytest
```

## Troubleshooting

### `kcpwd list` shows "No passwords stored" but passwords exist

The `list` command uses `security dump-keychain` which:
- May take 5-10 seconds to complete
- Requires keychain access permissions
- May not work if keychain is locked

**Solutions:**
1. Make sure your keychain is unlocked
2. Try accessing passwords directly: `kcpwd get <keyname>`
3. Use Keychain Access app: Open Keychain Access → Search for "kcpwd"
4. Check with terminal: `security find-generic-password -s kcpwd`

If you can get passwords with `kcpwd get` but `list` doesn't work, your passwords are safe and accessible - the list feature just has trouble parsing `security dump-keychain` output on some macOS versions.

### Export fails or returns empty

If `kcpwd export` shows 0 passwords exported but you have passwords:
1. Unlock your keychain
2. The export depends on `list_all_keys()` - use the workarounds above
3. Alternatively, manually export keys you know: Store them in a text file and import later

### Import issues

- **"Cannot import: file contains only keys"**: The export file was created with `--keys-only` flag. Re-export with passwords.
- **"Invalid JSON"**: Check file format, make sure it's valid JSON
- **Skipped existing**: This is normal with default behavior. Use `--overwrite` to replace existing passwords

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## Disclaimer

This is a personal password manager tool. While it uses secure storage (macOS Keychain), please use at your own risk. For enterprise or critical password management, consider established solutions like 1Password, Bitwarden, or similar.

## Roadmap

- [x] Python library support
- [x] Decorator for automatic password injection
- [x] Password generation
- [x] Import/export functionality
- [ ] Master password protection
- [ ] Password strength indicator
- [ ] Cross-platform support (Linux, Windows)
- [ ] GUI web UI application
- [ ] Multi Node/user support
- [ ] Integration with other password managers
- [ ] Two-factor authentication support
- [ ] MultiSite password management
- [ ] Encrypted export files

## Changelog

### v0.3.0
- Added import/export functionality for password backups
- Added `list` command to display all stored keys
- Added `list_all_keys()` function for programmatic access
- Improved security warnings for export operations
- Added dry-run mode for safe import preview
- Comprehensive import/export tests

### v0.2.1
- Added cryptographically secure password generation (`generate` command)
- Generate passwords with customizable length and character types
- Option to exclude ambiguous characters (0/O, 1/l/I)
- Generate and save passwords in one command
- Comprehensive password generation tests

### v0.2.0
- Added Python library support
- Added `@require_password` decorator
- Refactored code into modular structure
- Enhanced API with better return types

### v0.1.0
- Initial CLI release
- Basic password storage and retrieval
- macOS Keychain integration