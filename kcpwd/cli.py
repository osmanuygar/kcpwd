#!/usr/bin/env python3
"""
kcpwd - Cross-platform Keychain Password Manager CLI
Supports macOS, Linux, and Windows
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
@click.version_option(version='0.8.0')
def cli():
    """kcpwd - Cross-platform Password Manager (macOS, Linux & Windows)"""
    # Check platform support
    if not is_platform_supported():
        platform_name = get_platform_name()
        click.echo(click.style(f"⚠️  Warning: {platform_name} is not officially supported",
                               fg='yellow'), err=True)
        click.echo("Supported platforms: macOS, Linux, Windows\n", err=True)


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

    # Platform-specific notes
    current_platform = status['platform']

    if current_platform == 'linux':
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

    elif current_platform == 'windows':
        click.echo(f"\n💡 Windows Notes:")
        if status['clipboard_available']:
            tool = status.get('clipboard_tool', 'clipboard tool')
            click.echo(f"  • Clipboard available via {tool}")
            if tool == 'clip.exe':
                click.echo(f"  • For better clipboard support, install: pip install pywin32")
        else:
            click.echo(f"  • Install pywin32 for clipboard support: pip install pywin32")

        if backend['type'] == 'keyring':
            click.echo(f"  • Using Windows Credential Locker (Windows Credential Manager)")
            click.echo(f"  • View passwords: Control Panel → Credential Manager → Windows Credentials")
        else:
            click.echo(f"  • Using encrypted file backend (keyring not available)")
            click.echo(f"  • Storage: %USERPROFILE%\\.kcpwd\\keyring.enc")

    elif current_platform == 'macos':
        click.echo(f"\n💡 macOS Notes:")
        click.echo(f"  • Using macOS Keychain (native integration)")
        click.echo(f"  • View passwords: Keychain Access app")
        click.echo(f"  • Command line: security find-generic-password -s kcpwd")

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
    """Retrieve password and copy to clipboard (or print)

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
        elif current_platform in ['macos', 'windows']:
            # Try clipboard on macOS and Windows
            from .core import copy_to_clipboard
            if copy_to_clipboard(password):
                click.echo(f"✓ Password for '{key}' copied to clipboard")
            else:
                # Clipboard failed, print instead
                click.echo(f"✓ Password: {password}")
        else:
            # Linux - print by default
            click.echo(password)
    else:
        # Determine if we should copy to clipboard
        should_copy = not print_password and current_platform in ['macos', 'windows']

        password = _get_password(key, copy_to_clip=should_copy)

        if password is None:
            click.echo(f"No password found for '{key}'", err=True)
            return

        # Handle output based on platform and user preference
        if print_password:
            click.echo(password)
        elif current_platform in ['macos', 'windows']:
            click.echo(f"✓ Password for '{key}' copied to clipboard")
        else:
            # Linux - print to stdout
            click.echo(password)


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

    if current_platform in ['macos', 'windows']:
        from .core import copy_to_clipboard
        if copy_to_clipboard(password):
            click.echo(f"✓ Password for '{key}' copied to clipboard")
        else:
            click.echo(f"✓ Password: {password}")
    else:
        # Linux - print to stdout
        click.echo(password)


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
        should_copy = copy if copy is not None else (current_platform in ['macos', 'windows'])

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

        # Windows
        set KCPWD_UI_SECRET=mysecret
        kcpwd ui

        # Linux/macOS
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


@cli.group()
def k8s():
    """Kubernetes secret management commands

    Sync kcpwd passwords to/from Kubernetes secrets.

    Examples:
        kcpwd k8s sync prod_db --namespace production
        kcpwd k8s sync-all --namespace myapp
        kcpwd k8s import db-secret --namespace production
        kcpwd k8s list --namespace production
    """
    pass


@k8s.command()
@click.argument('key')
@click.option('--namespace', '-n', default='default', help='Kubernetes namespace')
@click.option('--secret-name', '-s', help='K8s secret name (defaults to key)')
@click.option('--secret-key', '-k', default='password', help='Key in K8s secret (default: password)')
@click.option('--master-password', '-m', help='Master password if needed')
@click.option('--label', '-l', multiple=True, help='Additional labels (format: key=value)')
@click.option('--kubeconfig', help='Path to kubeconfig file')
@click.option('--create/--no-create', default=True, help='Create secret if missing (default: yes)')
def sync(key, namespace, secret_name, secret_key, master_password, label, kubeconfig, create):
    """Sync a kcpwd password to Kubernetes secret

    Examples:
        kcpwd k8s sync prod_db --namespace production
        kcpwd k8s sync api_key --secret-name my-api-secret
        kcpwd k8s sync db_pass --master-password MY_PASS
    """
    try:
        from .k8s import sync_to_k8s, K8sError

        # Parse labels
        labels = {}
        for lbl in label:
            if '=' in lbl:
                k, v = lbl.split('=', 1)
                labels[k] = v

        click.echo(f"🔄 Syncing '{key}' to Kubernetes...")

        result = sync_to_k8s(
            key=key,
            namespace=namespace,
            secret_name=secret_name,
            secret_key=secret_key,
            master_password=master_password,
            labels=labels if labels else None,
            kubeconfig=kubeconfig,
            create_if_missing=create
        )

        click.echo(f"✓ Successfully {result['action']} secret:")
        click.echo(f"  kcpwd key: {result['kcpwd_key']}")
        click.echo(f"  K8s secret: {result['k8s_secret']}")
        click.echo(f"  Namespace: {result['namespace']}")
        click.echo(f"  Secret key: {result['secret_key']}")

    except K8sError as e:
        click.echo(click.style(f"✗ Kubernetes error: {e}", fg='red'), err=True)
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'), err=True)


@k8s.command()
@click.option('--namespace', '-n', default='default', help='Kubernetes namespace')
@click.option('--prefix', '-p', help='Only sync keys with this prefix')
@click.option('--label', '-l', multiple=True, help='Additional labels (format: key=value)')
@click.option('--kubeconfig', help='Path to kubeconfig file')
@click.option('--skip-master', is_flag=True, help='Skip master-protected passwords')
def sync_all(namespace, prefix, label, kubeconfig, skip_master):
    """Sync all kcpwd passwords to Kubernetes

    Examples:
        kcpwd k8s sync-all --namespace production
        kcpwd k8s sync-all --prefix prod_ --namespace production
        kcpwd k8s sync-all --skip-master
    """
    try:
        from .k8s import sync_all_to_k8s, K8sError

        # Parse labels
        labels = {}
        for lbl in label:
            if '=' in lbl:
                k, v = lbl.split('=', 1)
                labels[k] = v

        click.echo(f"🔄 Syncing all passwords to Kubernetes...")
        click.echo(f"   Namespace: {namespace}")
        if prefix:
            click.echo(f"   Prefix: {prefix}")
        click.echo()

        result = sync_all_to_k8s(
            namespace=namespace,
            prefix=prefix,
            labels=labels if labels else None,
            kubeconfig=kubeconfig,
            skip_master_protected=skip_master
        )

        click.echo()
        click.echo(f"📊 Summary:")
        click.echo(f"   Total: {result['total']}")
        click.echo(f"   Synced: {click.style(str(result['synced']), fg='green')}")
        click.echo(f"   Failed: {click.style(str(result['failed']), fg='red')}")

        if result['failed'] > 0:
            click.echo(f"\n⚠️  Errors:")
            for error in result['errors']:
                click.echo(f"   • {error['key']}: {error['error']}")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'), err=True)


@k8s.command(name='import')
@click.argument('secret_name')
@click.option('--namespace', '-n', default='default', help='Kubernetes namespace')
@click.option('--key', '-k', help='kcpwd key name (defaults to secret name)')
@click.option('--secret-key', '-s', default='password', help='Key in K8s secret (default: password)')
@click.option('--master-password', '-m', is_flag=True, help='Store with master password protection')
@click.option('--kubeconfig', help='Path to kubeconfig file')
@click.option('--overwrite', is_flag=True, help='Overwrite if exists in kcpwd')
def import_secret(secret_name, namespace, key, secret_key, master_password, kubeconfig, overwrite):
    """Import Kubernetes secret to kcpwd

    Examples:
        kcpwd k8s import db-credentials --namespace production
        kcpwd k8s import api-secret --key my_api_key
        kcpwd k8s import prod-db --master-password
    """
    try:
        from .k8s import import_from_k8s, K8sError

        click.echo(f"📥 Importing secret '{secret_name}' from Kubernetes...")

        result = import_from_k8s(
            secret_name=secret_name,
            namespace=namespace,
            kcpwd_key=key,
            secret_key=secret_key,
            use_master=master_password,
            kubeconfig=kubeconfig,
            overwrite=overwrite
        )

        click.echo(f"✓ Successfully imported:")
        click.echo(f"  K8s secret: {result['k8s_secret']}")
        click.echo(f"  Namespace: {result['namespace']}")
        click.echo(f"  kcpwd key: {result['kcpwd_key']}")
        if result['master_protected']:
            click.echo(f"  Protection: 🔒 Master password")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'), err=True)


@k8s.command(name='list')
@click.option('--namespace', '-n', default='default', help='Kubernetes namespace')
@click.option('--managed-only', is_flag=True, help='Only show kcpwd-managed secrets')
@click.option('--kubeconfig', help='Path to kubeconfig file')
def list_secrets(namespace, managed_only, kubeconfig):
    """List Kubernetes secrets

    Examples:
        kcpwd k8s list --namespace production
        kcpwd k8s list --managed-only
    """
    try:
        from .k8s import list_k8s_secrets, K8sError

        click.echo(f"📋 Kubernetes secrets in '{namespace}':")
        if managed_only:
            click.echo(f"   (showing only kcpwd-managed secrets)")
        click.echo()

        secrets = list_k8s_secrets(
            namespace=namespace,
            managed_only=managed_only,
            kubeconfig=kubeconfig
        )

        if not secrets:
            click.echo("   No secrets found")
            return

        for secret in secrets:
            click.echo(f"  • {secret['name']}")
            click.echo(f"    Keys: {', '.join(secret['keys'])}")
            click.echo()

        click.echo(f"Total: {len(secrets)} secrets")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'), err=True)


@k8s.command()
@click.argument('secret_name')
@click.option('--namespace', '-n', default='default', help='Kubernetes namespace')
@click.option('--kubeconfig', help='Path to kubeconfig file')
@click.confirmation_option(prompt='Are you sure you want to delete this secret?')
def delete(secret_name, namespace, kubeconfig):
    """Delete Kubernetes secret

    Examples:
        kcpwd k8s delete db-credentials --namespace production
    """
    try:
        from .k8s import delete_k8s_secret, K8sError

        click.echo(f"🗑️  Deleting secret '{secret_name}'...")

        success = delete_k8s_secret(
            secret_name=secret_name,
            namespace=namespace,
            kubeconfig=kubeconfig
        )

        if success:
            click.echo(f"✓ Secret '{secret_name}' deleted from namespace '{namespace}'")

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'), err=True)


@k8s.command()
@click.option('--namespace', '-n', default='default', help='Kubernetes namespace')
@click.option('--interval', '-i', default=60, type=int, help='Sync interval in seconds (default: 60)')
@click.option('--prefix', '-p', help='Only sync keys with this prefix')
@click.option('--kubeconfig', help='Path to kubeconfig file')
def watch(namespace, interval, prefix, kubeconfig):
    """Watch and auto-sync passwords to Kubernetes

    Continuously monitors kcpwd and syncs changes to Kubernetes.

    Examples:
        kcpwd k8s watch --namespace production
        kcpwd k8s watch --namespace myapp --interval 120
        kcpwd k8s watch --prefix prod_ --namespace production
    """
    try:
        from .k8s import watch_and_sync

        watch_and_sync(
            namespace=namespace,
            interval=interval,
            prefix=prefix,
            kubeconfig=kubeconfig
        )

    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'), err=True)


@k8s.command(name='diff')
@click.option('--namespace', '-n', default='default',
              help='Kubernetes namespace to compare with')
@click.option('--prefix', '-p',
              help='Only check secrets with this prefix')
@click.option('--kubeconfig',
              help='Path to kubeconfig file')
@click.option('--quick', is_flag=True,
              help='Quick check without comparing values')
@click.option('--format', '-f',
              type=click.Choice(['table', 'json', 'summary']),
              default='summary',
              help='Output format (default: summary)')
def diff(namespace, prefix, kubeconfig, quick, format):
    """Compare kcpwd secrets with Kubernetes secrets

    Shows which secrets are in sync, differ, or missing between
    kcpwd and Kubernetes.

    Examples:
        # Basic diff
        kcpwd k8s diff --namespace production

        # Only check specific prefix
        kcpwd k8s diff -n prod --prefix prod_

        # Quick check (don't compare values)
        kcpwd k8s diff -n prod --quick

        # JSON output
        kcpwd k8s diff -n prod --format json
    """
    try:
        from .k8s import diff_with_k8s, get_drift_summary, K8sError
        import json

        click.echo(f"🔍 Comparing kcpwd with K8s namespace '{namespace}'...")
        if prefix:
            click.echo(f"   Prefix filter: {prefix}")
        click.echo()

        # Run diff
        result = diff_with_k8s(
            namespace=namespace,
            prefix=prefix,
            kubeconfig=kubeconfig,
            check_values=not quick
        )

        # Output based on format
        if format == 'json':
            click.echo(json.dumps(result, indent=2))

        elif format == 'table':
            # Table format
            click.echo("╔════════════════════════════════════════════════════════════╗")
            click.echo("║                    DRIFT COMPARISON                        ║")
            click.echo("╚════════════════════════════════════════════════════════════╝")
            click.echo()

            click.echo(f"{'Category':<30} {'Count':>10}")
            click.echo("-" * 60)
            click.echo(f"{'Total in kcpwd':<30} {result['total_kcpwd']:>10}")
            click.echo(f"{'Total in K8s':<30} {result['total_k8s']:>10}")
            click.echo(f"{'In sync':<30} {len(result['in_sync']):>10}")
            click.echo(f"{'Value differs':<30} {len(result['value_differs']):>10}")
            click.echo(f"{'Only in kcpwd':<30} {len(result['only_in_kcpwd']):>10}")
            click.echo(f"{'Only in K8s':<30} {len(result['only_in_k8s']):>10}")
            click.echo("-" * 60)
            click.echo(f"{'Sync percentage':<30} {result['sync_percentage']:>9.1f}%")

        else:  # summary (default)
            summary = get_drift_summary(result)
            click.echo(summary)

        # Exit code based on sync status
        if result['sync_percentage'] < 100:
            # Has drift, exit with code 1
            raise SystemExit(1)

    except K8sError as e:
        click.echo(click.style(f"✗ Kubernetes error: {e}", fg='red'), err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg='red'), err=True)
        raise click.Abort()


@cli.group()
def helm():
    """Helm values integration commands"""
    pass


@helm.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--strict/--no-strict', default=True, help='Fail on missing passwords')
@click.option('--validate/--no-validate', default=True, help='Validate YAML syntax')
def template(input_file, output, strict, validate):
    """Process Helm values template with kcpwd references

    Replaces {{ kcpwd('key') }} with actual passwords.

    Examples:
        kcpwd helm template values.yaml -o values-processed.yaml
        kcpwd helm template values.yaml --no-strict
    """
    try:
        from .helm import process_helm_values_file

        click.echo(f"📋 Processing Helm values: {input_file}")

        result = process_helm_values_file(
            input_file=input_file,
            output_file=output,
            strict=strict,
            validate_yaml=validate
        )

        if output:
            click.echo(f"✓ Processed values written to: {output}")
        else:
            click.echo("\n" + "=" * 60)
            import yaml
            click.echo(yaml.dump(result, default_flow_style=False))
            click.echo("=" * 60)

    except Exception as e:
        click.echo(f"✗ Failed to process values: {e}", err=True)
        raise click.Abort()


@helm.command()
@click.argument('values_file', type=click.Path(exists=True))
def scan(values_file):
    """Scan Helm values for kcpwd references

    Shows all {{ kcpwd('key') }} references found.

    Example:
        kcpwd helm scan values.yaml
    """
    try:
        from .helm import scan_values_for_kcpwd_refs

        with open(values_file, 'r') as f:
            content = f.read()

        refs = scan_values_for_kcpwd_refs(content)

        if not refs:
            click.echo("No kcpwd references found")
            return

        click.echo(f"\n📋 Found {len(refs)} kcpwd reference(s):\n")

        for i, ref in enumerate(refs, 1):
            click.echo(f"{i}. Key: {click.style(ref['key'], fg='green', bold=True)}")
            if ref['needs_master']:
                click.echo(f"   Master: {'Yes (inline)' if ref['master_inline'] else 'Yes (will prompt)'}")
            click.echo(f"   Match: {ref['full_match']}")
            click.echo()

    except Exception as e:
        click.echo(f"✗ Failed to scan values: {e}", err=True)
        raise click.Abort()


@helm.command()
@click.argument('chart_dir', type=click.Path(exists=True))
@click.option('--namespace', '-n', default='default', help='Kubernetes namespace')
@click.option('--values', default='values.yaml', help='Values file name')
@click.option('--release', help='Helm release name (for secret naming)')
@click.option('--kubeconfig', type=click.Path(), help='Path to kubeconfig')
def sync(chart_dir, namespace, values, release, kubeconfig):
    """Sync Helm chart's kcpwd references to K8s secrets

    Scans values.yaml for {{ kcpwd('key') }} references and syncs them to K8s.

    Examples:
        kcpwd helm sync ./mychart --namespace production
        kcpwd helm sync ./mychart --release myapp --namespace prod
    """
    try:
        from .helm import sync_helm_chart_secrets

        click.echo(f"🔄 Syncing Helm chart secrets to Kubernetes...")
        click.echo(f"   Chart: {chart_dir}")
        click.echo(f"   Namespace: {namespace}")
        if release:
            click.echo(f"   Release: {release}")
        click.echo()

        result = sync_helm_chart_secrets(
            chart_dir=chart_dir,
            namespace=namespace,
            values_file=values,
            release_name=release,
            kubeconfig=kubeconfig
        )

        if result['synced'] == 0:
            click.echo("ℹ️  No kcpwd references found in values")
            return

        click.echo(f"\n✓ Sync complete:")
        click.echo(f"  Synced: {result['synced']}")
        click.echo(f"  Failed: {result['failed']}")

        if result['references']:
            click.echo(f"\n📋 Synced secrets:")
            for ref in result['references']:
                click.echo(f"  • {ref['key']} → {ref['secret_name']} ({ref['namespace']})")

        if result['errors']:
            click.echo(f"\n⚠️  Errors:")
            for error in result['errors']:
                click.echo(f"  • {error['key']}: {error['error']}", err=True)

    except Exception as e:
        click.echo(f"✗ Failed to sync: {e}", err=True)
        raise click.Abort()


@helm.command()
def example():
    """Generate example Helm values with kcpwd integration

    Example:
        kcpwd helm example > values.yaml
    """
    from .helm import generate_example_values

    example = generate_example_values()
    click.echo(example)


@helm.command()
@click.argument('output_dir', type=click.Path())
def plugin(output_dir):
    """Generate Helm plugin package

    Creates files for helm-kcpwd plugin installation.

    Example:
        kcpwd helm plugin ./helm-kcpwd-plugin
    """
    try:
        from .helm import create_helm_plugin_package
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        click.echo(f"📦 Generating Helm plugin package...")

        package = create_helm_plugin_package()

        for filename, content in package.items():
            file_path = output_path / filename
            with open(file_path, 'w') as f:
                f.write(content)

            # Make shell scripts executable
            if filename.endswith('.sh'):
                file_path.chmod(0o755)

            click.echo(f"✓ Created: {file_path}")

        click.echo(f"\n✓ Helm plugin package created in: {output_path}")
        click.echo(f"\nTo install:")
        click.echo(f"  cd {output_path}")
        click.echo(f"  helm plugin install .")

    except Exception as e:
        click.echo(f"✗ Failed to generate plugin: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    cli()