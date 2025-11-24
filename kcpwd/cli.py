#!/usr/bin/env python3
"""
kcpwd - Cross-platform Keychain Password Manager CLI
Supports macOS and Linux
Stores passwords securely in system keyring and provides clipboard integration
"""

import click
import os
import getpass
from .core import set_password as _set_password
from .core import get_password as _get_password
from .core import delete_password as _delete_password
from .core import generate_password as _generate_password
from .core import list_all_keys as _list_all_keys
from .core import export_passwords as _export_passwords
from .core import import_passwords as _import_passwords
from .core import SERVICE_NAME
from .master_protection import (
    set_master_password,
    get_master_password,
    delete_master_password,
    list_master_keys
)
from .strength import check_password_strength, get_strength_color, get_strength_bar
from .platform_utils import (
    get_platform,
    get_platform_name,
    is_platform_supported,
    check_platform_requirements
)


@click.group()
@click.version_option(version='0.6.0')
def cli():
    """kcpwd - Cross-platform Password Manager (macOS & Linux)"""
    # Check platform support
    if not is_platform_supported():
        platform_name = get_platform_name()
        click.echo(click.style(f"⚠️  Warning: {platform_name} is not officially supported",
                               fg='yellow'), err=True)
        click.echo("Supported platforms: macOS, Linux\n", err=True)


@cli.command()
def info():
    """Display platform and configuration information"""
    from .core import get_backend_info

    status = check_platform_requirements()
    backend = get_backend_info()

    click.echo(f"\n🔧 Platform Information")
    click.echo("=" * 40)
    click.echo(f"Platform: {status['platform_name']}")
    click.echo(f"Supported: {'✓ Yes' if status['supported'] else '✗ No'}")

    # Backend info
    click.echo(f"\n🔐 Storage Backend")
    click.echo("=" * 40)
    if backend['type'] == 'keyring':
        click.echo(f"Type: System Keyring")
        click.echo(f"Backend: {backend.get('name', 'Unknown')}")
        click.echo(f"Status: ✓ Active (OS-native secure storage)")
    else:
        click.echo(f"Type: Encrypted File Storage")
        click.echo(f"Backend: {backend.get('name', 'Unknown')}")
        click.echo(f"Status: ✓ Active (fallback)")
        if 'note' in backend:
            click.echo(f"Note: {backend['note']}")

    click.echo(f"\n📋 Clipboard")
    click.echo("=" * 40)
    click.echo(f"Status: {'✓ Available' if status['clipboard_available'] else '✗ Disabled'}")
    if status.get('clipboard_tool'):
        click.echo(f"Tool: {status['clipboard_tool']}")

    if status['warnings']:
        click.echo(f"\n⚠️  Notes:")
        for warning in status['warnings']:
            click.echo(f"  • {warning}")

    # Linux-specific notes
    if status['platform'] == 'linux':
        click.echo(f"\n💡 Linux Notes:")
        if status['clipboard_available']:
            tool = status.get('clipboard_tool', 'clipboard tool')
            click.echo(f"  • Clipboard available via {tool}")
            click.echo(f"  • If clipboard fails, use shell pipes: kcpwd get key | xclip -selection clipboard")
        else:
            click.echo(f"  • No clipboard tool found (install xclip, xsel, or wl-clipboard)")
            click.echo(f"  • Use shell pipes instead: kcpwd get key | xclip -selection clipboard")

        if backend['type'] == 'keyring':
            click.echo(f"  • Using D-Bus Secret Service (gnome-keyring, KWallet, etc.)")
        else:
            click.echo(f"  • Using encrypted file backend (no system keyring detected)")
            click.echo(f"  • Storage: ~/.kcpwd/keyring.enc")

    click.echo()


@cli.command()
@click.argument('key')
@click.argument('password')
@click.option('--master-password', '-m', is_flag=True,
              help='Protect this password with a master password')
@click.option('--check-strength', '-c', is_flag=True,
              help='Check password strength before saving')
def set(key: str, password: str, master_password: bool = False, check_strength: bool = False):
    """Store a password for a given key

    Examples:
        kcpwd set dbadmin asd123
        kcpwd set prod_db secret --master-password
        kcpwd set myapi password123 --check-strength
    """
    # Check strength if requested
    if check_strength:
        result = check_password_strength(password)
        color = get_strength_color(result['strength'])
        bar = get_strength_bar(result['score'])

        click.echo(f"\n🔐 Password Strength Analysis:")
        click.echo(f"Score: {result['score']}/100 [{bar}]")
        click.echo(f"Strength: {click.style(result['strength_text'], fg=color, bold=True)}")

        if result['feedback']:
            click.echo(f"\n💡 Suggestions:")
            for tip in result['feedback']:
                click.echo(f"  • {tip}")

        if result['score'] < 50:
            click.echo(f"\n⚠️  Warning: This password is weak!")
            if not click.confirm('Do you still want to save it?'):
                click.echo("Cancelled")
                return
        click.echo()

    if master_password:
        mp = getpass.getpass("Enter master password: ")
        mp_confirm = getpass.getpass("Confirm master password: ")

        if mp != mp_confirm:
            click.echo("Error: Passwords do not match", err=True)
            return

        if len(mp) < 8:
            click.echo("Error: Master password must be at least 8 characters", err=True)
            return

        if set_master_password(key, password, mp):
            click.echo(f"✓ Password stored for '{key}' with master password protection")
        else:
            click.echo(f"Error storing password", err=True)
    else:
        if _set_password(key, password):
            click.echo(f"✓ Password stored for '{key}'")
        else:
            click.echo(f"Error storing password", err=True)


@cli.command()
@click.argument('key')
@click.argument('password')
def set_master(key: str, password: str):
    """Store a password with master password protection (shorthand)"""
    mp = getpass.getpass("Enter master password: ")
    mp_confirm = getpass.getpass("Confirm master password: ")

    if mp != mp_confirm:
        click.echo("Error: Passwords do not match", err=True)
        return

    if len(mp) < 8:
        click.echo("Error: Master password must be at least 8 characters", err=True)
        return

    if set_master_password(key, password, mp):
        click.echo(f"✓ Password stored for '{key}' with master password protection")
    else:
        click.echo(f"Error storing password", err=True)


@cli.command()
@click.argument('key')
@click.option('--master-password', '-m', is_flag=True,
              help='Password is protected with master password')
@click.option('--print', '-p', 'print_password', is_flag=True,
              help='Print password to stdout instead of clipboard')
def get(key: str, master_password: bool = False, print_password: bool = False):
    """Retrieve password and copy to clipboard (macOS) or print (Linux)

    Examples:
        kcpwd get dbadmin
        kcpwd get prod_db --master-password
        kcpwd get myapi --print  # Print to stdout
    """
    # Get platform info
    current_platform = get_platform()

    if master_password:
        mp = getpass.getpass("Enter master password: ")
        password = get_master_password(key, mp)

        if password is None:
            click.echo(f"No password found for '{key}' or incorrect master password", err=True)
            return

        # Handle output based on platform and user preference
        if print_password:
            click.echo(password)
        elif current_platform == 'linux':
            # On Linux, always print (clipboard disabled)
            click.echo(password)
        else:
            # Try clipboard on macOS
            from .core import copy_to_clipboard
            if copy_to_clipboard(password):
                click.echo(f"✓ Password for '{key}' copied to clipboard")
            else:
                click.echo(f"✓ Password: {password}")
    else:
        password = _get_password(key, copy_to_clip=(not print_password and current_platform == 'macos'))

        if password is None:
            click.echo(f"No password found for '{key}'", err=True)
            return

        # Handle output based on platform and user preference
        if print_password:
            click.echo(password)
        elif current_platform == 'linux':
            click.echo(password)
        else:
            click.echo(f"✓ Password for '{key}' copied to clipboard")


@cli.command()
@click.argument('key')
def get_master(key: str):
    """Retrieve master-protected password (shorthand)"""
    mp = getpass.getpass("Enter master password: ")
    password = get_master_password(key, mp)

    if password is None:
        click.echo(f"No password found for '{key}' or incorrect master password", err=True)
        return

    current_platform = get_platform()

    if current_platform == 'linux':
        click.echo(password)
    else:
        from .core import copy_to_clipboard
        if copy_to_clipboard(password):
            click.echo(f"✓ Password for '{key}' copied to clipboard")
        else:
            click.echo(f"✓ Password: {password}")


@cli.command()
@click.argument('key')
@click.confirmation_option(prompt=f'Are you sure you want to delete this password?')
def delete(key: str):
    """Delete a stored password"""
    if _delete_password(key):
        click.echo(f"✓ Password for '{key}' deleted")
    else:
        click.echo(f"No password found for '{key}'", err=True)


@cli.command()
@click.argument('key')
@click.confirmation_option(prompt=f'Are you sure you want to delete this master-protected password?')
def delete_master(key: str):
    """Delete a master-protected password (shorthand)"""
    if delete_master_password(key):
        click.echo(f"✓ Master-protected password for '{key}' deleted")
    else:
        click.echo(f"No master-protected password found for '{key}'", err=True)


@cli.command()
def list():
    """List all stored password keys"""
    keys = _list_all_keys()
    master_keys = list_master_keys()

    if not keys and not master_keys:
        click.echo("No passwords stored yet")
        click.echo(f"\nTo add a password: kcpwd set <key> <password>")
        click.echo(f"To add with master password: kcpwd set <key> <password> --master-password")
        return

    if keys:
        click.echo(f"Regular passwords ({len(keys)}):\n")
        for key in keys:
            click.echo(f"  • {key}")

    if master_keys:
        click.echo(f"\n🔒 Master-protected passwords ({len(master_keys)}):\n")
        for key in master_keys:
            click.echo(f"  • {key} 🔒")

    click.echo(f"\nTo retrieve: kcpwd get <key>")
    click.echo(f"To retrieve master-protected: kcpwd get <key> --master-password")


@cli.command()
@click.option('--length', '-l', default=16, help='Password length (default: 16)')
@click.option('--no-uppercase', is_flag=True, help='Exclude uppercase letters')
@click.option('--no-lowercase', is_flag=True, help='Exclude lowercase letters')
@click.option('--no-digits', is_flag=True, help='Exclude digits')
@click.option('--no-symbols', is_flag=True, help='Exclude symbols')
@click.option('--exclude-ambiguous', is_flag=True, help='Exclude ambiguous characters (0/O, 1/l/I)')
@click.option('--save', '-s', help='Save generated password with this key')
@click.option('--master-password', '-m', is_flag=True, help='Save with master password protection')
@click.option('--copy/--no-copy', default=None, help='Copy to clipboard (default: auto based on platform)')
@click.option('--show-strength', is_flag=True, default=True, help='Show password strength (default: yes)')
def generate(length, no_uppercase, no_lowercase, no_digits, no_symbols, exclude_ambiguous,
             save, master_password, copy, show_strength):
    """Generate a secure random password"""
    try:
        password = _generate_password(
            length=length,
            use_uppercase=not no_uppercase,
            use_lowercase=not no_lowercase,
            use_digits=not no_digits,
            use_symbols=not no_symbols,
            exclude_ambiguous=exclude_ambiguous
        )

        click.echo(f"\n🔐 Generated password: {click.style(password, fg='green', bold=True)}")

        if show_strength:
            result = check_password_strength(password)
            color = get_strength_color(result['strength'])
            bar = get_strength_bar(result['score'])

            click.echo(f"\n📊 Strength: {click.style(result['strength_text'], fg=color, bold=True)} "
                       f"({result['score']}/100)")
            click.echo(f"    [{bar}]")

        # Handle clipboard based on platform
        current_platform = get_platform()
        should_copy = copy if copy is not None else (current_platform == 'macos')

        if should_copy:
            from .core import copy_to_clipboard
            if copy_to_clipboard(password):
                click.echo("\n✓ Copied to clipboard")

        if save:
            if master_password:
                mp = getpass.getpass("\nEnter master password: ")
                mp_confirm = getpass.getpass("Confirm master password: ")

                if mp != mp_confirm:
                    click.echo("Error: Passwords do not match", err=True)
                    return

                if set_master_password(save, password, mp):
                    click.echo(f"✓ Saved as '{save}' with master password protection")
                else:
                    click.echo(f"Failed to save password", err=True)
            else:
                if _set_password(save, password):
                    click.echo(f"✓ Saved as '{save}'")
                else:
                    click.echo(f"Failed to save password", err=True)

        click.echo()

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument('password')
def check_strength(password: str):
    """Check strength of a password"""
    result = check_password_strength(password)
    color = get_strength_color(result['strength'])
    bar = get_strength_bar(result['score'])

    click.echo(f"\n🔐 Password Strength Analysis")
    click.echo("=" * 40)
    click.echo(f"\nScore: {result['score']}/100")
    click.echo(f"[{bar}]")
    click.echo(f"\nStrength: {click.style(result['strength_text'], fg=color, bold=True)}")

    click.echo(f"\n📋 Details:")
    click.echo(f"  Length: {result['details']['length']} characters")
    click.echo(f"  Lowercase: {'✓' if result['details']['has_lowercase'] else '✗'}")
    click.echo(f"  Uppercase: {'✓' if result['details']['has_uppercase'] else '✗'}")
    click.echo(f"  Digits: {'✓' if result['details']['has_digits'] else '✗'}")
    click.echo(f"  Symbols: {'✓' if result['details']['has_symbols'] else '✗'}")

    if result['feedback']:
        click.echo(f"\n💡 Suggestions:")
        for tip in result['feedback']:
            click.echo(f"  • {tip}")

    click.echo()


@cli.command()
@click.argument('filepath', type=click.Path())
@click.option('--keys-only', is_flag=True, help='Export only keys without passwords')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing file without confirmation')
def export(filepath: str, keys_only: bool, force: bool):
    """Export all passwords to a JSON file"""
    if os.path.exists(filepath) and not force:
        if not click.confirm(f"File '{filepath}' already exists. Overwrite?"):
            click.echo("Export cancelled")
            return

    if not keys_only:
        click.echo(click.style("⚠️  WARNING: Exported file will contain passwords in PLAIN TEXT!",
                               fg='yellow', bold=True))
        click.echo("Master-protected passwords are NOT included for security.")
        click.echo("Make sure to:")
        click.echo("  • Store the file in a secure location")
        click.echo("  • Delete it after use")
        click.echo("  • Never commit it to version control\n")

        if not click.confirm("Do you want to continue?"):
            click.echo("Export cancelled")
            return

    result = _export_passwords(filepath, include_passwords=not keys_only)

    if result['success']:
        click.echo(f"✓ {result['message']}")

        master_keys = list_master_keys()
        if master_keys:
            click.echo(f"\nℹ️  {len(master_keys)} master-protected passwords NOT exported:")
            for key in master_keys[:5]:
                click.echo(f"  • {key}")
            if len(master_keys) > 5:
                click.echo(f"  ... and {len(master_keys) - 5} more")

        if result['failed_keys']:
            click.echo(f"\n⚠️  Failed to export: {', '.join(result['failed_keys'])}", err=True)
    else:
        click.echo(f"✗ {result['message']}", err=True)


@cli.command(name='import')
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--overwrite', is_flag=True, help='Overwrite existing passwords')
@click.option('--dry-run', is_flag=True, help='Show what would be imported without making changes')
def import_cmd(filepath: str, overwrite: bool, dry_run: bool):
    """Import passwords from a JSON file"""
    result = _import_passwords(filepath, overwrite=overwrite, dry_run=dry_run)

    if result['success']:
        click.echo(f"✓ {result['message']}")

        if result['skipped_keys']:
            click.echo(f"\n📋 Skipped existing keys ({len(result['skipped_keys'])}):")
            for key in result['skipped_keys'][:10]:
                click.echo(f"  • {key}")
            if len(result['skipped_keys']) > 10:
                click.echo(f"  ... and {len(result['skipped_keys']) - 10} more")
            click.echo("\nUse --overwrite to replace existing passwords")

        if result['failed_keys']:
            click.echo(f"\n⚠️  Failed to import: {', '.join(result['failed_keys'])}", err=True)
    else:
        click.echo(f"✗ {result['message']}", err=True)


@cli.command()
@click.option('--host', default='127.0.0.1', help='Host address (default: 127.0.0.1)')
@click.option('--port', default=8765, type=int, help='Port number (default: 8765)')
@click.option('--secret', envvar='KCPWD_UI_SECRET', help='UI access secret (or set KCPWD_UI_SECRET)')
@click.option('--no-open-browser', is_flag=True, help='Do not open browser automatically')
def ui(host, port, secret, no_open_browser):
    """Start the web UI server

    The web UI provides a modern interface for password management.

    Examples:
        kcpwd ui
        kcpwd ui --port 8000
        kcpwd ui --host 0.0.0.0 --port 8080
        KCPWD_UI_SECRET=mysecret kcpwd ui
    """
    try:
        from .ui.api import start_server
        start_server(
            host=host,
            port=port,
            secret=secret,
            open_browser=not no_open_browser
        )
    except ImportError as e:
        click.echo(click.style("❌ UI dependencies not installed", fg='red', bold=True))
        click.echo("\nTo use the Web UI, install with:")
        click.echo(click.style("  pip install kcpwd[ui]", fg='yellow'))
        click.echo("\nOr install dependencies manually:")
        click.echo("  pip install fastapi uvicorn[standard] pydantic")
        click.echo(f"\nError details: {e}")
    except Exception as e:
        click.echo(click.style(f"❌ Failed to start UI: {e}", fg='red'), err=True)

if __name__ == '__main__':
    cli()