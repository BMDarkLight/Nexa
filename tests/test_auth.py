# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from api.main import app, pwd_context
from api.auth import users_db, prospective_users_db, orgs_db
import datetime

client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup_db():
    users_db.delete_many({})
    prospective_users_db.delete_many({})
    orgs_db.delete_many({})
    yield
    users_db.delete_many({})
    prospective_users_db.delete_many({})
    orgs_db.delete_many({})

def create_user_in_db(username, password, permission="sysadmin", organization="testorg"):
    users_db.insert_one({
        "username": username,
        "password": pwd_context.hash(password),
        "firstname": "First",
        "lastname": "Last",
        "email": f"{username}@example.com",
        "phone": "1234567890",
        "organization": organization,
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow(),
        "permission": permission
    })

def auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def test_signup_and_signin():
    resp = client.post("/signup", json={
        "username": "orgadmin1",
        "password": "pass123",
        "firstname": "Org",
        "lastname": "Admin",
        "email": "orgadmin1@example.com",
        "phone": "1111111111",
        "organization": "Org1",
        "plan": "free"
    })
    assert resp.status_code == 200
    assert "prospect" in resp.json()["message"].lower()

    create_user_in_db("sysadmin", "pass123", permission="sysadmin")

    resp = client.post("/signin", data={"username": "sysadmin", "password": "pass123"})
    sys_token = resp.json()["access_token"]

    resp = client.post("/signup/approve/orgadmin1", headers=auth_header(sys_token))
    assert resp.status_code == 200

    resp = client.post("/signin", data={"username": "orgadmin1", "password": "pass123"})
    assert resp.status_code == 200
    orgadmin_token = resp.json()["access_token"]

    resp = client.get("/users", headers=auth_header(orgadmin_token))
    assert resp.status_code == 200
    assert any(u["username"] == "orgadmin1" for u in resp.json())

    resp = client.get("/users/orgadmin1", headers=auth_header(orgadmin_token))
    assert resp.status_code == 200
    assert resp.json()["username"] == "orgadmin1"

def test_user_delete_self_and_admin_delete():
    create_user_in_db("sysadmin", "pass123", permission="sysadmin")
    create_user_in_db("user1", "pass123", permission="orguser")

    resp = client.post("/signin", data={"username": "sysadmin", "password": "pass123"})
    sys_token = resp.json()["access_token"]

    resp = client.delete("/users/user1", headers=auth_header(sys_token))
    assert resp.status_code == 200

def test_permission_denied_for_regular_user_listing_users():
    create_user_in_db("sysadmin", "pass123", permission="sysadmin")
    create_user_in_db("user1", "pass123", permission="orguser")

    resp = client.post("/signin", data={"username": "user1", "password": "pass123"})
    token = resp.json()["access_token"]

    resp = client.get("/users", headers=auth_header(token))
    assert resp.status_code == 403

def test_invite_and_approve_user():
    create_user_in_db("orgadmin", "pass123", permission="orgadmin", organization="OrgX")
    orgs_db.insert_one({
        "name": "OrgX",
        "owner": "orgadmin",
        "users": ["orgadmin"],
        "description": "",
        "plan": "free",
        "settings": {},
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow()
    })

    resp = client.post("/signin", data={"username": "orgadmin", "password": "pass123"})
    org_token = resp.json()["access_token"]

    resp = client.post("/invite/user2", headers=auth_header(org_token))
    assert resp.status_code == 200

    resp = client.post("/invite/signin/user2", data={"username": "user2", "password": "pass123"})
    assert resp.status_code == 200

    resp = client.post("/invite/approve/user2", headers=auth_header(org_token))
    assert resp.status_code == 200

def test_public_endpoints_accessible():
    assert client.get("/").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.post("/signin", data={"username": "nonexist", "password": "x"}).status_code in (401, 422)