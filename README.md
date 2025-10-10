# kcpwd

**Keychain Password Manager CLI** - A simple, secure command-line password manager for macOS that uses the native macOS Keychain.

## Features

- 🔐 Secure storage using macOS Keychain
- 📋 Automatic clipboard copying
- 🚀 Simple CLI interface
- 🔒 No passwords stored in plain text
- 🍎 Native macOS integration

## Installation

### From PyPI
```bash
pip install kcpwd
```

### From Source
```bash
git clone https://github.com/yourusername/kcpwd.git
cd kcpwd
pip install -e .
```

## Usage

### Store a password
```bash
kcpwd set dbadmin asd123
```

### Retrieve a password (copies to clipboard)
```bash
kcpwd get dbadmin
```

### Delete a password
```bash
kcpwd delete dbadmin
```

### List stored keys
```bash
kcpwd list
```

## How It Works

`kcpwd` stores your passwords in the **macOS Keychain** - the same secure, encrypted storage that Safari and other macOS apps use. This means:

- Passwords are encrypted with your Mac's security
- They persist across reboots
- They're protected by your Mac's login password
- No plain text files or databases

### Viewing Your Passwords

Open **Keychain Access** app and search for "kcpwd" to see all stored passwords.

Or use Terminal:
```bash
security find-generic-password -s "kcpwd" -a "dbadmin" -w
```

## Security Notes

⚠️ **Important Security Considerations:**

- Passwords are stored in macOS Keychain (encrypted)
- Passwords remain in clipboard until you copy something else
- Consider clearing clipboard after use for sensitive passwords
- Designed for personal use on trusted devices
- Always use strong, unique passwords

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

## Project Structure
```
kcpwd/
├── kcpwd/
│   ├── __init__.py
│   └── cli.py
├── tests/
│   └── test_cli.py
├── setup.py
├── README.md
├── LICENSE
└── requirements.txt
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## Disclaimer

This is a personal password manager tool. While it uses secure storage (macOS Keychain), please use at your own risk. For enterprise or critical password management, consider established solutions like 1Password, Bitwarden, or similar.

## Roadmap

- [ ] Master password protection
- [ ] Auto-clear clipboard after X seconds
- [ ] Password generation
- [ ] Import/export functionality
- [ ] Password strength indicator
- [ ] Cross-platform support (Linux, Windows)