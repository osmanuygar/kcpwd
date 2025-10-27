#!/usr/bin/env python3
"""
kcpwd - macOS Keychain Password Manager CLI
Stores passwords securely in macOS Keychain and copies them to clipboard
"""

import click
from .core import set_password as _set_password
from .core import get_password as _get_password
from .core import delete_password as _delete_password
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


if __name__ == '__main__':
    cli()