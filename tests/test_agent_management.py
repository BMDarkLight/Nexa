import pytest
from fastapi.testclient import TestClient
from bson import ObjectId
import datetime

# Assuming your app and dbs are accessible for testing
from api.main import app, pwd_context
from api.auth import users_db, orgs_db
from api.agent import agents_db

# Use the TestClient for making requests to your FastAPI app
client = TestClient(app)

# --- Fixtures ---

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_db():
    """A fixture to clean the database before and after all tests in this module."""
    users_db.delete_many({})
    orgs_db.delete_many({})
    agents_db.delete_many({})
    yield
    users_db.delete_many({})
    orgs_db.delete_many({})
    agents_db.delete_many({})

@pytest.fixture(scope="module")
def org_admin_token():
    """
    Creates an organization, an orgadmin user, and returns a valid auth token.
    This is scoped to the module as it's a common requirement for all tests.
    """
    org = orgs_db.insert_one({"name": "TestCorp"})
    org_id = org.inserted_id
    
    user_doc = {
        "username": "test_org_admin",
        "password": pwd_context.hash("adminpass"),
        "permission": "orgadmin",
        "status": "active",
        "organization": org_id
    }
    users_db.insert_one(user_doc)

    resp = client.post("/signin", data={"username": "test_org_admin", "password": "adminpass"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    
    return token, org_id

@pytest.fixture(scope="module")
def regular_user_token(org_admin_token):
    """Creates a regular orguser for testing permission denials."""
    _, org_id = org_admin_token # Get the org_id from the admin fixture
    
    user_doc = {
        "username": "test_regular_user",
        "password": pwd_context.hash("userpass"),
        "permission": "orguser",
        "status": "active",
        "organization": org_id
    }
    users_db.insert_one(user_doc)

    resp = client.post("/signin", data={"username": "test_regular_user", "password": "userpass"})
    assert resp.status_code == 200
    return resp.json()["access_token"]

def auth_header(token):
    """Helper function to create authorization headers."""
    return {"Authorization": f"Bearer {token}"}


# --- Test Cases ---

def test_create_agent_as_org_admin(org_admin_token):
    """Tests that an orgadmin can successfully create a new agent."""
    token, _ = org_admin_token
    agent_payload = {
        "name": "Sales Assistant",
        "description": "Helps with sales inquiries.",
        "model": "gpt-4o",
        "temperature": 0.5,
        "tools": []
    }
    
    resp = client.post("/agents", headers=auth_header(token), json=agent_payload)
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Sales Assistant"
    assert data["temperature"] == 0.5
    assert agents_db.count_documents({"name": "Sales Assistant"}) == 1

def test_create_agent_as_regular_user(regular_user_token):
    """Tests that a regular user CANNOT create an agent."""
    agent_payload = {
        "name": "Unauthorized Agent", 
        "description": "Should not be created.", 
        "model": "gpt-3.5-turbo",
        "tools": []
    }
    
    resp = client.post("/agents", headers=auth_header(regular_user_token), json=agent_payload)
    
    assert resp.status_code == 403
    assert agents_db.count_documents({"name": "Unauthorized Agent"}) == 0

def test_list_agents_for_organization(org_admin_token):
    """Tests that an orgadmin can list all agents within their organization."""
    token, org_id = org_admin_token
    
    agents_db.delete_many({})
    now = datetime.datetime.now(datetime.UTC).isoformat()
    
    agents_db.insert_one({"name": "Agent A", "org": org_id, "model": "gpt-4", "description": "d", "tools": [], "created_at": now, "updated_at": now, "temperature": 0.7})
    agents_db.insert_one({"name": "Agent B", "org": org_id, "model": "gpt-4", "description": "d", "tools": [], "created_at": now, "updated_at": now, "temperature": 0.7})
    agents_db.insert_one({"name": "Agent C", "org": ObjectId(), "model": "gpt-4", "description": "d", "tools": [], "created_at": now, "updated_at": now, "temperature": 0.7})

    resp = client.get("/agents", headers=auth_header(token))
    
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    agent_names = {agent["name"] for agent in data}
    assert "Agent A" in agent_names
    assert "Agent B" in agent_names
    assert "Agent C" not in agent_names

def test_get_specific_agent(org_admin_token):
    """Tests retrieving a single agent by its ID."""
    token, org_id = org_admin_token
    now = datetime.datetime.now(datetime.UTC).isoformat()
    
    result = agents_db.insert_one({"name": "Specific Agent", "org": org_id, "model": "gpt-4", "description": "d", "tools": [], "created_at": now, "updated_at": now, "temperature": 0.7})
    agent_id = str(result.inserted_id)
    
    resp = client.get(f"/agents/{agent_id}", headers=auth_header(token))
    
    assert resp.status_code == 200
    assert resp.json()["name"] == "Specific Agent"

def test_update_agent_as_org_admin(org_admin_token):
    """Tests that an orgadmin can successfully update an agent."""
    token, org_id = org_admin_token
    now = datetime.datetime.now(datetime.UTC).isoformat()

    result = agents_db.insert_one({"name": "Original Name", "description": "Original Desc", "org": org_id, "model": "gpt-3.5-turbo", "tools": [], "created_at": now, "updated_at": now, "temperature": 0.7})
    agent_id = str(result.inserted_id)
    
    update_payload = {
        "name": "Updated Name",
        "temperature": 0.9,
    }
    
    resp = client.put(f"/agents/{agent_id}", headers=auth_header(token), json=update_payload)
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Name"
    assert data["temperature"] == 0.9
    
    updated_doc = agents_db.find_one({"_id": ObjectId(agent_id)})
    assert updated_doc["name"] == "Updated Name"

def test_update_agent_as_regular_user(regular_user_token, org_admin_token):
    """Tests that a regular user CANNOT update an agent."""
    _, org_id = org_admin_token
    now = datetime.datetime.now(datetime.UTC).isoformat()

    result = agents_db.insert_one({"name": "Untouchable Agent", "org": org_id, "model": "gpt-4", "tools": [], "created_at": now, "updated_at": now, "temperature": 0.7})
    agent_id = str(result.inserted_id)
    
    update_payload = {"name": "Attempted Update"}
    resp = client.put(f"/agents/{agent_id}", headers=auth_header(regular_user_token), json=update_payload)
    
    assert resp.status_code == 403
    db_agent = agents_db.find_one({"_id": ObjectId(agent_id)})
    assert db_agent["name"] == "Untouchable Agent"

def test_delete_agent_as_org_admin(org_admin_token):
    """Tests that an orgadmin can successfully delete an agent."""
    token, org_id = org_admin_token
    now = datetime.datetime.now(datetime.UTC).isoformat()

    result = agents_db.insert_one({"name": "Agent to Delete", "org": org_id, "model": "gpt-4", "tools": [], "created_at": now, "updated_at": now, "temperature": 0.7})
    agent_id = str(result.inserted_id)
    
    assert agents_db.count_documents({"_id": ObjectId(agent_id)}) == 1
    
    resp = client.delete(f"/agents/{agent_id}", headers=auth_header(token))
    
    assert resp.status_code == 200
    assert "deleted successfully" in resp.json()["message"]
    assert agents_db.count_documents({"_id": ObjectId(agent_id)}) == 0

def test_delete_agent_as_regular_user(regular_user_token, org_admin_token):
    """Tests that a regular user CANNOT delete an agent."""
    _, org_id = org_admin_token
    now = datetime.datetime.now(datetime.UTC).isoformat()

    result = agents_db.insert_one({"name": "Protected Agent", "org": org_id, "model": "gpt-4", "tools": [], "created_at": now, "updated_at": now, "temperature": 0.7})
    agent_id = str(result.inserted_id)

    resp = client.delete(f"/agents/{agent_id}", headers=auth_header(regular_user_token))

    assert resp.status_code == 403
    assert agents_db.count_documents({"_id": ObjectId(agent_id)}) == 1
