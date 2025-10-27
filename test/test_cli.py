import pytest
from click.testing import CliRunner
from kcpwd.cli import cli
from kcpwd import set_password, get_password, delete_password, require_password
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


# ===== CLI Tests =====

def test_set_password_cli(runner, cleanup):
    """Test setting a password via CLI"""
    result = runner.invoke(cli, ['set', 'testkey', 'testpass123'])
    assert result.exit_code == 0
    assert "Password stored for 'testkey'" in result.output

    # Verify it was actually stored
    stored = keyring.get_password(SERVICE_NAME, "testkey")
    assert stored == "testpass123"


def test_get_password_cli(runner, cleanup):
    """Test getting a password via CLI"""
    # First set a password
    keyring.set_password(SERVICE_NAME, "testkey", "testpass123")

    # Then get it
    result = runner.invoke(cli, ['get', 'testkey'])
    assert result.exit_code == 0
    assert "copied to clipboard" in result.output


def test_get_nonexistent_password_cli(runner):
    """Test getting a password that doesn't exist via CLI"""
    result = runner.invoke(cli, ['get', 'nonexistent'])
    assert result.exit_code == 0
    assert "No password found" in result.output


def test_delete_password_cli(runner, cleanup):
    """Test deleting a password via CLI"""
    # First set a password
    keyring.set_password(SERVICE_NAME, "testkey", "testpass123")

    # Then delete it (with confirmation)
    result = runner.invoke(cli, ['delete', 'testkey'], input='y\n')
    assert result.exit_code == 0
    assert "deleted" in result.output

    # Verify it was deleted
    stored = keyring.get_password(SERVICE_NAME, "testkey")
    assert stored is None


def test_list_command_cli(runner):
    """Test list command via CLI"""
    result = runner.invoke(cli, ['list'])
    assert result.exit_code == 0
    assert "Keychain Access" in result.output or "security find-generic-password" in result.output


# ===== Library Tests =====

def test_set_password_lib(cleanup):
    """Test setting a password via library"""
    result = set_password("testkey", "testpass123")
    assert result == True

    # Verify it was stored
    stored = keyring.get_password(SERVICE_NAME, "testkey")
    assert stored == "testpass123"


def test_get_password_lib(cleanup):
    """Test getting a password via library"""
    # First set a password
    keyring.set_password(SERVICE_NAME, "testkey", "testpass123")

    # Get it
    password = get_password("testkey")
    assert password == "testpass123"


def test_get_nonexistent_password_lib():
    """Test getting a password that doesn't exist via library"""
    password = get_password("nonexistent")
    assert password is None


def test_delete_password_lib(cleanup):
    """Test deleting a password via library"""
    # First set a password
    keyring.set_password(SERVICE_NAME, "testkey", "testpass123")

    # Delete it
    result = delete_password("testkey")
    assert result == True

    # Verify it was deleted
    stored = keyring.get_password(SERVICE_NAME, "testkey")
    assert stored is None


def test_delete_nonexistent_password_lib():
    """Test deleting a password that doesn't exist via library"""
    result = delete_password("nonexistent")
    assert result == False


# ===== Decorator Tests =====

def test_require_password_decorator(cleanup):
    """Test the @require_password decorator"""
    # Setup: store a password
    keyring.set_password(SERVICE_NAME, "testkey", "testpass123")

    # Create a function with decorator
    @require_password('testkey')
    def test_function(arg1, password=None):
        return f"{arg1}:{password}"

    # Call without password - should be injected
    result = test_function("hello")
    assert result == "hello:testpass123"


def test_require_password_decorator_custom_param(cleanup):
    """Test the @require_password decorator with custom parameter name"""
    # Setup: store a password
    keyring.set_password(SERVICE_NAME, "testkey", "api_token_123")

    # Create a function with decorator using custom param name
    @require_password('testkey', param_name='api_key')
    def test_function(arg1, api_key=None):
        return f"{arg1}:{api_key}"

    # Call without api_key - should be injected
    result = test_function("endpoint")
    assert result == "endpoint:api_token_123"


def test_require_password_decorator_missing_password():
    """Test the @require_password decorator when password doesn't exist"""

    # Create a function with decorator
    @require_password('nonexistent')
    def test_function(password=None):
        return password

    # Should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        test_function()

    assert "Password not found" in str(exc_info.value)


def test_require_password_decorator_with_provided_password(cleanup):
    """Test that decorator doesn't override manually provided password"""
    # Setup: store a password
    keyring.set_password(SERVICE_NAME, "testkey", "stored_pass")

    # Create a function with decorator
    @require_password('testkey')
    def test_function(password=None):
        return password

    # Call with explicit password - should use provided one
    result = test_function(password="manual_pass")
    assert result == "manual_pass"