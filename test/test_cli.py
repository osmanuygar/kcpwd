import pytest
from click.testing import CliRunner
from kcpwd.cli import cli
from kcpwd import set_password, get_password, delete_password, require_password, generate_password
import keyring
import re

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


# ===== Password Generation Tests =====

def test_generate_password_default():
    """Test password generation with default settings"""
    password = generate_password()
    assert len(password) == 16
    assert any(c.isupper() for c in password)
    assert any(c.islower() for c in password)
    assert any(c.isdigit() for c in password)
    assert any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password)


def test_generate_password_custom_length():
    """Test password generation with custom length"""
    password = generate_password(length=20)
    assert len(password) == 20

    password = generate_password(length=8)
    assert len(password) == 8


def test_generate_password_no_symbols():
    """Test password generation without symbols"""
    password = generate_password(length=16, use_symbols=False)
    assert len(password) == 16
    assert not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password)
    assert any(c.isupper() for c in password)
    assert any(c.islower() for c in password)
    assert any(c.isdigit() for c in password)


def test_generate_password_digits_only():
    """Test generating numeric PIN"""
    pin = generate_password(
        length=6,
        use_uppercase=False,
        use_lowercase=False,
        use_symbols=False
    )
    assert len(pin) == 6
    assert pin.isdigit()


def test_generate_password_exclude_ambiguous():
    """Test password generation excluding ambiguous characters"""
    # Generate many passwords to check
    for _ in range(10):
        password = generate_password(length=20, exclude_ambiguous=True)
        assert 'O' not in password
        assert 'I' not in password
        assert 'l' not in password
        assert '0' not in password
        assert '1' not in password


def test_generate_password_minimum_length():
    """Test password generation with minimum length requirement"""
    with pytest.raises(ValueError, match="at least 4 characters"):
        generate_password(length=3)


def test_generate_password_no_character_types():
    """Test that at least one character type must be enabled"""
    with pytest.raises(ValueError, match="At least one character type"):
        generate_password(
            use_uppercase=False,
            use_lowercase=False,
            use_digits=False,
            use_symbols=False
        )


def test_generate_password_contains_all_types():
    """Test that generated password contains at least one of each enabled type"""
    password = generate_password(length=16)
    assert any(c.isupper() for c in password), "Should contain uppercase"
    assert any(c.islower() for c in password), "Should contain lowercase"
    assert any(c.isdigit() for c in password), "Should contain digit"
    assert any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password), "Should contain symbol"


def test_generate_password_randomness():
    """Test that generated passwords are different (randomness)"""
    passwords = [generate_password(length=16) for _ in range(10)]
    # All passwords should be unique
    assert len(set(passwords)) == 10


def test_generate_command_cli(runner):
    """Test generate command via CLI"""
    result = runner.invoke(cli, ['generate'])
    assert result.exit_code == 0
    assert "Generated password:" in result.output
    assert "Copied to clipboard" in result.output


def test_generate_command_cli_custom_length(runner):
    """Test generate command with custom length via CLI"""
    result = runner.invoke(cli, ['generate', '-l', '20'])
    assert result.exit_code == 0
    assert "Generated password:" in result.output


def test_generate_command_cli_no_symbols(runner):
    """Test generate command without symbols via CLI"""
    result = runner.invoke(cli, ['generate', '--no-symbols'])
    assert result.exit_code == 0
    assert "Generated password:" in result.output


def test_generate_command_cli_with_save(runner, cleanup):
    """Test generate command with save option via CLI"""
    result = runner.invoke(cli, ['generate', '-s', 'testkey'])
    assert result.exit_code == 0
    assert "Generated password:" in result.output
    assert "Saved as 'testkey'" in result.output

    # Verify it was saved
    stored = keyring.get_password(SERVICE_NAME, "testkey")
    assert stored is not None
    assert len(stored) == 16