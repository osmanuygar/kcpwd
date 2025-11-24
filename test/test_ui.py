"""
Test UI functionality
"""

import pytest
from fastapi.testclient import TestClient


# Only run if UI dependencies are installed
pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")

from kcpwd.ui.api import app, create_session, verify_session


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    """Get authenticated token"""
    import os
    os.environ["KCPWD_UI_SECRET"] = "test_secret"

    response = client.post("/api/auth", json={"secret": "test_secret"})
    assert response.status_code == 200
    return response.json()["token"]


def test_health_check(client):
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_auth_success(client):
    """Test successful authentication"""
    import os
    os.environ["KCPWD_UI_SECRET"] = "test_secret"

    response = client.post("/api/auth", json={"secret": "test_secret"})
    assert response.status_code == 200

    data = response.json()
    assert "token" in data
    assert data["message"] == "Authenticated successfully"


def test_auth_failure(client):
    """Test failed authentication"""
    import os
    os.environ["KCPWD_UI_SECRET"] = "correct_secret"

    response = client.post("/api/auth", json={"secret": "wrong_secret"})
    assert response.status_code == 401


def test_session_management():
    """Test session creation and verification"""
    token = create_session()
    assert token is not None
    assert verify_session(token) == True
    assert verify_session("invalid_token") == False


def test_info_endpoint(client, auth_token):
    """Test info endpoint"""
    response = client.get(
        "/api/info",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200

    data = response.json()
    assert "platform" in data
    assert "backend" in data


def test_list_passwords(client, auth_token):
    """Test list passwords endpoint"""
    response = client.get(
        "/api/passwords",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200

    data = response.json()
    assert "regular" in data
    assert "master_protected" in data
    assert "total" in data


def test_create_password(client, auth_token):
    """Test creating a password"""
    response = client.post(
        "/api/passwords",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "key": "test_ui_password",
            "password": "test123",
            "use_master": False
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] == True
    assert data["key"] == "test_ui_password"

    # Cleanup
    client.delete(
        "/api/passwords/test_ui_password",
        headers={"Authorization": f"Bearer {auth_token}"}
    )


def test_retrieve_password(client, auth_token):
    """Test retrieving a password"""
    # First create
    client.post(
        "/api/passwords",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "key": "test_retrieve",
            "password": "retrieve123",
            "use_master": False
        }
    )

    # Then retrieve
    response = client.post(
        "/api/passwords/retrieve",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "key": "test_retrieve",
            "use_master": False
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert data["password"] == "retrieve123"

    # Cleanup
    client.delete(
        "/api/passwords/test_retrieve",
        headers={"Authorization": f"Bearer {auth_token}"}
    )


def test_delete_password(client, auth_token):
    """Test deleting a password"""
    # Create
    client.post(
        "/api/passwords",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "key": "test_delete",
            "password": "delete123",
            "use_master": False
        }
    )

    # Delete
    response = client.delete(
        "/api/passwords/test_delete",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert response.json()["success"] == True


def test_generate_password(client, auth_token):
    """Test password generation"""
    response = client.post(
        "/api/generate",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "length": 16,
            "use_uppercase": True,
            "use_lowercase": True,
            "use_digits": True,
            "use_symbols": True
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert "password" in data
    assert len(data["password"]) == 16
    assert "strength" in data


def test_check_strength(client, auth_token):
    """Test password strength checking"""
    response = client.post(
        "/api/check-strength",
        headers={"Authorization": f"Bearer {auth_token}"},
        params={"password": "WeakPass1!"}
    )
    assert response.status_code == 200

    data = response.json()
    assert "score" in data
    assert "strength" in data
    assert "feedback" in data


def test_stats(client, auth_token):
    """Test statistics endpoint"""
    response = client.get(
        "/api/stats",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200

    data = response.json()
    assert "total" in data
    assert "regular" in data
    assert "master_protected" in data


def test_unauthorized_access(client):
    """Test that endpoints require authentication"""
    response = client.get("/api/passwords")
    assert response.status_code == 401


def test_logout(client, auth_token):
    """Test logout functionality"""
    response = client.post(
        "/api/logout",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200

    # Token should no longer work
    response = client.get(
        "/api/passwords",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 401