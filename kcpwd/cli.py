#!/usr/bin/env python3
"""
kcpwd - macOS Keychain Password Manager CLI
Stores passwords securely in macOS Keychain and copies them to clipboard
"""

import click
import os
from .core import set_password as _set_password
from .core import get_password as _get_password
from .core import delete_password as _delete_password
from .core import generate_password as _generate_password
from .core import list_all_keys as _list_all_keys
from .core import export_passwords as _export_passwords
from .core import import_passwords as _import_passwords
from .core import SERVICE_NAME


@click.group()
def cli():
    """kcpwd - macOS Keychain Password Manager"""
    pass


@cli.command()
@click.argument('key')
@click.argument('password')
def set(key: str, password: str):
    """Store a password for a given key

    Example: kcpwd set dbadmin asd123
    """
    if _set_password(key, password):
        click.echo(f"✓ Password stored for '{key}'")
    else:
        click.echo(f"Error storing password", err=True)


@cli.command()
@click.argument('key')
def get(key: str):
    """Retrieve password and copy to clipboard

    Example: kcpwd get dbadmin
    """
    password = _get_password(key, copy_to_clip=True)

    if password is None:
        click.echo(f"No password found for '{key}'", err=True)
        return

    click.echo(f"✓ Password for '{key}' copied to clipboard")


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
def list():
    """List all stored password keys (not the actual passwords)

    Example: kcpwd list
    """
    keys = _list_all_keys()

    if not keys:
        click.echo("No passwords stored yet")
        click.echo(f"\nTo add a password: kcpwd set <key> <password>")
        return

    click.echo(f"Found {len(keys)} stored password(s):\n")
    for key in keys:
        click.echo(f"  • {key}")

    click.echo(f"\nTo retrieve: kcpwd get <key>")
    click.echo(f"To delete: kcpwd delete <key>")


@cli.command()
@click.option('--length', '-l', default=16, help='Password length (default: 16)')
@click.option('--no-uppercase', is_flag=True, help='Exclude uppercase letters')
@click.option('--no-lowercase', is_flag=True, help='Exclude lowercase letters')
@click.option('--no-digits', is_flag=True, help='Exclude digits')
@click.option('--no-symbols', is_flag=True, help='Exclude symbols')
@click.option('--exclude-ambiguous', is_flag=True, help='Exclude ambiguous characters (0/O, 1/l/I)')
@click.option('--save', '-s', help='Save generated password with this key')
@click.option('--copy/--no-copy', default=True, help='Copy to clipboard (default: yes)')
def generate(length, no_uppercase, no_lowercase, no_digits, no_symbols, exclude_ambiguous, save, copy):
    """Generate a secure random password

    Examples:
        kcpwd generate                          # 16-char password
        kcpwd generate -l 20                    # 20-char password
        kcpwd generate --no-symbols             # No special characters
        kcpwd generate -s myapi                 # Generate and save as 'myapi'
        kcpwd generate -l 6 --no-uppercase --no-lowercase --no-symbols  # 6-digit PIN
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
    Keep the file secure and delete it after use.

    Examples:
        kcpwd export backup.json                # Export with passwords
        kcpwd export keys.json --keys-only      # Export only key names
        kcpwd export backup.json -f             # Force overwrite
    """
    # Check if file exists
    if os.path.exists(filepath) and not force:
        if not click.confirm(f"File '{filepath}' already exists. Overwrite?"):
            click.echo("Export cancelled")
            return

    # Security warning for full export
    if not keys_only:
        click.echo(click.style("⚠️  WARNING: Exported file will contain passwords in PLAIN TEXT!",
                               fg='yellow', bold=True))
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
        kcpwd import backup.json                # Import, skip existing
        kcpwd import backup.json --overwrite    # Import, overwrite existing
        kcpwd import backup.json --dry-run      # Preview import
    """
    # Perform import
    result = _import_passwords(filepath, overwrite=overwrite, dry_run=dry_run)

    if result['success']:
        click.echo(f"✓ {result['message']}")

        if result['skipped_keys']:
            click.echo(f"\n📋 Skipped existing keys ({len(result['skipped_keys'])}):")
            for key in result['skipped_keys'][:10]:  # Show first 10
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