"""
kcpwd.platform_utils - Platform-specific utilities for cross-platform support
Supports macOS, Linux, and Windows with appropriate clipboard and keyring backends
"""

import sys
import platform
import subprocess
from typing import Optional


def get_platform() -> str:
    """Detect current platform

    Returns:
        str: 'macos', 'linux', 'windows', or 'unknown'
    """
    system = platform.system().lower()
    if system == 'darwin':
        return 'macos'
    elif system == 'linux':
        return 'linux'
    elif system == 'windows':
        return 'windows'
    return 'unknown'


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard (platform-independent)

    Args:
        text: Text to copy to clipboard

    Returns:
        bool: True if successful, False otherwise
    """
    current_platform = get_platform()

    try:
        if current_platform == 'macos':
            return _copy_to_clipboard_macos(text)
        elif current_platform == 'linux':
            return _copy_to_clipboard_linux(text)
        elif current_platform == 'windows':
            return _copy_to_clipboard_windows(text)
        else:
            return False
    except Exception:
        return False


def _copy_to_clipboard_macos(text: str) -> bool:
    """Copy to clipboard on macOS using pbcopy"""
    try:
        process = subprocess.Popen(
            ['pbcopy'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        process.communicate(text.encode('utf-8'))
        return True
    except Exception:
        return False


def _copy_to_clipboard_linux(text: str) -> bool:
    """Copy to clipboard on Linux

    Tries multiple clipboard tools in order:
    1. xclip (X11 - most common)
    2. xsel (X11 - alternative)
    3. wl-copy (Wayland)

    If no clipboard tool is available, returns False silently.
    Users can pipe output manually: kcpwd get key | xclip -selection clipboard
    """
    clipboard_commands = [
        ['xclip', '-selection', 'clipboard'],  # X11 - most common
        ['xsel', '--clipboard', '--input'],     # X11 - alternative
        ['wl-copy']                             # Wayland
    ]

    for cmd in clipboard_commands:
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            process.communicate(text.encode('utf-8'))
            if process.returncode == 0:
                return True
        except FileNotFoundError:
            # Command not found, try next one
            continue
        except Exception:
            continue

    # No clipboard tool found or all failed
    return False


def _copy_to_clipboard_windows(text: str) -> bool:
    """Copy to clipboard on Windows using win32clipboard"""
    try:
        import win32clipboard

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        return True
    except ImportError:
        # Fallback to subprocess with clip.exe
        try:
            process = subprocess.Popen(
                ['clip'],
                stdin=subprocess.PIPE,
                shell=True
            )
            process.communicate(text.encode('utf-8'))
            return True
        except Exception:
            return False
    except Exception:
        return False


def get_keyring_backend():
    """Get appropriate keyring backend for the platform

    Returns:
        str: Backend module name or None for default
    """
    current_platform = get_platform()

    if current_platform == 'macos':
        # Use default keyring (macOS Keychain)
        return None
    elif current_platform == 'linux':
        # Use SecretStorage for Linux (D-Bus Secret Service)
        return 'secretstorage'
    elif current_platform == 'windows':
        # Use default keyring (Windows Credential Locker)
        return None

    return None


def check_clipboard_support():
    """Check which clipboard tool is available

    Returns:
        str or None: Name of available clipboard tool, or None if none found
    """
    current_platform = get_platform()

    if current_platform == 'linux':
        clipboard_tools = ['xclip', 'xsel', 'wl-copy']

        for tool in clipboard_tools:
            try:
                subprocess.run(
                    ['which', tool],
                    capture_output=True,
                    check=True,
                    timeout=1
                )
                return tool
            except:
                continue
        return None
    elif current_platform == 'windows':
        try:
            import win32clipboard
            return 'win32clipboard'
        except ImportError:
            # Check if clip.exe is available
            try:
                subprocess.run(
                    ['where', 'clip'],
                    capture_output=True,
                    check=True,
                    shell=True
                )
                return 'clip.exe'
            except:
                return None
    elif current_platform == 'macos':
        try:
            subprocess.run(['which', 'pbcopy'], capture_output=True, check=True)
            return 'pbcopy'
        except:
            return None

    return None


def is_platform_supported() -> bool:
    """Check if current platform is supported

    Returns:
        bool: True if platform is supported
    """
    return get_platform() in ['macos', 'linux', 'windows']


def get_platform_name() -> str:
    """Get human-readable platform name

    Returns:
        str: Platform name
    """
    current_platform = get_platform()
    if current_platform == 'macos':
        return 'macOS'
    elif current_platform == 'linux':
        return 'Linux'
    elif current_platform == 'windows':
        return 'Windows'
    return 'Unknown'


def check_platform_requirements() -> dict:
    """Check if platform requirements are met

    Returns:
        dict: Status information
    """
    current_platform = get_platform()

    result = {
        'platform': current_platform,
        'platform_name': get_platform_name(),
        'supported': is_platform_supported(),
        'clipboard_available': False,
        'keyring_backend': None,
        'warnings': []
    }

    if current_platform == 'macos':
        # Check if pbcopy is available
        try:
            subprocess.run(['which', 'pbcopy'], capture_output=True, check=True)
            result['clipboard_available'] = True
        except:
            result['warnings'].append('pbcopy not found - clipboard functionality disabled')

        result['keyring_backend'] = 'macOS Keychain'

    elif current_platform == 'linux':
        # Check for available clipboard tools
        clipboard_tools = ['xclip', 'xsel', 'wl-copy']
        available_tools = []

        for tool in clipboard_tools:
            try:
                subprocess.run(
                    ['which', tool],
                    capture_output=True,
                    check=True,
                    timeout=1
                )
                available_tools.append(tool)
            except:
                pass

        if available_tools:
            result['clipboard_available'] = True
            result['clipboard_tool'] = available_tools[0]  # First available
            result['warnings'].append(
                f'Clipboard support via {available_tools[0]} '
                f'(alternatives: {", ".join(available_tools[1:])})'
                if len(available_tools) > 1
                else f'Clipboard support via {available_tools[0]}'
            )
        else:
            result['clipboard_available'] = False
            result['warnings'].append(
                'No clipboard tool found. Install xclip, xsel, or wl-clipboard for clipboard support. '
                'Alternatively, pipe output: kcpwd get key | xclip -selection clipboard'
            )

        # Check if secretstorage is available
        try:
            import secretstorage
            result['keyring_backend'] = 'D-Bus Secret Service (secretstorage)'
        except ImportError:
            result['warnings'].append('secretstorage not installed - keyring may not work')
            result['supported'] = False

    elif current_platform == 'windows':
        # Check clipboard support
        clipboard_tool = check_clipboard_support()
        if clipboard_tool:
            result['clipboard_available'] = True
            result['clipboard_tool'] = clipboard_tool
            result['warnings'].append(f'Clipboard support via {clipboard_tool}')
        else:
            result['clipboard_available'] = False
            result['warnings'].append(
                'Clipboard not available. Install pywin32 for better clipboard support: '
                'pip install pywin32'
            )

        # Check keyring support
        try:
            import keyring
            backend = keyring.get_keyring()
            backend_name = backend.__class__.__name__

            if 'Windows' in backend_name or 'WinVault' in backend_name:
                result['keyring_backend'] = 'Windows Credential Locker'
            else:
                result['keyring_backend'] = backend_name
                result['warnings'].append(
                    f'Using {backend_name} backend. '
                    'For best Windows support, ensure Windows Credential Locker is available.'
                )
        except Exception as e:
            result['warnings'].append(f'Keyring backend issue: {str(e)}')
            result['supported'] = False

    else:
        result['warnings'].append(f'Unsupported platform: {platform.system()}')

    return result