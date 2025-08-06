import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from api.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_users_db(monkeypatch):
    mock_db = MagicMock()
    monkeypatch.setattr("api.main.users_db", mock_db)
    return mock_db


def test_signup_success(mock_users_db):
    mock_users_db.find_one.return_value = None
    mock_users_db.insert_one.return_value.acknowledged = True
    mock_users_db.insert_one.return_value.inserted_id = "fakeid123"

    payload = {
        "username": "testuser",
        "password": "testpass",
        "firstname": "Test",
        "lastname": "User",
        "email": "test@example.com",
        "phone": "1234567890"
    }
    response = client.post("/signup", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "User created successfully"
    mock_users_db.insert_one.assert_called_once()


def test_signup_user_already_exists(mock_users_db):
    mock_users_db.find_one.return_value = {"username": "testuser"}

    payload = {"username": "testuser", "password": "testpass"}
    response = client.post("/signup", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "User already exists"


def test_signin_success(mock_users_db, monkeypatch):
    mock_user = {"username": "testuser", "password": "hashed"}
    mock_users_db.find_one.return_value = mock_user

    monkeypatch.setattr("api.main.pwd_context.verify", lambda p, h: True)
    monkeypatch.setattr("api.main.create_access_token", lambda data: "fake-jwt")

    form_data = {"username": "testuser", "password": "testpass"}
    response = client.post("/signin", data=form_data)
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "fake-jwt"
    assert data["token_type"] == "bearer"


def test_signin_invalid_credentials(mock_users_db, monkeypatch):
    mock_users_db.find_one.return_value = None 
    form_data = {"username": "nouser", "password": "wrong"}
    response = client.post("/signin", data=form_data)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_list_users_permission_denied(mock_users_db, monkeypatch):
    monkeypatch.setattr("api.main.verify_token", lambda t: {"permission": "user"})
    response = client.get("/users", headers={"Authorization": "Bearer faketoken"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_list_users_success(mock_users_db, monkeypatch):
    monkeypatch.setattr("api.main.verify_token", lambda t: {"permission": "admin"})
    mock_users_db.find.return_value = [{"username": "testuser", "permission": "user"}]

    response = client.get("/users", headers={"Authorization": "Bearer faketoken"})
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert users[0]["username"] == "testuser"


def test_get_user_not_found(mock_users_db, monkeypatch):
    monkeypatch.setattr("api.main.verify_token", lambda t: {"permission": "admin", "username": "missinguser"})
    mock_users_db.find_one.return_value = None

    response = client.get("/users/missinguser", headers={"Authorization": "Bearer faketoken"})
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_delete_user_success(mock_users_db, monkeypatch):
    monkeypatch.setattr("api.main.verify_token", lambda t: {"permission": "admin", "username": "testuser"})
    mock_users_db.delete_one.return_value.deleted_count = 1

    response = client.delete("/users/testuser", headers={"Authorization": "Bearer faketoken"})
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]


def test_delete_user_not_found(mock_users_db, monkeypatch):
    monkeypatch.setattr("api.main.verify_token", lambda t: {"permission": "admin", "username": "testuser"})
    mock_users_db.delete_one.return_value.deleted_count = 0

    response = client.delete("/users/testuser", headers={"Authorization": "Bearer faketoken"})
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"