import pytest
from httpx import AsyncClient
from api.main import app
from fastapi import status

test_user = {
    "username": "testuser",
    "password": "testpass123",
    "firstname": "Test",
    "lastname": "User",
    "email": "test@example.com",
    "phone": "1234567890"
}

@pytest.mark.asyncio
async def test_homepage_and_login_page():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res_home = await ac.get("/")
        res_login = await ac.get("/login")
    assert res_home.status_code == 200
    assert res_login.status_code == 200
    assert "Organizational AI" in res_home.text

@pytest.mark.asyncio
async def test_signup():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        data = {
            "username": test_user["username"],
            "password": test_user["password"],
            "firstname": test_user["firstname"],
            "lastname": test_user["lastname"],
            "email": test_user["email"],
            "phone": test_user["phone"]
        }
        response = await ac.post("/signup", data=data)

    assert response.status_code in (200, 400)
    if response.status_code == 200:
        assert "User created successfully" in response.json()["message"]

@pytest.mark.asyncio
async def test_signin_and_get_token():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        data = {
            "username": test_user["username"],
            "password": test_user["password"]
        }
        response = await ac.post("/signin", data=data)

    assert response.status_code == 200
    json_data = response.json()
    assert "access_token" in json_data
    assert json_data["token_type"] == "bearer"
    return json_data["access_token"]

@pytest.mark.asyncio
async def test_protected_user_routes():
    token = await test_signin_and_get_token()

    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res_users = await ac.get("/users", headers=headers)
        assert res_users.status_code in (403, 200)

        res_user = await ac.get(f"/users/{test_user['username']}", headers=headers)
        assert res_user.status_code in (403, 200, 404)

        res_delete = await ac.delete(f"/users/{test_user['username']}", headers=headers)
        assert res_delete.status_code in (403, 200, 404)