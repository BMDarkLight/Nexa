import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

test_user = {
    "username": "testuser",
    "password": "testpass123",
    "firstname": "Test",
    "lastname": "User",
    "email": "test@example.com",
    "phone": "1234567890"
}

def test_homepage_and_login_page():
    res_home = client.get("/")
    res_login = client.get("/login")

    assert res_home.status_code == 200
    assert res_login.status_code == 200
    assert "Organizational AI" in res_home.text

def test_signup():
    response = client.post("/signup", data=test_user)

    assert response.status_code in (200, 400)
    if response.status_code == 200:
        assert "User created successfully" in response.json()["message"]

def test_signin_and_get_token():
    data = {
        "username": test_user["username"],
        "password": test_user["password"]
    }
    response = client.post("/signin", data=data)

    assert response.status_code == 200
    json_data = response.json()
    assert "access_token" in json_data
    assert json_data["token_type"] == "bearer"
    return json_data["access_token"]

def test_protected_user_routes():
    token = test_signin_and_get_token()
    headers = {"Authorization": f"Bearer {token}"}

    res_users = client.get("/users", headers=headers)
    assert res_users.status_code in (200, 403)

    res_user = client.get(f"/users/{test_user['username']}", headers=headers)
    assert res_user.status_code in (200, 403, 404)

    res_delete = client.delete(f"/users/{test_user['username']}", headers=headers)
    assert res_delete.status_code in (200, 403, 404)