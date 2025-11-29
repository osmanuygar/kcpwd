<p align="left">
  <img src="kcpwd/ui/static/kcpwd_logo.png" alt="kcpwd Logo" width="200"/>
</p>

[![PyPI version](https://img.shields.io/pypi/v/kcpwd.svg)](https://pypi.org/project/kcpwd/)
[![Python Version](https://img.shields.io/pypi/pyversions/kcpwd.svg)](https://pypi.org/project/kcpwd/)
[![License](https://img.shields.io/pypi/l/kcpwd.svg)]  
# kcpwd

**Cross-platform Keychain Password Manager CLI, Library & Web UI** - A powerful password manager for **macOS and Linux** with native system keyring support, modern web interface, and **temporary password sharing**.

## ✨ Features

-  **🌐 Modern Web UI** - Beautiful, professional dark mode interface with FastAPI backend
-  **🔗 NEW: Password Sharing** - Pastebin-style temporary share links (5m-3h)
-  **Cross-platform**: Supports macOS and Linux
-  **Automatic Backend Selection**: System keyring or encrypted file fallback
-  **Works Everywhere**: Docker, CI/CD, headless servers - no dependencies!
-  Secure storage using native system keyring (macOS Keychain / Linux Secret Service)
-  **Master Password Protection** - Extra protection layer for sensitive passwords
-  Automatic clipboard copying (macOS) / optional on Linux
-  Cryptographically secure password generation
-  **Password Strength Checker** - Analyze password strength with detailed feedback
-  **Professional Dark Theme** - Corporate-grade dark mode UI
-  Import/Export functionality for backups
-  Simple CLI interface
-  Python library for programmatic access
-  **Decorator support** for automatic password injection
-  No passwords stored in plain text
-  Native OS integration when available


**Example:**
```python
# API usage
import requests

response = requests.post("http://localhost:8765/api/share/create",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "key": "github_token",
        "duration": "1h",
        "access_type": "once"
    })

share_url = response.json()["share_url"]
# http://localhost:8765/s/Xy9kL2mN4pQ6rS8t
```

## Platform Support

### macOS
- ✅ Native macOS Keychain integration
- ✅ Automatic clipboard copying with `pbcopy`
- ✅ Full feature support
- ✅ Web UI support
- ✅ Password sharing

### Linux
- ✅ **Works immediately - no setup required!**
- ✅ Auto-detects system keyring (gnome-keyring, KWallet, etc.)
- ✅ Falls back to encrypted file storage if no keyring
- ✅ Optional clipboard support via `xclip`, `xsel`, or `wl-copy` (auto-detected)
- ✅ Perfect for Docker, CI/CD, headless servers
- ✅ Web UI support
- ✅ Password sharing
- 📦 Zero required dependencies (secretstorage optional for system keyring)

## Installation

### Basic Installation
```bash
pip install kcpwd
```

### With Web UI (Recommended)
```bash
pip install 'kcpwd[ui]'
```

### From Source
```bash
git clone https://github.com/osmanuygar/kcpwd.git
cd kcpwd
pip install -e .[ui]  # Install with UI support
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

## Quick Start

### CLI Usage

```bash
# Check platform support and configuration
kcpwd info

# Store a password
kcpwd set github_token ghp_xxxxxxxxxxxx

# Retrieve password (clipboard on macOS, stdout on Linux)
kcpwd get github_token

# Generate strong password
kcpwd generate -l 20 -s myapp

# List all passwords
kcpwd list
```

### 🌐 Web UI Usage

```bash
# Start the web UI
kcpwd ui

# Custom port
kcpwd ui --port 8000

# With persistent secret
export KCPWD_UI_SECRET="your-secure-secret"
kcpwd ui
```

Then open your browser to `http://localhost:8765` and enter the UI secret shown in the terminal.

**Web UI Features:**
- 📋 View and manage all passwords
- 🔍 Search passwords instantly
- ➕ Add new passwords with strength checking
- 🎲 Generate secure passwords with custom rules
- 🔗 **Share passwords temporarily** (NEW!)
- 📤 Export/Import for backups
- 🔒 Master password support
- 📊 Real-time statistics
- 🎨 Professional dark mode theme

### 🔗 Password Sharing Usage

**Via Web UI:**
1. Navigate to Share tab
2. Select password to share
3. Configure:
   - Duration (5m - 3h)
   - Access type (anyone/once/password)
   - Optional: Max views, access password
4. Copy and share the link

**Via API:**
```python
import requests

# Authenticate
auth = requests.post("http://localhost:8765/api/auth",
    json={"secret": "your-ui-secret"})
token = auth.json()["token"]

# Create share
share = requests.post("http://localhost:8765/api/share/create",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "key": "my_password",
        "duration": "30m",
        "access_type": "once",
        "max_views": 1
    })

print(share.json()["share_url"])
# Output: http://localhost:8765/s/AbC123XyZ
```

**Access share (no auth needed):**
```bash
# Browser
http://localhost:8765/s/AbC123XyZ

# API
curl http://localhost:8765/s/AbC123XyZ/access
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
# 🔐 Storage Backend
# ========================================
# Type: System Keyring
# Backend: SecretService Keyring
# Status: ✓ Active (OS-native secure storage)
```

### CLI Commands

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

#### Web UI
```bash
# Start web UI (default: http://127.0.0.1:8765)
kcpwd ui

# Custom host and port
kcpwd ui --host 0.0.0.0 --port 8000

# Set persistent secret
export KCPWD_UI_SECRET="my-secure-secret-key"
kcpwd ui

# Open browser automatically (default: yes)
kcpwd ui --no-open-browser  # Don't open browser
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

#### Decorators

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
```

### 🌐 Web UI API (Programmatic Access)

The Web UI also exposes a REST API that you can use programmatically:

```python
import requests

# Authenticate
response = requests.post("http://localhost:8765/api/auth", 
    json={"secret": "your-ui-secret"})
token = response.json()["token"]

headers = {"Authorization": f"Bearer {token}"}

# List passwords
response = requests.get("http://localhost:8765/api/passwords", headers=headers)
passwords = response.json()

# Get a password
response = requests.post("http://localhost:8765/api/passwords/retrieve",
    headers=headers,
    json={"key": "my_password", "use_master": False})
password = response.json()["password"]

# Generate password
response = requests.post("http://localhost:8765/api/generate",
    headers=headers,
    json={"length": 20, "use_symbols": True})
new_password = response.json()["password"]

# Create share link (NEW!)
response = requests.post("http://localhost:8765/api/share/create",
    headers=headers,
    json={
        "key": "my_password",
        "duration": "1h",
        "access_type": "once"
    })
share_url = response.json()["share_url"]
```
### 🔗 Password Sharing (NEW in v0.6.4!)

Create temporary, secure links to share passwords:

```bash
# Via Web UI
1. Go to Share tab
2. Select password
3. Choose duration (5m, 15m, 30m, 1h, 3h)
4. Select access type (anyone/once/password)
5. Click "Create Share Link"
```
## Security Details

- **Encryption**: AES-256-GCM (authenticated encryption)
- **Key Derivation**: PBKDF2-SHA256 with 600,000 iterations (OWASP 2023)
- **Storage**: 
  - macOS: Native Keychain
  - Linux: D-Bus Secret Service (gnome-keyring, KWallet)
  - Fallback: Encrypted file (AES-256-GCM)
- **Master Password**: Not stored anywhere (must be remembered)
- **Web UI**: Session-based authentication with secure tokens
- **API**: Bearer token authentication
- **Password Sharing**:
  - 128-bit random share IDs
  - Short-lived by design (max 3 hours)
  - Auto-expiration with background cleanup
  - Optional password protection
  - Access logging (IP, timestamp, user agent)

## Platform-Specific Notes

### macOS
- Uses native Keychain Access
- Passwords accessible via: `security find-generic-password -s kcpwd -a <key> -w`
- Clipboard integration works automatically
- Web UI runs on localhost by default

### Linux
- Requires D-Bus Secret Service daemon (gnome-keyring, KWallet, etc.)
- Falls back to encrypted file if no keyring available
- Clipboard is **disabled by default** (security/dependency choice)
- Use shell pipes for clipboard: `kcpwd get key | xclip -selection clipboard`
- Works in both X11 and Wayland (with appropriate clipboard tools)
- Web UI works perfectly on all Linux distributions

## Web UI Configuration

### Environment Variables

```bash
# UI Secret (recommended to set)
export KCPWD_UI_SECRET="your-secure-random-string"

# Host (default: 127.0.0.1)
export KCPWD_UI_HOST="0.0.0.0"

# Port (default: 8765)
export KCPWD_UI_PORT="8000"

# Enable CORS for separate frontend (default: false)
export KCPWD_UI_CORS="true"

# Debug mode (default: false)
export KCPWD_UI_DEBUG="true"
```

### Deployment

**Development:**
```bash
kcpwd ui
```

**Production (with gunicorn):**
```bash
pip install gunicorn
gunicorn kcpwd.ui.api:app --bind 0.0.0.0:8765 --workers 4
```

**Docker:**
```dockerfile
FROM python:3.11-slim
RUN pip install kcpwd[ui]
ENV KCPWD_UI_SECRET="change-me"
CMD ["kcpwd", "ui", "--host", "0.0.0.0"]
```

**Systemd Service:**
```ini
[Unit]
Description=kcpwd Web UI
After=network.target

[Service]
Type=simple
User=youruser
Environment="KCPWD_UI_SECRET=your-secret"
ExecStart=/usr/local/bin/kcpwd ui --host 127.0.0.1
Restart=always

[Install]
WantedBy=multi-user.target
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
- **Web UI** (optional):
  - `fastapi>=0.104.0`
  - `uvicorn[standard]>=0.24.0`
  - `pydantic>=2.0.0`

## Troubleshooting

### Web UI Issues

**"UI files not found"**
- Make sure you installed with `[ui]` extra: `pip install kcpwd[ui]`
- Check if files exist: `ls ~/.local/lib/python*/site-packages/kcpwd/ui/static/`

**"Cannot connect to UI"**
- Check if port is available: `lsof -i :8765`
- Try different port: `kcpwd ui --port 8000`
- Check firewall settings

**"Session expired"**
- Sessions expire after 1 hour by default
- Just re-authenticate with your UI secret

### Password Sharing Issues

**"Share link not working"**
- Check if sharing is enabled: look for "🔗 Sharing: ENABLED" in server logs
- Verify link hasn't expired
- Check if max views reached (for limited shares)

**"Cannot create share"**
- Ensure you're authenticated
- Check password exists
- Verify duration and access type are valid

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

### v0.6.4 (Current) - Password Sharing & Professional Dark Mode
-  **NEW: Password Sharing** - Pastebin-style temporary share links
-  **NEW: Professional Dark Theme** - Corporate-grade dark mode UI
-  Temporary share links (5m, 15m, 30m, 1h, 3h)
-  Three access modes: anyone, one-time, password-protected
-  Beautiful share access pages with QR codes
-  Auto-expiration with background cleanup
-  Access logging and statistics
-  Share management tab in Web UI
-  REST API for password sharing
-  Zero new dependencies

### v0.6.3 - Web UI & Enhanced Features
-  Modern Web UI with FastAPI backend
-  Beautiful, responsive interface for password management
-  Real-time password strength visualization
-  Interactive password generator with live preview
-  Import/Export via Web UI
-  Session-based authentication
-  Enhanced UI with logo
-  REST API for programmatic access
-  Improved documentation and examples
-  Better error handling and user feedback

### v0.5.0 - Linux Support and Encrypted File Backend
-   Full Linux support via D-Bus Secret Service
-   Platform detection and info command (`kcpwd info`)
-   Optional clipboard support on Linux
-   Encrypted file backend for universal compatibility
-   Automatic backend detection
-   `get_backend_info()` API function

### v0.4.1
-  `@require_master_password` decorator
-  Password strength checker with visual feedback
-  CLI `check-strength` command

### v0.4.0
-  Per-password master password protection
-  AES-256-GCM encryption
-  PBKDF2-SHA256 key derivation

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

Contributions welcome! Platform-specific improvements, Web UI enhancements, and password sharing features especially appreciated.

### Development Setup

```bash
# Clone repository
git clone https://github.com/osmanuygar/kcpwd.git
cd kcpwd

# Install development dependencies
pip install -e .[dev,ui]

# Run tests
pytest

# Code formatting
black kcpwd/
ruff check kcpwd/

# Type checking
mypy kcpwd/
```

## Roadmap

- [x] macOS support
- [x] Linux support
- [x] Password strength checker
- [x] Master password protection
- [x] Web UI with FastAPI
- [x] Password sharing (temporary links)
- [x] Professional dark mode
- [ ] Windows support (Windows Credential Locker)
- [ ] Password history tracking
- [ ] Browser extensions
- [ ] Multi-user support
- [ ] Cloud sync options
- [ ] 2FA/OTP support
- [ ] QR code generation for shares
- [ ] Email notifications on share access
- [ ] Mobile apps
- [ ] Multi node sync
- [ ] Advanced reporting and analytics



### Password Sharing Scenarios

1. **Emergency Production Access**
   ```bash
   # Create 15-minute one-time link for on-call engineer
   kcpwd ui
   # Share tab → prod_db → 15m → once → Create
   ```

2. **Client API Key Handoff**
   ```bash
   # Password-protected 3-hour share
   kcpwd ui
   # Share tab → client_api_key → 3h → password → Create
   ```

3. **Team Onboarding**
   ```bash
   # 1-hour link for initial credentials
   kcpwd ui
   # Share tab → staging_creds → 1h → anyone → Create
   ```

4. **Support Password Reset**
   ```bash
   # 30-minute temporary password
   kcpwd ui
   # Share tab → temp_reset → 30m → once → Create
   ```

## Screenshots

### CLI
```bash
$ kcpwd info
🔧 Platform Information
========================================
Platform: Linux
Supported: ✓ Yes
🔐 Storage Backend
========================================
Type: System Keyring
Backend: SecretService Keyring
Status: ✓ Active (OS-native secure storage)
```

### Web UI
Beautiful, professional dark mode interface:
- 🎨 Corporate-grade dark theme
- 📱 Responsive design
- 💪 Real-time password strength
- 🎲 Interactive password generator
- 🔗 Password sharing with beautiful access pages
- 🔒 Secure session management
- 📊 Statistics and monitoring

## Support

-  [Documentation](https://github.com/osmanuygar/kcpwd)
-  [Issue Tracker](https://github.com/osmanuygar/kcpwd/issues)
-  [Discussions](https://github.com/osmanuygar/kcpwd/discussions)

## Star History

If you find kcpwd useful, please ⭐ star the repository!

---

Made with ❤️ by [osmanuygar](https://github.com/osmanuygar)