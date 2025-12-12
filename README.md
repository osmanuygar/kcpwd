<p align="left">
  <img src="kcpwd/ui/static/kcpwd_logo.png" alt="kcpwd Logo" width="200"/>
</p>

[![PyPI version](https://img.shields.io/pypi/v/kcpwd.svg)](https://pypi.org/project/kcpwd/)
[![Python Version](https://img.shields.io/pypi/pyversions/kcpwd.svg)](https://pypi.org/project/kcpwd/)
[![License](https://img.shields.io/pypi/l/kcpwd.svg)](https://github.com/osmanuygar/kcpwd/blob/main/LICENSE)

# kcpwd

**Cross-platform Keychain Password Manager CLI, Library & Web UI with Kubernetes Integration** - A powerful password manager for **macOS, Linux, and Windows** with native system keyring support, modern web interface, and native Kubernetes secret management.

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


## Platform Support

### macOS
- ✅ Native macOS Keychain integration
- ✅ Automatic clipboard copying with `pbcopy`
- ✅ Full feature support
- ✅ Web UI support
- ✅ Kubernetes integration

### Linux
- ✅ **Works immediately - no setup required!**
- ✅ Auto-detects system keyring (gnome-keyring, KWallet, etc.)
- ✅ Falls back to encrypted file storage if no keyring
- ✅ Optional clipboard support via `xclip`, `xsel`, or `wl-copy` (auto-detected)
- ✅ Perfect for Docker, CI/CD, headless servers
- ✅ Web UI support
- ✅ Kubernetes integration
- 📦 Zero required dependencies (secretstorage optional for system keyring)

### Windows
- ✅ **Native Windows Credential Locker integration**
- ✅ Automatic clipboard copying via `clip.exe` or `pywin32`
- ✅ Full feature support
- ✅ Web UI support
- ✅ Kubernetes integration
- ✅ Works on Windows 10, 11, and Server editions
- 📦 Optional `pywin32` for enhanced clipboard support



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



### ⎈ Kubernetes Usage

```bash
# Sync a password to K8s
kcpwd k8s sync prod_db --namespace production

# Sync all passwords
kcpwd k8s sync-all --namespace production

# Import from K8s
kcpwd k8s import db-credentials --namespace production

# Watch mode (auto-sync)
kcpwd k8s watch --namespace production

# List K8s secrets
kcpwd k8s list --namespace production
```

## Kubernetes Integration Deep Dive

### Common Commands

#### Sync Single Password

```bash
# Basic sync
kcpwd k8s sync prod_db --namespace production

# Custom secret name
kcpwd k8s sync api_key --secret-name my-api-secret --namespace myapp

# Master-protected password
kcpwd k8s sync secure_db --master-password MY_MASTER_PASS --namespace prod

# With custom labels
kcpwd k8s sync db_pass --label app=myapp --label tier=backend
```

#### Sync All Passwords

```bash
# Sync all passwords to a namespace
kcpwd k8s sync-all --namespace production

# Sync only passwords with prefix
kcpwd k8s sync-all --prefix prod_ --namespace production

# Skip master-protected passwords
kcpwd k8s sync-all --skip-master --namespace dev
```

#### Import from Kubernetes

```bash
# Import a secret to kcpwd
kcpwd k8s import db-credentials --namespace production

# Import with custom kcpwd key name
kcpwd k8s import api-secret --key my_api_key

# Import and protect with master password
kcpwd k8s import prod-db --master-password
```

#### Watch Mode (Auto-sync)

```bash
# Auto-sync every 60 seconds
kcpwd k8s watch --namespace production

# Custom interval
kcpwd k8s watch --namespace myapp --interval 120

# With prefix filter
kcpwd k8s watch --prefix prod_ --namespace production
```

### Use Cases Overview

**Common Scenarios:**
- ✅ CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins)
- ✅ GitOps workflows (ArgoCD, Flux)
- ✅ Local development (Minikube, Kind)
- ✅ Multi-environment deployments
- ✅ Blue-green and canary deployments
- ✅ Secret rotation automation
- ✅ Disaster recovery and backups

**📚 [Complete Usage Examples →](usages/K8S_USAGE_EXAMPLES.md)**

Quick example - CI/CD Pipeline:

```yaml
# GitHub Actions
- name: Sync secrets
  run: |
    pip install kcpwd
    kcpwd set db_password "${{ secrets.DB_PASSWORD }}"
    kcpwd k8s sync-all --namespace production
```

### Helm Integration

Use kcpwd passwords directly in Helm values:

```yaml
# values.yaml
database:
  password: "{{ kcpwd('db_password') }}"
api:
  key: "{{ kcpwd('api_key') }}"
production:
  secret: "{{ kcpwd('prod_secret', master=true) }}"
```

```bash
# Process and deploy
kcpwd helm template values.yaml -o values-processed.yaml
helm install myapp ./chart -f values-processed.yaml
```

**📚 [Helm Integration Examples →](usages/K8S_USAGE_EXAMPLES.md#helm-integration-examples)**

## Usage

### Platform Information

```bash
# Check your platform configuration
kcpwd info

# Output example (macOS):
# 🔧 Platform Information
# ========================================
# Platform: macOS
# Supported: ✓ Yes
# 
# 🔐 Storage Backend
# ========================================
# Type: System Keyring
# Backend: Keyring
# Status: ✓ Active (OS-native secure storage)
# 
# 📋 Clipboard
# ========================================
# Status: ✓ Available
# 
# 💡 macOS Notes:
#   • Using macOS Keychain (native integration)
#   • View passwords: Keychain Access app
#   • Command line: security find-generic-password -s kcpwd
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
**📚 [Complete Usage Examples →](usages/PASSWORD_SHARING_EXAMPLES.md)**

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
#### Exporting Passwords
```bash
# Export environment variables
kcpwd export-env [OPTIONS]
  -k, --keys TEXT         Specific keys to export
  -p, --prefix TEXT       Variable name prefix
  --uppercase/--no-uppercase  Convert to uppercase (default: yes)
  -f, --format [export|set|plain]  Output format

# Generate .env file
kcpwd generate-env [OUTPUT_PATH] [OPTIONS]
  -k, --keys TEXT         Specific keys to include
  -p, --prefix TEXT       Variable name prefix
  --uppercase/--no-uppercase  Convert to uppercase
  --no-comments          Skip header comments
  -f, --force            Overwrite without confirmation
```

```bash
# Store credentials
kcpwd set aws_key AKIAIOSFODNN7EXAMPLE
kcpwd set aws_secret wJalrXUtnFEMI/K7MDENG

# Export and use
eval $(kcpwd export-env --prefix "SPARK_")
pyspark --conf "spark.hadoop.fs.s3a.access.key=$SPARK_AWS_KEY"
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

#### Kubernetes Integration

```python
from kcpwd.k8s import sync_to_k8s, sync_all_to_k8s, import_from_k8s

# Sync single password
result = sync_to_k8s(
    key="prod_db",
    namespace="production",
    secret_name="database-credentials",
    labels={"app": "myapp"}
)

# Sync all passwords
results = sync_all_to_k8s(
    namespace="production",
    prefix="prod_"
)

# Import from K8s
result = import_from_k8s(
    secret_name="existing-secret",
    namespace="production",
    kcpwd_key="imported_password"
)
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
- **Kubernetes**: Uses native K8s RBAC and secret encryption at rest

## Platform-Specific Notes

### macOS
- Uses native Keychain Access
- Passwords accessible via: `security find-generic-password -s kcpwd -a <key> -w`
- Clipboard integration works automatically
- Web UI runs on localhost by default
- Kubernetes integration requires kubectl

### Linux
- Requires D-Bus Secret Service daemon (gnome-keyring, KWallet, etc.)
- Falls back to encrypted file if no keyring available
- Clipboard is **disabled by default** (security/dependency choice)
- Use shell pipes for clipboard: `kcpwd get key | xclip -selection clipboard`
- Works in both X11 and Wayland (with appropriate clipboard tools)
- Web UI works perfectly on all Linux distributions
- Kubernetes integration requires kubectl

### Windows
- Uses Windows Credential Locker (built into Windows 10/11)
- Passwords stored securely in Windows Credential Manager
- Access via: Control Panel → Credential Manager → Windows Credentials
- Clipboard integration via `clip.exe` (built-in) or `pywin32` (optional, better)
- Web UI works on all Windows versions
- Compatible with Windows Server editions
- Kubernetes integration requires kubectl

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
- `pyyaml>=6.0.0` (for Helm integration)
- **Web UI** (optional):
  - `fastapi>=0.104.0`
  - `uvicorn[standard]>=0.24.0`
  - `pydantic>=2.0.0`
- **Kubernetes** (optional):
  - `kubectl` CLI tool

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

### Kubernetes Issues

**"kubectl not found"**
```bash
# Install kubectl
# macOS
brew install kubectl

# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Windows (Chocolatey)
choco install kubernetes-cli
```

**"Permission denied" (K8s)**
```bash
# Check RBAC permissions
kubectl auth can-i create secrets -n production

# If denied, ask your cluster admin for permissions
```

**"Secret already exists"**
```bash
# kcpwd will update it automatically, or manually:
kubectl delete secret prod-db -n production
kcpwd k8s sync prod_db --namespace production
```
## 🚀 Kubernetes Integration (NEW in v0.8.0)

**kcpwd now includes native Kubernetes support!** Sync passwords to/from Kubernetes secrets with zero additional infrastructure.

### Why kcpwd for Kubernetes?

| Feature | kcpwd | Vault | Sealed Secrets | External Secrets |
|---------|-------|-------|----------------|------------------|
| **Setup Time** | 0 minutes | Hours | 30+ minutes | 1+ hour |
| **Infrastructure** | None | Servers + DB | Controller | Operators |
| **Learning Curve** | Minimal | Steep | Moderate | Moderate |
| **Local Dev** | ✅ Perfect | ⚠️ Complex | ❌ No | ⚠️ Limited |
| **CI/CD** | ✅ Simple | ✅ Yes | ✅ Yes | ✅ Yes |
| **GitOps** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Master Password** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Cost** | Free | $$$ | Free | Free |

### Quick Start

```bash
# 1. Store password locally
kcpwd set prod_db "my_secure_password"

# 2. Sync to Kubernetes
kcpwd k8s sync prod_db --namespace production

# 3. Use in your deployment
kubectl get secret prod-db -n production
```

That's it! Your password is now a Kubernetes secret.

### Key K8s Features

- ✅ **Bi-directional sync** - kcpwd ↔ Kubernetes secrets
- ✅ **Watch mode** - Auto-sync with configurable intervals
- ✅ **Master password support** - Extra security layer for sensitive passwords
- ✅ **GitOps friendly** - Works with ArgoCD, Flux, etc.
- ✅ **CI/CD ready** - Perfect for deployment pipelines
- ✅ **Helm integration** - Use `{{ kcpwd('key') }}` in values.yaml
- ✅ **Zero infrastructure** - Just needs kubectl
- ✅ **Multi-namespace** - Sync to different namespaces
- ✅ **Label management** - Add custom labels to secrets




## Changelog


### v0.8.0 (LATEST) - Kubernetes & Helm Integration 🚀
- 🎯 **Native Kubernetes support** - Sync passwords to/from K8s secrets
- ⎈ **Helm integration** - Use `{{ kcpwd('key') }}` in values.yaml
- 🔄 **Bi-directional sync** - Import secrets from K8s to kcpwd
- 👀 **Watch mode** - Auto-sync with configurable intervals
- 🏷️ **Label management** - Add custom labels to K8s secrets
- 🔐 **Master password in K8s** - Extra security for production
- 🚀 **CI/CD ready** - Perfect for GitHub Actions, GitLab CI, etc.
- 📦 **Zero infrastructure** - Just needs kubectl
- 🎨 **GitOps friendly** - Works with ArgoCD, Flux

### v0.7.0 - Windows Support & Password Sharing
- 🪟 **Full Windows support** with Windows Credential Locker
- ✅ Windows clipboard integration (clip.exe + pywin32)
- 🔗 **Password sharing** - Secure temporary links with expiration
- ⏱️ Time-based expiration (5m - 3h)
- 🔒 Multiple security options (anyone/once/password)
- 📊 Access logging and statistics
- 🎨 Beautiful share access pages
- 🧹 Automatic cleanup
- ✅ Platform detection for Windows
- ✅ Tested on Windows 10/11 & Server editions

### v0.6.4 - Enhanced Web UI
- 🌐 **Modern Web UI** with FastAPI backend
- 🎨 Beautiful, responsive interface for password management
- 📊 Real-time password strength visualization
- 🎲 Interactive password generator with live preview
- 📤 Import/Export via Web UI
- 🔐 Session-based authentication
- 🎭 Enhanced UI with logo and dark mode
- 🔌 **REST API** for programmatic access

### v0.5.0 - Linux Support and Universal Compatibility
- 🐧 Full Linux support via D-Bus Secret Service
- 📋 Platform detection and info command (`kcpwd info`)
- 📎 Optional clipboard support on Linux
- 💾 Encrypted file backend for universal compatibility
- 🔍 Automatic backend detection
- 🛠️ `get_backend_info()` API function

### v0.4.1 - Master Password & Strength Checking
- 🔐 `@require_master_password` decorator
- 💪 Password strength checker with visual feedback
- 📊 CLI `check-strength` command

### v0.4.0 - Security Enhancements
- 🔒 Per-password master password protection
- 🔐 AES-256-GCM encryption
- 🔑 PBKDF2-SHA256 key derivation (600k iterations)

### v0.3.0 - Import/Export
- 📤 Import/export functionality
- 📋 `list` command for viewing all passwords

### v0.2.1 - Password Generation
- 🎲 Cryptographically secure password generation
- ⚙️ Customizable generation options

### v0.2.0 - Python Library
- 📦 Python library support
- 🎯 `@require_password` decorator
- 🔌 Programmatic API access

### v0.1.0 - Initial Release
- 🎉 macOS Keychain integration
- 💻 CLI interface
- 📋 Basic password management
- 🔐 Secure storage

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Platform-specific improvements, Kubernetes enhancements, and Web UI improvements especially appreciated.

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
- [x] Kubernetes integration
- [x] Helm integration
- [ ] Password history tracking
- [ ] Browser extensions
- [ ] Multi-user support
- [ ] Cloud sync options
- [ ] 2FA/OTP support
- [ ] Mobile apps
- [ ] Multi-node sync
- [ ] Advanced reporting and analytics
- [ ] Kubernetes Operator
- [ ] Terraform Provider

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

- 📖 [Documentation](https://github.com/osmanuygar/kcpwd)
- 🐛 [Issue Tracker](https://github.com/osmanuygar/kcpwd/issues)
- 💬 [Discussions](https://github.com/osmanuygar/kcpwd/discussions)


## Star History

If you find kcpwd useful, please ⭐ star the repository!

---

Made with ❤️ by [osmanuygar](https://github.com/osmanuygar)