#!/usr/bin/env python3
"""
kcpwd - macOS Keychain Password Manager CLI
Stores passwords securely in macOS Keychain and copies them to clipboard
"""

import click
import keyring
import subprocess
from typing import Optional

# Service name for keyring (namespace for your passwords)
SERVICE_NAME = "kcpwd"


def copy_to_clipboard(text: str) -> bool:
    """Copy text to macOS clipboard using pbcopy"""
    try:
        process = subprocess.Popen(
            ['pbcopy'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        process.communicate(text.encode('utf-8'))
        return True
    except Exception as e:
        click.echo(f"Error copying to clipboard: {e}", err=True)
        return False


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
    try:
        keyring.set_password(SERVICE_NAME, key, password)
        click.echo(f"✓ Password stored for '{key}'")
    except Exception as e:
        click.echo(f"Error storing password: {e}", err=True)


@cli.command()
@click.argument('key')
def get(key: str):
    """Retrieve password and copy to clipboard

    Example: kcpwd get dbadmin
    """
    try:
        password = keyring.get_password(SERVICE_NAME, key)

        if password is None:
            click.echo(f"No password found for '{key}'", err=True)
            return

        if copy_to_clipboard(password):
            click.echo(f"✓ Password for '{key}' copied to clipboard")
        else:
            click.echo(f"Failed to copy password to clipboard", err=True)

    except Exception as e:
        click.echo(f"Error retrieving password: {e}", err=True)


@cli.command()
@click.argument('key')
@click.confirmation_option(prompt=f'Are you sure you want to delete this password?')
def delete(key: str):
    """Delete a stored password

    Example: kcpwd delete dbadmin
    """
    try:
        password = keyring.get_password(SERVICE_NAME, key)

        if password is None:
            click.echo(f"No password found for '{key}'", err=True)
            return

        keyring.delete_password(SERVICE_NAME, key)
        click.echo(f"✓ Password for '{key}' deleted")

    except Exception as e:
        click.echo(f"Error deleting password: {e}", err=True)


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