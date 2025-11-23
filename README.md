# kcpwd

**Cross-platform Keychain Password Manager CLI & Library** - A simple, secure password manager for **macOS and Linux** that uses native system keyrings. Can be used as both a command-line tool and a Python library.

## Features

-  **Cross-platform**: Supports macOS and Linux
-  **Automatic Backend Selection**: System keyring or encrypted file fallback
-  **Works Everywhere**: Docker, CI/CD, headless servers - no dependencies!
-  Secure storage using native system keyring (macOS Keychain / Linux Secret Service)
-  **Master Password Protection (v0.4.0)** - Extra protection layer for sensitive passwords
-  Automatic clipboard copying (macOS) / optional on Linux
-  Cryptographically secure password generation
-  **Password Strength Checker (v0.4.1)** - Analyze password strength with detailed feedback
-  Import/Export functionality for backups
-  Simple CLI interface
-  Python library for programmatic access
-  **Decorator support** for automatic password injection (including master-protected passwords)
-  No passwords stored in plain text
-  Native OS integration when available

## Platform Support

### macOS
- ✅ Native macOS Keychain integration
- ✅ Automatic clipboard copying with `pbcopy`
- ✅ Full feature support

### Linux
- ✅ **Works immediately - no setup required!**
- ✅ Auto-detects system keyring (gnome-keyring, KWallet, etc.)
- ✅ Falls back to encrypted file storage if no keyring
- ✅ Optional clipboard support via `xclip`, `xsel`, or `wl-copy` (auto-detected)
- ✅ Perfect for Docker, CI/CD, headless servers
- 📦 Zero required dependencies (secretstorage optional for system keyring)

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

### Linux Requirements (Optional)

**kcpwd works out of the box on Linux!** For enhanced security with system keyring:

**Ubuntu/Debian:**
```bash
# Optional: System keyring (more secure)
sudo apt install gnome-keyring

# Optional: Clipboard support
sudo apt install xclip  # or xsel or wl-clipboard
```

**Fedora:**
```bash
# Optional: System keyring
sudo dnf install gnome-keyring

# Optional: Clipboard support
sudo dnf install xclip  # or xsel
```

**Arch:**
```bash
# Optional: System keyring
sudo pacman -S gnome-keyring

# Optional: Clipboard support
sudo pacman -S xclip  # or xsel
```

**Wayland users:**
```bash
# Use wl-clipboard for clipboard support
sudo apt install wl-clipboard  # Debian/Ubuntu
sudo dnf install wl-clipboard  # Fedora
sudo pacman -S wl-clipboard   # Arch
```

**What if I don't install anything?**
- ✅ kcpwd uses encrypted file backend (works everywhere!)
- ✅ AES-256-GCM encryption (secure)
- ✅ Perfect for Docker, CI/CD, headless servers
- ℹ️ Master password required (setup on first use)

**For KDE users:** KWallet provides Secret Service by default (system keyring available).

**Note**: Clipboard tools are optional. Without them, use shell pipes:
```bash
kcpwd get mykey | xclip -selection clipboard
```

## Quick Start

```bash
# Check platform support and configuration
kcpwd info

# Store a password
kcpwd set github_token ghp_xxxxxxxxxxxx

# Retrieve password (clipboard on macOS, stdout on Linux)
kcpwd get github_token

# On Linux, pipe to clipboard manually:
kcpwd get github_token | xclip -selection clipboard

# Generate strong password
kcpwd generate -l 20 -s myapp

# List all passwords
kcpwd list
```

## Usage

### Platform Information

```bash
# Check your platform configuration
kcpwd info

# Output example (Linux):
# 🔧 Platform Information
# ========================================
# Platform: Linux
# Supported: ✓ Yes
# Keyring Backend: D-Bus Secret Service (secretstorage)
# Clipboard: ✗ Disabled
# 
# 💡 Linux Notes:
#   • Clipboard is disabled (use shell pipes instead)
#   • Example: kcpwd get key | xclip -selection clipboard
#   • Requires D-Bus Secret Service (gnome-keyring, KWallet, etc.)
```

### CLI Usage

#### Store a password
```bash
# Regular password
kcpwd set dbadmin asd123

# With master password protection
kcpwd set prod_db secret --master-password

# Or shorthand:
kcpwd set-master prod_db secret123

# Check password strength before saving
kcpwd set myapi weak123 --check-strength
```

#### Retrieve a password

**macOS (automatic clipboard):**
```bash
kcpwd get dbadmin
# Output: ✓ Password for 'dbadmin' copied to clipboard
```

**Linux (stdout - pipe to clipboard):**
```bash
# Print to stdout
kcpwd get dbadmin

# Or pipe to clipboard (if xclip installed):
kcpwd get dbadmin | xclip -selection clipboard

# For Wayland (wl-clipboard):
kcpwd get dbadmin | wl-copy
```

**Both platforms - print to stdout:**
```bash
kcpwd get dbadmin --print
```

#### Master-protected passwords
```bash
# Set with master password
kcpwd set-master prod_db secret123

# Get with master password
kcpwd get-master prod_db

# Or use flag:
kcpwd get prod_db --master-password
```

#### Delete a password
```bash
kcpwd delete dbadmin
kcpwd delete-master prod_db  # for master-protected
```

#### List all passwords
```bash
kcpwd list
```

#### Generate passwords
```bash
# Generate with automatic strength check
kcpwd generate

# Generate and save
kcpwd generate -s myapi

# Generate 20-character password
kcpwd generate -l 20

# Generate without symbols
kcpwd generate --no-symbols

# Generate 6-digit PIN
kcpwd generate -l 6 --no-uppercase --no-lowercase --no-symbols
```

#### Check password strength
```bash
kcpwd check-strength "MyP@ssw0rd123"
```

#### Export/Import
```bash
# Export passwords
kcpwd export backup.json

# Import passwords
kcpwd import backup.json

# Dry run (preview)
kcpwd import backup.json --dry-run
```

### Library Usage

#### Basic Operations

```python
from kcpwd import set_password, get_password, delete_password

# Store password
set_password("my_database", "secret123")

# Retrieve password
password = get_password("my_database")
print(password)  # Output: secret123

# Delete password
delete_password("my_database")
```

#### Platform Detection

```python
from kcpwd import get_platform, get_platform_name, check_platform_requirements

# Get current platform
platform = get_platform()  # 'macos' or 'linux'
print(f"Running on: {get_platform_name()}")

# Check platform requirements
status = check_platform_requirements()
print(f"Supported: {status['supported']}")
print(f"Keyring: {status['keyring_backend']}")
print(f"Clipboard: {status['clipboard_available']}")
```

#### Master Password Protection

```python
from kcpwd.master_protection import (
    set_master_password,
    get_master_password,
    has_master_password,
    list_master_keys
)

# Store with master password
set_master_password("prod_db", "super_secret", "MyMasterPass123!")

# Retrieve
password = get_master_password("prod_db", "MyMasterPass123!")

# Check if master-protected
if has_master_password("prod_db"):
    print("This password needs master password")

# List all master-protected keys
keys = list_master_keys()
```

#### Password Strength Checker

```python
from kcpwd import check_password_strength

result = check_password_strength("MyP@ssw0rd123")
print(f"Score: {result['score']}/100")
print(f"Strength: {result['strength_text']}")

# Get feedback
for tip in result['feedback']:
    print(f"  - {tip}")
```

#### Decorators (including Master Password)

```python
from kcpwd import require_password, require_master_password

# Regular password decorator
@require_password('my_db')
def connect_to_db(host, password=None):
    print(f"Connecting with: {password}")

connect_to_db("localhost")  # Password auto-injected

# Master password decorator (will prompt)
@require_master_password('prod_db')
def connect_to_prod(host, password=None):
    print(f"Connecting to prod: {password}")

connect_to_prod("prod.example.com")  # Prompts for master password

# Automation mode (no prompt)
import os
MASTER_PASSWORD = os.getenv('MASTER_PASSWORD')

@require_master_password('prod_db', master_password=MASTER_PASSWORD)
def automated_task(password=None):
    # Runs without user interaction
    pass
```

## Security Details

- **Encryption**: AES-256-GCM (authenticated encryption)
- **Key Derivation**: PBKDF2-SHA256 with 600,000 iterations (OWASP 2023)
- **Storage**: 
  - macOS: Native Keychain
  - Linux: D-Bus Secret Service (gnome-keyring, KWallet)
- **Master Password**: Not stored anywhere (must be remembered)

## Platform-Specific Notes

### macOS
- Uses native Keychain Access
- Passwords accessible via: `security find-generic-password -s kcpwd -a <key> -w`
- Clipboard integration works automatically

### Linux
- Requires D-Bus Secret Service daemon (gnome-keyring, KWallet, etc.)
- Clipboard is **disabled by default** (security/dependency choice)
- Use shell pipes for clipboard: `kcpwd get key | xclip -selection clipboard`
- Works in both X11 and Wayland (with appropriate clipboard tools)

**Linux Clipboard Options:**
```bash
# X11 - xclip
kcpwd get key | xclip -selection clipboard

# X11 - xsel
kcpwd get key | xsel --clipboard

# Wayland - wl-clipboard
kcpwd get key | wl-copy
```

## Requirements

- Python 3.8+
- **macOS**: Built-in (no extra dependencies)
- **Linux**: 
  - D-Bus Secret Service daemon (gnome-keyring, KWallet, etc.)
  - `secretstorage>=3.3.0` (auto-installed)
- `cryptography>=41.0.0` (for master password protection)
- `click>=8.0.0` (for CLI)
- `keyring>=23.0.0` (for keyring abstraction)

## Troubleshooting

### Linux Issues

**"No secret service available"**
- Install gnome-keyring: `sudo apt install gnome-keyring`
- Make sure it's running: `gnome-keyring-daemon --start`
- For KDE: KWallet should work automatically

**"D-Bus error"**
- Check D-Bus is running: `ps aux | grep dbus`
- Set `DBUS_SESSION_BUS_ADDRESS` if needed

**Clipboard not working**
- Linux clipboard is disabled by design
- Use shell pipes: `kcpwd get key | xclip -selection clipboard`
- Install xclip: `sudo apt install xclip`

### macOS Issues

**"No passwords found" but they exist**
- Keychain might be locked
- Use Keychain Access app to verify
- Command: `security find-generic-password -s kcpwd`

## Changelog

### v0.5.0 (Current) - Linux Support and Encrypted File Backend
-  **New**: Full Linux support via D-Bus Secret Service
-  **New**: Platform detection and info command (`kcpwd info`)
-  **New**: Optional clipboard support on Linux (xclip, xsel, wl-copy auto-detection)
-  **New**: Encrypted file backend (AES-256-GCM) for universal compatibility
-  **New**: Automatic backend detection (system keyring → file fallback)
-  **New**: `get_backend_info()` API function
-  Linux uses `secretstorage` for keyring backend
-  Cross-platform clipboard with automatic fallback
-  Platform-agnostic keyring operations
-  Platform utilities module with feature detection 
-  Zero dependencies required on Linux
-  Master password for file backend (setup on first use)


### v0.4.1
-  `@require_master_password` decorator
-  Password strength checker with visual feedback
-  CLI `check-strength` command
-  `--check-strength` flag for `set` command

### v0.4.0
-  Per-password master password protection
-  AES-256-GCM encryption
-  PBKDF2-SHA256 key derivation (600k iterations)

### v0.3.0
-  Import/export functionality
-  `list` command

### v0.2.1
-  Password generation

### v0.2.0
-  Python library support
-  `@require_password` decorator

### v0.1.0
- 🎉 Initial release (macOS only)

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Platform-specific improvements especially appreciated.

## Roadmap

- [x] macOS support
- [x] Linux support (v0.5.0)
- [ ] Windows support (Windows Credential Locker)
- [ ] Optional clipboard on Linux (auto-detect xclip/wl-copy)
- [ ] GUI application
- [ ] Password history
- [ ] Browser extensions
- [ ] Multi-user support
- [ ] Cloud sync options
- [ ] Secret sharing
- [ ] Multi Node support 