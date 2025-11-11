import pytest
import keyring
import cryptography
from kcpwd.master_protection import (
    set_master_password,
    get_master_password,
    delete_master_password,
    has_master_password,
    list_master_keys,
    MASTER_SERVICE_NAME
)
from kcpwd import set_password, get_password, delete_password


@pytest.fixture
def cleanup():
    """Cleanup test data after each test"""
    yield
    # Clean up test passwords
    test_keys = ["test1", "test2", "test3", "master_test1", "master_test2"]

    # Regular passwords
    for key in test_keys:
        try:
            keyring.delete_password("kcpwd", key)
        except:
            pass

    # Master-protected passwords
    for key in test_keys:
        try:
            keyring.delete_password(MASTER_SERVICE_NAME, key)
        except:
            pass


# ===== Master Password Tests =====

def test_set_master_password(cleanup):
    """Test setting a master-protected password"""
    result = set_master_password("test1", "password123", "MasterPass123!")
    assert result == True

    # Verify it was stored
    stored = keyring.get_password(MASTER_SERVICE_NAME, "test1")
    assert stored is not None
    assert stored != "password123"  # Should be encrypted


def test_get_master_password(cleanup):
    """Test retrieving a master-protected password"""
    # Set password
    set_master_password("test1", "secret123", "MyMaster!")

    # Get with correct master password
    password = get_master_password("test1", "MyMaster!")
    assert password == "secret123"


def test_get_master_password_wrong_password(cleanup):
    """Test that wrong master password returns None"""
    set_master_password("test1", "secret123", "CorrectMaster!")

    # Try with wrong password
    password = get_master_password("test1", "WrongMaster!")
    assert password is None


def test_get_nonexistent_master_password(cleanup):
    """Test getting a master password that doesn't exist"""
    password = get_master_password("nonexistent", "SomeMaster!")
    assert password is None


def test_delete_master_password(cleanup):
    """Test deleting a master-protected password"""
    # Set password
    set_master_password("test1", "secret123", "MyMaster!")

    # Delete it
    result = delete_master_password("test1")
    assert result == True

    # Verify it's gone
    stored = keyring.get_password(MASTER_SERVICE_NAME, "test1")
    assert stored is None


def test_delete_nonexistent_master_password(cleanup):
    """Test deleting a master password that doesn't exist"""
    result = delete_master_password("nonexistent")
    assert result == False


def test_has_master_password(cleanup):
    """Test checking if a key has master password protection"""
    # Before setting
    assert has_master_password("test1") == False

    # After setting
    set_master_password("test1", "secret123", "MyMaster!")
    assert has_master_password("test1") == True

    # After deleting
    delete_master_password("test1")
    assert has_master_password("test1") == False


def test_list_master_keys(cleanup):
    """Test listing all master-protected keys"""
    # Initially empty
    keys = list_master_keys()
    master_test_keys = [k for k in keys if k.startswith("master_test")]
    assert len(master_test_keys) == 0

    # Add some passwords
    set_master_password("master_test1", "pass1", "Master!")
    set_master_password("master_test2", "pass2", "Master!")

    # List should include them
    keys = list_master_keys()
    assert "master_test1" in keys
    assert "master_test2" in keys


def test_master_password_encryption_uniqueness(cleanup):
    """Test that same password with different master passwords produces different encrypted data"""
    password = "same_password"
    master1 = "MasterPass1!"
    master2 = "MasterPass2!"

    # Set same password with different master passwords
    set_master_password("test1", password, master1)
    set_master_password("test2", password, master2)

    # Get encrypted data
    encrypted1 = keyring.get_password(MASTER_SERVICE_NAME, "test1")
    encrypted2 = keyring.get_password(MASTER_SERVICE_NAME, "test2")

    # Encrypted data should be different
    assert encrypted1 != encrypted2


def test_master_password_salt_uniqueness(cleanup):
    """Test that multiple encryptions of same password produce different results (unique salt)"""
    password = "same_password"
    master = "MasterPass!"

    # Set same password twice
    set_master_password("test1", password, master)
    set_master_password("test2", password, master)

    # Get encrypted data
    encrypted1 = keyring.get_password(MASTER_SERVICE_NAME, "test1")
    encrypted2 = keyring.get_password(MASTER_SERVICE_NAME, "test2")

    # Should be different due to unique salt and nonce
    assert encrypted1 != encrypted2

    # But both should decrypt to same password
    assert get_master_password("test1", master) == password
    assert get_master_password("test2", master) == password


def test_master_and_regular_passwords_separate(cleanup):
    """Test that master-protected and regular passwords are stored separately"""
    key = "test1"
    regular_password = "regular_pass"
    master_password = "master_pass"
    master_key = "MasterPass!"

    # Set regular password
    set_password(key, regular_password)

    # Set master-protected password with same key
    set_master_password(key, master_password, master_key)

    # Both should exist independently
    assert get_password(key) == regular_password
    assert get_master_password(key, master_key) == master_password


def test_master_password_with_special_characters(cleanup):
    """Test master password with special characters in password and master password"""
    password = "p@$$w0rd!#%"
    master = "M@ster!P@ss#123"

    set_master_password("test1", password, master)
    retrieved = get_master_password("test1", master)

    assert retrieved == password


def test_master_password_with_unicode(cleanup):
    """Test master password with unicode characters"""
    password = "пароль123"  # Russian
    master = "主密码456"  # Chinese

    set_master_password("test1", password, master)
    retrieved = get_master_password("test1", master)

    assert retrieved == password


def test_master_password_long_password(cleanup):
    """Test with very long password"""
    password = "a" * 1000  # 1000 characters
    master = "MasterPass!"

    set_master_password("test1", password, master)
    retrieved = get_master_password("test1", master)

    assert retrieved == password
    assert len(retrieved) == 1000