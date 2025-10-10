import pytest
from click.testing import CliRunner
from kcpwd.cli import cli
import keyring

SERVICE_NAME = "kcpwd"


@pytest.fixture
def runner():
    """Create a CLI runner for testing"""
    return CliRunner()


@pytest.fixture
def cleanup():
    """Cleanup test data after each test"""
    yield
    # Clean up test passwords after each test
    try:
        keyring.delete_password(SERVICE_NAME, "testkey")
    except:
        pass


def test_set_password(runner, cleanup):
    """Test setting a password"""
    result = runner.invoke(cli, ['set', 'testkey', 'testpass123'])
    assert result.exit_code == 0
    assert "Password stored for 'testkey'" in result.output

    # Verify it was actually stored
    stored = keyring.get_password(SERVICE_NAME, "testkey")
    assert stored == "testpass123"


def test_get_password(runner, cleanup):
    """Test getting a password"""
    # First set a password
    keyring.set_password(SERVICE_NAME, "testkey", "testpass123")

    # Then get it
    result = runner.invoke(cli, ['get', 'testkey'])
    assert result.exit_code == 0
    assert "copied to clipboard" in result.output


def test_get_nonexistent_password(runner):
    """Test getting a password that doesn't exist"""
    result = runner.invoke(cli, ['get', 'nonexistent'])
    assert result.exit_code == 0
    assert "No password found" in result.output


def test_delete_password(runner, cleanup):
    """Test deleting a password"""
    # First set a password
    keyring.set_password(SERVICE_NAME, "testkey", "testpass123")

    # Then delete it (with confirmation)
    result = runner.invoke(cli, ['delete', 'testkey'], input='y\n')
    assert result.exit_code == 0
    assert "deleted" in result.output

    # Verify it was deleted
    stored = keyring.get_password(SERVICE_NAME, "testkey")
    assert stored is None


def test_delete_nonexistent_password(runner):
    """Test deleting a password that doesn't exist"""
    result = runner.invoke(cli, ['delete', 'nonexistent'], input='y\n')
    assert result.exit_code == 0
    assert "No password found" in result.output


def test_list_command(runner):
    """Test list command"""
    result = runner.invoke(cli, ['list'])
    assert result.exit_code == 0
    assert "Keychain Access" in result.output or "security find-generic-password" in result.output