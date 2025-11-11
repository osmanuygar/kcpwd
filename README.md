# kcpwd

**Keychain Password Manager CLI & Library** - A simple, secure password manager for macOS that uses the native macOS Keychain. Can be used as both a command-line tool and a Python library.

## Features

-  Secure storage using macOS Keychain
-  **Master Password Protection (v0.4.0)** - Extra protection layer for sensitive passwords
-  Automatic clipboard copying
-  Cryptographically secure password generation
-  Import/Export functionality for backups
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
# Regular password
kcpwd set dbadmin asd123

# or shorthand:
kcpwd set-master prod_db secret123
```

#### Retrieve a password (copies to clipboard)
```bash
# Regular password
kcpwd get dbadmin

# or shorthand:
kcpwd get-master prod_db
```

#### Delete a password
```bash
# Regular password
kcpwd delete dbadmin

# Master-protected password
kcpwd delete-master prod_db
```

#### List all stored passwords
```bash
kcpwd list

# Shows:
# Regular passwords (3):
#   • dbadmin
#   • api_key
#   • test_db
#
# 🔒 Master-protected passwords (2):
#   • prod_db 🔒
#   • production_api 🔒
```

**Note:** The `list` command shows regular and master-protected passwords separately. Master-protected passwords require the master password to retrieve.

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

# Generate and save with master password
kcpwd generate -s prod_api --master-password

# Generate a 6-digit PIN
kcpwd generate -l 6 --no-uppercase --no-lowercase --no-symbols

# Generate without ambiguous characters (no 0/O, 1/l/I)
kcpwd generate --exclude-ambiguous
```

#### Export passwords
```bash
# Export all regular passwords to a JSON file
kcpwd export backup.json

# Export only key names (without passwords)
kcpwd export keys.json --keys-only

# Force overwrite existing file
kcpwd export backup.json -f
```

**⚠️ Security Warning**: 
- Exported files contain passwords in **PLAIN TEXT**. Keep them secure!
- **Master-protected passwords are NOT included in exports** for security reasons.

#### Import passwords
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

#### Master Password Protection (NEW in v0.4.0!)

```python
from kcpwd.master_protection import (
    set_master_password,
    get_master_password,
    delete_master_password,
    has_master_password,
    list_master_keys
)

# Store password with master password protection
set_master_password("prod_db", "super_secret", "MyMasterPass123!")

# Retrieve master-protected password
password = get_master_password("prod_db", "MyMasterPass123!")
print(password)  # Output: super_secret

# Wrong master password returns None
password = get_master_password("prod_db", "WrongPassword")
print(password)  # Output: None

# Check if a key has master password protection
if has_master_password("prod_db"):
    print("This password is master-protected")

# List all master-protected keys
keys = list_master_keys()
print(keys)  # Output: ['prod_db', 'prod_api']

# Delete master-protected password
delete_master_password("prod_db")
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

#### List All Keys

```python
from kcpwd import list_all_keys
from kcpwd.master_protection import list_master_keys

# Get all regular password keys
keys = list_all_keys()
print(keys)  # Output: ['my_database', 'api_key', 'email_password']

# Get all master-protected keys
master_keys = list_master_keys()
print(master_keys)  # Output: ['prod_db', 'prod_api']

# Check if a specific key exists
if 'my_database' in list_all_keys():
    print("Database password exists!")
```

#### Export/Import

```python
from kcpwd import export_passwords, import_passwords

# Export all regular passwords
result = export_passwords('backup.json')
print(f"Exported {result['exported_count']} passwords")

# Note: Master-protected passwords are NOT included in exports

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

#### Using Decorators

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

**Note**: Decorator currently works only with regular passwords, not master-protected ones.


### Security Details

- **Encryption**: AES-256-GCM (authenticated encryption)
- **Key Derivation**: PBKDF2-SHA256 with 600,000 iterations (OWASP 2023)
- **Storage**: Separate keychain service (`kcpwd-master`)
- **Master Password**: Not stored anywhere (must be remembered)

### Important Notes

 **Master Password is NOT backed up by kcpwd**
- If you forget your master password, master-protected passwords **CANNOT be recovered**
- Store your master password in a safe place (paper backup, different password manager)
- Each master-protected password is independently encrypted

 **Master-protected passwords are NOT exported**
- This is intentional for security
- Export only includes regular passwords
- Use separate backup strategy for production credentials

## Export File Format

The export JSON file has the following structure:

```json
{
  "exported_at": "2025-01-15T10:30:00.123456",
  "service": "kcpwd",
  "version": "0.4.0",
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

**Note**: Master-protected passwords are not included in exports.

## How It Works

`kcpwd` stores your passwords in the **macOS Keychain** - the same secure, encrypted storage that Safari and other macOS apps use. This means:

-  Passwords are encrypted with your Mac's security
-  They persist across reboots
-  They're protected by your Mac's login password
-  No plain text files or databases
-  Can be accessed programmatically via Python
-  **Master-protected passwords have an additional AES-256 encryption layer** (v0.4.0)

### Viewing Your Passwords

Open **Keychain Access** app and search for "kcpwd" to see regular passwords.
Search for "kcpwd-master" to see master-protected entries (encrypted data).

Or use Terminal:
```bash
# Regular password
security find-generic-password -s "kcpwd" -a "dbadmin" -w

# Master-protected (shows encrypted data)
security find-generic-password -s "kcpwd-master" -a "prod_db" -w
```

## API Reference

### Regular Password Functions

#### `set_password(key: str, password: str) -> bool`
Store a password in macOS Keychain.

#### `get_password(key: str, copy_to_clip: bool = False) -> Optional[str]`
Retrieve a password from macOS Keychain.

#### `delete_password(key: str) -> bool`
Delete a password from macOS Keychain.

#### `list_all_keys() -> List[str]`
List all regular password keys.

### Master Password Functions (NEW in v0.4.0)

#### `set_master_password(key: str, password: str, master_password: str) -> bool`
Store password with master password protection.
- `key`: Password identifier
- `password`: The actual password to store
- `master_password`: Master password to encrypt with

#### `get_master_password(key: str, master_password: str) -> Optional[str]`
Retrieve master-protected password.
- Returns `None` if key not found or wrong master password

#### `delete_master_password(key: str) -> bool`
Delete master-protected password.

#### `has_master_password(key: str) -> bool`
Check if key is master-protected.

#### `list_master_keys() -> List[str]`
List all master-protected keys.

### Other Functions

#### `copy_to_clipboard(text: str) -> bool`
Copy text to macOS clipboard.

#### `generate_password(length=16, use_uppercase=True, use_lowercase=True, use_digits=True, use_symbols=True, exclude_ambiguous=False) -> str`
Generate a cryptographically secure random password.

#### `export_passwords(filepath: str, include_passwords: bool = True) -> Dict`
Export regular passwords to JSON file.
**Note**: Does not include master-protected passwords.

#### `import_passwords(filepath: str, overwrite: bool = False, dry_run: bool = False) -> Dict`
Import passwords from JSON file.

### Decorators

#### `@require_password(key: str, param_name: str = 'password')`
Decorator that automatically injects password from keychain.

## Security Notes

**Important Security Considerations:**

### Master Password Protection (v0.4.0)
-  Master password adds AES-256-GCM encryption layer
-  Uses PBKDF2-SHA256 with 600,000 iterations (OWASP 2023)
-  **Master password is NOT backed up** - keep it safe!
-  Each password independently encrypted with unique salt/nonce
-  Master-protected passwords excluded from exports

### General Security
-  Regular passwords stored in macOS Keychain (encrypted by macOS)
-  Export files contain regular passwords in **PLAIN TEXT** - keep secure!
-  Passwords remain in clipboard until you copy something else
-  Consider clearing clipboard after use for sensitive passwords
-  Designed for personal use on trusted devices
-  Always use strong, unique passwords
-  Delete export files immediately after use
-  Never commit export files to version control

## Requirements

- **macOS only** (uses native Keychain)
- Python 3.8+ 
- cryptography>=41.0.0 (for master password protection)

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
pytest -v  # verbose
pytest test/test_master.py  # master password tests only
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

### Master Password Issues (v0.4.0)

**"No password found or incorrect master password"**
- Check you're using the correct master password
- Master password is case-sensitive
- If forgotten, password cannot be recovered

**"Passwords do not match" when setting**
- Retype carefully
- Make sure both prompts get same password

### Export/Import issues

**Export shows fewer passwords than expected**
- Master-protected passwords are NOT included in exports (by design)
- Use `kcpwd list` to see all passwords

**Import fails**
- Check JSON file format is valid
- Ensure file has `passwords` array
- Master-protected passwords cannot be imported

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## Disclaimer

This is a personal password manager tool. While it uses secure storage (macOS Keychain) and strong encryption for master-protected passwords (AES-256-GCM), please use at your own risk. For enterprise or critical password management, consider established solutions like 1Password, Bitwarden, or similar.

## Roadmap

- [x] Python library support
- [x] Decorator for automatic password injection
- [x] Password generation
- [x] Import/export functionality
- [x] Master password protection (v0.4.0) 
- [ ] Password strength indicator
- [ ] Decorator support for master-protected passwords
- [ ] Cross-platform support (Linux, Windows)
- [ ] GUI web UI application
- [ ] Multi user support
- [ ] Integration with other password managers
- [ ] Two-factor authentication support

## Changelog

### v0.4.0 (Current)
- ** Added per-password master password protection**
- Each password can optionally be protected with master password
- AES-256-GCM authenticated encryption for master-protected passwords
- PBKDF2-SHA256 key derivation with 600,000 iterations (OWASP 2023)
- New commands: `set-master`, `get-master`, `delete-master` for easier usage
- CLI flags: `--master-password` / `-m` for set/get/generate commands
- Master-protected passwords shown separately in `list` command
- Master-protected passwords excluded from exports (security feature)
- New `kcpwd.master` module with dedicated functions

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