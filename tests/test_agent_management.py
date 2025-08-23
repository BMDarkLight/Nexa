import pytest
from fastapi.testclient import TestClient
from bson import ObjectId
import datetime

# Assuming your app and dbs are accessible for testing
from api.main import app, pwd_context
from api.auth import users_db, orgs_db
from api.agent import agents_db, connectors_db

# Use the TestClient for making requests to your FastAPI app
client = TestClient(app)

# --- Fixtures ---
@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_db():
    """A fixture to clean the database before and after all tests in this module."""
    users_db.delete_many({})
    orgs_db.delete_many({})
    agents_db.delete_many({})
    connectors_db.delete_many({})
    yield
    users_db.delete_many({})
    orgs_db.delete_many({})
    agents_db.delete_many({})
    connectors_db.delete_many({})

@pytest.fixture(scope="module")
def org_admin_token():
    """
    Creates an organization, an orgadmin user, and returns a valid auth token and org_id.
    """
    org = orgs_db.insert_one({"name": "ConnectorTestCorp"})
    org_id = org.inserted_id
    
    user_doc = {
        "username": "test_connector_admin",
        "password": pwd_context.hash("connadminpass"),
        "permission": "orgadmin",
        "status": "active",
        "organization": org_id
    }
    users_db.insert_one(user_doc)

    resp = client.post("/signin", data={"username": "test_connector_admin", "password": "connadminpass"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    
    return token, org_id

@pytest.fixture(scope="module")
def regular_user_token(org_admin_token):
    """Creates a regular orguser for testing permission denials."""
    _, org_id = org_admin_token
    
    user_doc = {
        "username": "test_connector_user",
        "password": pwd_context.hash("connuserpass"),
        "permission": "orguser",
        "status": "active",
        "organization": org_id
    }
    users_db.insert_one(user_doc)

    resp = client.post("/signin", data={"username": "test_connector_user", "password": "connuserpass"})
    assert resp.status_code == 200
    return resp.json()["access_token"]

@pytest.fixture
def test_agent(org_admin_token):
    """Creates a test agent owned by the test organization."""
    _, org_id = org_admin_token
    now = datetime.datetime.now(datetime.UTC).isoformat()
    agent_doc = {
        "name": "Agent for Connectors",
        "org": org_id,
        "model": "gpt-4",
        "description": "An agent to test connectors on.",
        "tools": [],
        "created_at": now,
        "updated_at": now,
        "temperature": 0.7
    }
    result = agents_db.insert_one(agent_doc)
    return str(result.inserted_id)


def auth_header(token):
    """Helper function to create authorization headers."""
    return {"Authorization": f"Bearer {token}"}


# --- Test Cases for Connectors ---

def test_create_connector_as_org_admin(org_admin_token, test_agent):
    """Tests that an orgadmin can successfully create a connector for an agent."""
    token, _ = org_admin_token
    agent_id = test_agent
    
    connector_payload = {
        "name": "My Test Sheet", # <-- ADDED NAME
        "connector_type": "google_sheet",
        "settings": {"sheet_id": "12345", "credentials": "abcde"}
    }
    
    resp = client.post(f"/agents/{agent_id}/connectors", headers=auth_header(token), json=connector_payload)
    
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Test Sheet"
    assert data["connector_type"] == "google_sheet"
    assert data["settings"]["sheet_id"] == "12345"
    assert connectors_db.count_documents({"agent_id": ObjectId(agent_id)}) == 1

def test_create_connector_as_regular_user(regular_user_token, test_agent):
    """Tests that a regular user CANNOT create a connector."""
    agent_id = test_agent
    connector_payload = {
        "name": "Unauthorized Sheet", # <-- ADDED NAME
        "connector_type": "google_sheet",
        "settings": {"sheet_id": "should_not_be_created"}
    }
    
    resp = client.post(f"/agents/{agent_id}/connectors", headers=auth_header(regular_user_token), json=connector_payload)
    
    assert resp.status_code == 403
    assert connectors_db.count_documents({"agent_id": ObjectId(agent_id)}) == 0

def test_list_connectors_for_agent(org_admin_token, test_agent):
    """Tests listing all connectors associated with a specific agent."""
    token, _ = org_admin_token
    agent_id = test_agent

    connectors_db.insert_one({
        "agent_id": ObjectId(agent_id), 
        "name": "Listed Sheet", # <-- ADDED NAME
        "connector_type": "google_sheet", 
        "settings": {}
    })
    
    resp = client.get(f"/agents/{agent_id}/connectors", headers=auth_header(token))
    
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Listed Sheet"
    assert data[0]["connector_type"] == "google_sheet"

def test_update_connector_settings(org_admin_token, test_agent):
    """Tests that an orgadmin can update the settings of an existing connector."""
    token, _ = org_admin_token
    agent_id = test_agent
    
    result = connectors_db.insert_one({
        "agent_id": ObjectId(agent_id),
        "name": "Original Name", # <-- ADDED NAME
        "connector_type": "google_sheet",
        "settings": {"sheet_id": "old_id"}
    })
    connector_id = str(result.inserted_id)
    
    update_payload = {
        "name": "Updated Name",
        "settings": {"sheet_id": "new_id", "credentials": "updated_creds"}
    }
    
    resp = client.put(f"/agents/{agent_id}/connectors/{connector_id}", headers=auth_header(token), json=update_payload)
    
    assert resp.status_code == 200
    updated_doc = connectors_db.find_one({"_id": ObjectId(connector_id)})
    assert updated_doc["name"] == "Updated Name"
    assert updated_doc["settings"]["sheet_id"] == "new_id"
    assert updated_doc["settings"]["credentials"] == "updated_creds"

def test_delete_connector_as_org_admin(org_admin_token, test_agent):
    """Tests that an orgadmin can successfully delete a connector."""
    token, _ = org_admin_token
    agent_id = test_agent
    
    result = connectors_db.insert_one({
        "agent_id": ObjectId(agent_id), 
        "name": "To Be Deleted", # <-- ADDED NAME
        "connector_type": "google_sheet", "settings": {}
    })
    connector_id = str(result.inserted_id)
    
    assert connectors_db.count_documents({"_id": ObjectId(connector_id)}) == 1
    
    resp = client.delete(f"/agents/{agent_id}/connectors/{connector_id}", headers=auth_header(token))
    
    assert resp.status_code == 200
    assert "deleted successfully" in resp.json()["message"]
    assert connectors_db.count_documents({"_id": ObjectId(connector_id)}) == 0

def test_delete_connector_as_regular_user(regular_user_token, org_admin_token, test_agent):
    """Tests that a regular user CANNOT delete a connector."""
    _, org_id = org_admin_token
    agent_id = test_agent

    result = connectors_db.insert_one({
        "agent_id": ObjectId(agent_id), 
        "name": "Protected", # <-- ADDED NAME
        "org": org_id, 
        "connector_type": "google_sheet", 
        "settings": {}
    })
    connector_id = str(result.inserted_id)

    resp = client.delete(f"/agents/{agent_id}/connectors/{connector_id}", headers=auth_header(regular_user_token))

    assert resp.status_code == 403
    assert connectors_db.count_documents({"_id": ObjectId(connector_id)}) == 1
