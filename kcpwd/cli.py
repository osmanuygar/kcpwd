#!/usr/bin/env python3
"""
kcpwd - macOS Keychain Password Manager CLI
Stores passwords securely in macOS Keychain and copies them to clipboard
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


@click.group()
def cli():
    """kcpwd - macOS Keychain Password Manager"""
    pass


@cli.command()
@click.argument('key')
@click.argument('password')
@click.option('--master-password', '-m', is_flag=True,
              help='Protect this password with a master password')
def set(key: str, password: str, master_password: bool= False):
    """Store a password for a given key

    Examples:
        kcpwd set dbadmin asd123
        kcpwd set prod_db secret --master-password
    """
    if master_password:
        # Prompt for master password
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
    """Store a password with master password protection (shorthand)

    Example: kcpwd set-master prod_db secret123
    """
    # Prompt for master password
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
def get(key: str, master_password: bool = False):
    """Retrieve password and copy to clipboard

    Examples:
        kcpwd get dbadmin
        kcpwd get prod_db --master-password
    """
    if master_password:
        # Prompt for master password
        mp = getpass.getpass("Enter master password: ")

        password = get_master_password(key, mp)

        if password is None:
            click.echo(f"No password found for '{key}' or incorrect master password", err=True)
            return

        from .core import copy_to_clipboard
        if copy_to_clipboard(password):
            click.echo(f"✓ Password for '{key}' copied to clipboard")
        else:
            click.echo(f"✓ Password: {password}")
    else:
        password = _get_password(key, copy_to_clip=True)

        if password is None:
            click.echo(f"No password found for '{key}'", err=True)
            return

        click.echo(f"✓ Password for '{key}' copied to clipboard")


@cli.command()
@click.argument('key')
def get_master(key: str):
    """Retrieve master-protected password (shorthand)

    Example: kcpwd get-master prod_db
    """
    # Prompt for master password
    mp = getpass.getpass("Enter master password: ")

    password = get_master_password(key, mp)

    if password is None:
        click.echo(f"No password found for '{key}' or incorrect master password", err=True)
        return

    from .core import copy_to_clipboard
    if copy_to_clipboard(password):
        click.echo(f"✓ Password for '{key}' copied to clipboard")
    else:
        click.echo(f"✓ Password: {password}")


@cli.command()
@click.argument('key')
@click.confirmation_option(prompt=f'Are you sure you want to delete this password?')
def delete(key: str):
    """Delete a stored password

    Example: kcpwd delete dbadmin
    """
    if _delete_password(key):
        click.echo(f"✓ Password for '{key}' deleted")
    else:
        click.echo(f"No password found for '{key}'", err=True)


@cli.command()
@click.argument('key')
@click.confirmation_option(prompt=f'Are you sure you want to delete this master-protected password?')
def delete_master(key: str):
    """Delete a master-protected password (shorthand)

    Example: kcpwd delete-master prod_db
    """
    if delete_master_password(key):
        click.echo(f"✓ Master-protected password for '{key}' deleted")
    else:
        click.echo(f"No master-protected password found for '{key}'", err=True)


@cli.command()
def list():
    """List all stored password keys

    Shows regular passwords and master-protected passwords separately.
    Example: kcpwd list
    """
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
    click.echo(f"To delete: kcpwd delete <key>")
    click.echo(f"To delete master-protected: kcpwd delete-master <key>")


@cli.command()
@click.option('--length', '-l', default=16, help='Password length (default: 16)')
@click.option('--no-uppercase', is_flag=True, help='Exclude uppercase letters')
@click.option('--no-lowercase', is_flag=True, help='Exclude lowercase letters')
@click.option('--no-digits', is_flag=True, help='Exclude digits')
@click.option('--no-symbols', is_flag=True, help='Exclude symbols')
@click.option('--exclude-ambiguous', is_flag=True, help='Exclude ambiguous characters (0/O, 1/l/I)')
@click.option('--save', '-s', help='Save generated password with this key')
@click.option('--master-password', '-m', is_flag=True, help='Save with master password protection')
@click.option('--copy/--no-copy', default=True, help='Copy to clipboard (default: yes)')
def generate(length, no_uppercase, no_lowercase, no_digits, no_symbols, exclude_ambiguous,
             save, master_password, copy):
    """Generate a secure random password

    Examples:
        kcpwd generate
        kcpwd generate -l 20
        kcpwd generate -s myapi
        kcpwd generate -s prod_db --master-password
    """
    try:
        password = _generate_password(
            length=length,
            use_uppercase=not no_uppercase,
            use_lowercase=not no_lowercase,
            use_digits=not no_digits,
            use_symbols=not no_symbols,
            exclude_ambiguous=exclude_ambiguous
        )

        # Display password
        click.echo(f"\n🔐 Generated password: {click.style(password, fg='green', bold=True)}")

        # Copy to clipboard if requested
        if copy:
            from .core import copy_to_clipboard
            if copy_to_clipboard(password):
                click.echo("✓ Copied to clipboard")

        # Save if key provided
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
    except Exception as e:
        click.echo(f"Error generating password: {e}", err=True)


@cli.command()
@click.argument('filepath', type=click.Path())
@click.option('--keys-only', is_flag=True, help='Export only keys without passwords')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing file without confirmation')
def export(filepath: str, keys_only: bool, force: bool):
    """Export all passwords to a JSON file

    WARNING: Exported file contains passwords in PLAIN TEXT!
    Master-protected passwords are NOT included in exports.

    Examples:
        kcpwd export backup.json
        kcpwd export keys.json --keys-only
    """
    # Check if file exists
    if os.path.exists(filepath) and not force:
        if not click.confirm(f"File '{filepath}' already exists. Overwrite?"):
            click.echo("Export cancelled")
            return

    # Security warning
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

    # Perform export
    result = _export_passwords(filepath, include_passwords=not keys_only)

    if result['success']:
        click.echo(f"✓ {result['message']}")

        # Show master-protected keys if any
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
    """Import passwords from a JSON file

    Examples:
        kcpwd import backup.json
        kcpwd import backup.json --overwrite
        kcpwd import backup.json --dry-run
    """
    # Perform import
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


if __name__ == '__main__':
    cli()