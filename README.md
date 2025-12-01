<p align="left">
  <img src="kcpwd/ui/static/kcpwd_logo.png" alt="kcpwd Logo" width="200"/>
</p>

[![PyPI version](https://img.shields.io/pypi/v/kcpwd.svg)](https://pypi.org/project/kcpwd/)
[![Python Version](https://img.shields.io/pypi/pyversions/kcpwd.svg)](https://pypi.org/project/kcpwd/)
[![License](https://img.shields.io/pypi/l/kcpwd.svg)]  
# kcpwd

**Cross-platform Keychain Password Manager CLI, Library & Web UI** - A powerful password manager for **macOS, Linux, and Windows** with native system keyring support and modern web interface.

## ✨ Features

-  **🌐 NEW: Modern Web UI** - Beautiful web interface with FastAPI backend
-  **🪟 NEW: Windows Support** - Native Windows Credential Locker integration
-  **Cross-platform**: Supports macOS, Linux, and Windows
-  **Automatic Backend Selection**: System keyring or encrypted file fallback
-  **Works Everywhere**: Docker, CI/CD, headless servers - no dependencies!
-  Secure storage using native system keyring (macOS Keychain / Linux Secret Service / Windows Credential Locker)
-  **Master Password Protection** - Extra protection layer for sensitive passwords
-  Automatic clipboard copying on all platforms
-  Cryptographically secure password generation
-  **Password Strength Checker** - Analyze password strength with detailed feedback
-  **Password Sharing** - Secure temporary password sharing with expiration
-  Import/Export functionality for backups
-  Simple CLI interface
-  Python library for programmatic access
-  **Decorator support** for automatic password injection
-  No passwords stored in plain text
-  Native OS integration when available


## Platform Support

### macOS
- ✅ Native macOS Keychain integration
- ✅ Automatic clipboard copying with `pbcopy`
- ✅ Full feature support
- ✅ Web UI support

### Linux
- ✅ **Works immediately - no setup required!**
- ✅ Auto-detects system keyring (gnome-keyring, KWallet, etc.)
- ✅ Falls back to encrypted file storage if no keyring
- ✅ Optional clipboard support via `xclip`, `xsel`, or `wl-copy` (auto-detected)
- ✅ Perfect for Docker, CI/CD, headless servers
- ✅ Web UI support
- 📦 Zero required dependencies (secretstorage optional for system keyring)

### Windows
- ✅ **Native Windows Credential Locker integration**
- ✅ Automatic clipboard copying via `clip.exe` or `pywin32`
- ✅ Full feature support
- ✅ Web UI support
- ✅ Works on Windows 10, 11, and Server editions
- 📦 Optional `pywin32` for enhanced clipboard support

## Installation

### Basic Installation
```bash
pip install kcpwd
```

### With Web UI
```bash
pip install 'kcpwd[ui]'
```

### Windows Enhanced (Recommended)
```bash
pip install 'kcpwd[ui]'
pip install pywin32  # For better clipboard support
```

### From Source
```bash
git clone https://github.com/osmanuygar/kcpwd.git
cd kcpwd
pip install -e .[ui]  # Install with UI support
```

### Platform-Specific Requirements

#### Linux (Optional)

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

#### Windows (Optional)

For enhanced clipboard support:
```bash
pip install pywin32
```

**Note:** Windows Credential Locker is built into Windows 10/11, no additional setup needed!

## Quick Start

### CLI Usage

```bash
# Check platform support and configuration
kcpwd info

# Store a password
kcpwd set github_token ghp_xxxxxxxxxxxx

# Retrieve password (copies to clipboard automatically)
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
- 📤 Export/Import for backups
- 🔒 Master password support
- 🔗 Secure password sharing
- 📊 Real-time statistics

## Usage

### Platform Information

```bash
# Check your platform configuration
kcpwd info

# Output example (Windows):
# 🔧 Platform Information
# ========================================
# Platform: macOS
# Supported: ✓ Yes
# 🔐 Storage Backend
# ========================================
# Type: System Keyring
# Backend: Keyring
# Status: ✓ Active (OS-native secure storage)
#📋 Clipboard
#========================================
#Status: ✓ Available
#
#💡 macOS Notes:
#  • Using macOS Keychain (native integration)
#  • View passwords: Keychain Access app
#  • Command line: security find-generic-password -s kcpwd
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

**All platforms (automatic clipboard):**
```bash
kcpwd get dbadmin
# Output: ✓ Password for 'dbadmin' copied to clipboard
```

**Print to stdout (all platforms):**
```bash
kcpwd get dbadmin --print
```

**Linux - pipe to clipboard:**
```bash
# For X11 (if xclip installed):
kcpwd get dbadmin | xclip -selection clipboard

# For Wayland (wl-clipboard):
kcpwd get dbadmin | wl-copy
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

#### Password Sharing
```bash
# Share a password temporarily (Web UI feature)
# 1. Start Web UI: kcpwd ui
# 2. Go to "Share" tab
# 3. Select password and duration
# 4. Get secure link: http://localhost:8765/s/ABC123
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
# Insert this section in README.md after the "Features" section

## 🚀 Kubernetes Integration (NEW in v0.8.0)

**kcpwd now includes native Kubernetes support!** Sync passwords to/from Kubernetes secrets with zero additional infrastructure.

### Quick Start

```bash
# Store password
kcpwd set prod_db "my_secure_password"

# Sync to Kubernetes
kcpwd k8s sync prod_db --namespace production

# That's it! Your password is now a Kubernetes secret
```

### Key Features

- ✅ **Bi-directional sync** - kcpwd ↔ Kubernetes secrets
- ✅ **Watch mode** - Auto-sync with configurable intervals
- ✅ **Master password support** - Extra security layer
- ✅ **GitOps friendly** - Works with ArgoCD, Flux, etc.
- ✅ **CI/CD ready** - Perfect for deployment pipelines
- ✅ **Zero infrastructure** - Just needs kubectl

### Common Commands

```bash
# Sync single password
kcpwd k8s sync prod_db --namespace production

# Sync all passwords
kcpwd k8s sync-all --namespace myapp

# Import from Kubernetes
kcpwd k8s import db-credentials --namespace production

# List secrets
kcpwd k8s list --namespace production

# Watch mode (auto-sync every 60s)
kcpwd k8s watch --namespace production
```

### CI/CD Example

```yaml
# GitHub Actions
- name: Sync passwords to K8s
  run: |
    pip install kcpwd
    kcpwd set db_password "${{ secrets.DB_PASSWORD }}"
    kcpwd k8s sync-all --namespace production
```

### Use in Deployments

```yaml
# deployment.yaml
env:
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: prod-db  # Created by kcpwd
      key: password
```

**📚 [Full Kubernetes Guide →](K8S_GUIDE.md)**

### Why kcpwd for Kubernetes?

| Feature | kcpwd | Vault | Sealed Secrets |
|---------|-------|-------|----------------|
| **Setup Time** | 0 minutes | Hours | 30+ minutes |
| **Infrastructure** | None | Servers + DB | Controller |
| **Learning Curve** | Minimal | Steep | Moderate |
| **Local Dev** | ✅ Perfect | ⚠️ Complex | ❌ No |
| **CI/CD** | ✅ Simple | ✅ Yes | ✅ Yes |

Perfect for:
-  Teams who want simple secret management
-  CI/CD pipelines
-  Multi-environment deployments
-  GitOps workflows
-  Local development that mirrors production

---
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
platform = get_platform()  # 'macos', 'linux', or 'windows'
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
```

## Security Details

- **Encryption**: AES-256-GCM (authenticated encryption)
- **Key Derivation**: PBKDF2-SHA256 with 600,000 iterations (OWASP 2023)
- **Storage**: 
  - macOS: Native Keychain
  - Linux: D-Bus Secret Service (gnome-keyring, KWallet)
  - Windows: Windows Credential Locker
  - Fallback: Encrypted file (AES-256-GCM)
- **Master Password**: Not stored anywhere (must be remembered)
- **Web UI**: Session-based authentication with secure tokens
- **API**: Bearer token authentication

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

### Windows
- Uses Windows Credential Locker (built into Windows 10/11)
- Passwords stored securely in Windows Credential Manager
- Access via: Control Panel → Credential Manager → Windows Credentials
- Clipboard integration via `clip.exe` (built-in) or `pywin32` (optional, better)
- Web UI works on all Windows versions
- Compatible with Windows Server editions

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

**Windows Service (NSSM):**
```powershell
# Download NSSM from https://nssm.cc/
nssm install kcpwd "C:\Python311\Scripts\kcpwd.exe" "ui"
nssm set kcpwd AppEnvironmentExtra KCPWD_UI_SECRET=your-secret
nssm start kcpwd
```

**Systemd Service (Linux):**
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
- **Windows**:
  - Windows 10/11 or Server 2016+
  - `pywin32` (optional, for better clipboard support)
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
- Check if port is available: 
  - Linux/Mac: `lsof -i :8765`
  - Windows: `netstat -ano | findstr :8765`
- Try different port: `kcpwd ui --port 8000`
- Check firewall settings

**"Session expired"**
- Sessions expire after 1 hour by default
- Just re-authenticate with your UI secret

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

### Windows Issues

**"Backend not available"**
- Windows Credential Locker is built into Windows 10/11
- Make sure you're running Windows 10 1703 or later
- Check: Control Panel → Credential Manager

**"Clipboard not working"**
- Install pywin32: `pip install pywin32`
- Or use built-in clip.exe (should work automatically)

**"Access denied" errors**
- Run as Administrator if needed
- Check Windows Credential Manager permissions

**Web UI on Windows**
- May need to allow through Windows Firewall
- Use `kcpwd ui --host 127.0.0.1` for localhost only

## Changelog

### v0.7.0 (NEXT) - Windows Support
- 🪟 **Full Windows support** with Windows Credential Locker
- ✅ Windows clipboard integration (clip.exe + pywin32)
- ✅ Platform detection for Windows
- ✅ All features working on Windows 10/11
- ✅ Windows-specific documentation
- ✅ Tested on Windows Server editions

### v0.6.4 - Password Sharing
-  NEW: Pastebin-style temporary password sharing
-  Time-based expiration (5m - 3h)
-  Multiple security options (anyone/once/password)
-  Access logging and statistics
-  Beautiful share access pages
-  Automatic cleanup

### v0.6.3 - Web UI & Enhanced Features
-  Modern Web UI** with FastAPI backend
-  Beautiful, responsive interface** for password management
-  Real-time password strength visualization**
-  Interactive password generator** with live preview
-  Import/Export via Web UI**
-  Session-based authentication**
-  Enhanced UI with logo
-  **REST API** for programmatic access
-  Enhanced CLI with `kcpwd ui` command
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

Contributions welcome! Platform-specific improvements and Web UI enhancements especially appreciated.

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
- [x] Password sharing
- [x] Windows support
- [ ] Password history tracking
- [ ] Browser extensions
- [ ] Multi-user support
- [ ] Cloud sync options
- [ ] 2FA/OTP support
- [ ] Mobile apps
- [ ] Multi node sync
- [ ] Advanced reporting and analytics


## Screenshots

### CLI
```bash
$ kcpwd info
🔧 Platform Information
========================================
Platform: Windows
Supported: ✓ Yes
🔐 Storage Backend
========================================
Type: System Keyring
Backend: Windows Credential Locker
Status: ✓ Active (OS-native secure storage)
```

### Web UI
Beautiful, modern interface for managing your passwords:
- Dark theme
- Responsive design
- Real-time password strength
- Interactive password generator
- Secure session management
- Password sharing

## Support

-  [Documentation](https://github.com/osmanuygar/kcpwd)
-  [Issue Tracker](https://github.com/osmanuygar/kcpwd/issues)
-  [Discussions](https://github.com/osmanuygar/kcpwd/discussions)

## Star History

If you find kcpwd useful, please ⭐ star the repository!

---

Made with ❤️ by [osmanuygar](https://github.com/osmanuygar)