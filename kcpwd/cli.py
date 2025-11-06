#!/usr/bin/env python3
"""
kcpwd - macOS Keychain Password Manager CLI
Stores passwords securely in macOS Keychain and copies them to clipboard
"""

import click
from .core import set_password as _set_password
from .core import get_password as _get_password
from .core import delete_password as _delete_password
from .core import generate_password as _generate_password
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

    Note: Due to Keychain limitations, this requires manual Keychain access
    """
    click.echo("To view all stored keys, open Keychain Access app:")
    click.echo(f"  Search for: {SERVICE_NAME}")
    click.echo("\nAlternatively, use: security find-generic-password -s kcpwd")


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


if __name__ == '__main__':
    cli()