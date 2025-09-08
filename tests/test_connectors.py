import pytest
from fastapi.testclient import TestClient
from bson import ObjectId
import datetime
from datetime import timezone
from functools import partial

from api.main import app, pwd_context
from api.auth import users_db, orgs_db
from api.agent import agents_db, connectors_db, get_agent_components
from api.tools.google_sheet import read_google_sheet

client = TestClient(app)

@pytest.fixture(scope="function", autouse=True)
def setup_and_teardown_db():
    users_db.delete_many({})
    orgs_db.delete_many({})
    agents_db.delete_many({})
    connectors_db.delete_many({})
    yield
    users_db.delete_many({})
    orgs_db.delete_many({})
    agents_db.delete_many({})
    connectors_db.delete_many({})

# --- FIX: Changed scope to "function" to match the database fixture ---
@pytest.fixture(scope="function")
def org_admin_token():
    org = orgs_db.insert_one({"name": "ConnectorLogicTestCorp"})
    org_id = org.inserted_id
    
    user_doc = {
        "_id": ObjectId(),
        "username": "test_connector_logic_admin",
        "password": pwd_context.hash("logicadminpass"),
        "permission": "orgadmin",
        "status": "active",
        "organization": org_id
    }
    users_db.insert_one(user_doc)
    orgs_db.update_one({"_id": org_id}, {"$set": {"owner": user_doc["_id"]}})

    resp = client.post("/signin", data={"username": "test_connector_logic_admin", "password": "logicadminpass"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    
    return token, org_id

def auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def test_create_connector(org_admin_token):
    token, _ = org_admin_token
    payload = {
        "name": "My Main Sheet",
        "connector_type": "google_sheet",
        "settings": {"id": "12345"}
    }
    resp = client.post("/connectors", headers=auth_header(token), json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Main Sheet"
    assert connectors_db.count_documents({"name": "My Main Sheet"}) == 1

def test_list_connectors(org_admin_token):
    token, org_id = org_admin_token
    connectors_db.insert_one({"name": "Sheet A", "org": org_id, "connector_type": "google_sheet", "settings": {}})
    connectors_db.insert_one({"name": "Drive B", "org": org_id, "connector_type": "google_drive", "settings": {}})
    
    resp = client.get("/connectors", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert {c["name"] for c in data} == {"Sheet A", "Drive B"}

def test_update_connector(org_admin_token):
    token, org_id = org_admin_token
    result = connectors_db.insert_one({"name": "Old Name", "org": org_id, "connector_type": "google_sheet", "settings": {}})
    connector_id = str(result.inserted_id)
    
    update_payload = {"name": "New Name", "settings": {"id": "updated"}}
    resp = client.put(f"/connectors/{connector_id}", headers=auth_header(token), json=update_payload)
    
    assert resp.status_code == 200
    updated_doc = connectors_db.find_one({"_id": result.inserted_id})
    assert updated_doc["name"] == "New Name"
    assert updated_doc["settings"]["id"] == "updated"

def test_delete_connector_and_verify_pull_from_agent(org_admin_token):
    token, org_id = org_admin_token
    conn_result = connectors_db.insert_one({"name": "To Be Deleted", "org": org_id, "connector_type": "google_sheet", "settings": {}})
    connector_id = conn_result.inserted_id
    
    agent_result = agents_db.insert_one({"name": "Agent With Connector", "org": org_id, "description": "Test agent", "connector_ids": [connector_id], "model": "gpt-4"})
    agent_id = agent_result.inserted_id

    agent_before = agents_db.find_one({"_id": agent_id})
    assert connector_id in agent_before["connector_ids"]

    resp = client.delete(f"/connectors/{str(connector_id)}", headers=auth_header(token))
    assert resp.status_code == 200

    agent_after = agents_db.find_one({"_id": agent_id})
    assert connector_id not in agent_after.get("connector_ids", [])
    assert connectors_db.count_documents({"_id": connector_id}) == 0

@pytest.mark.asyncio
async def test_agent_logic_with_connector(org_admin_token):
    _, org_id = org_admin_token
    
    connector_doc = {
        "name": "Logic Test Sheet",
        "org": org_id,
        "connector_type": "google_sheet",
        "settings": {"credentials": "fake_creds_for_logic_test"}
    }
    conn_result = connectors_db.insert_one(connector_doc)
    connector_id = conn_result.inserted_id

    agent_doc = {
        "name": "Logic Test Agent",
        "org": org_id,
        "model": "gpt-4",
        "description": "A test agent for logic.",
        "connector_ids": [connector_id],
    }
    agent_result = agents_db.insert_one(agent_doc)
    agent_id = str(agent_result.inserted_id)

    llm, _, _, _ = await get_agent_components(
        question="Read data from my sheet.",
        organization_id=org_id,
        agent_id=agent_id
    )

    assert "tools" in llm.model_kwargs
    configured_tools = llm.model_kwargs["tools"]
    assert len(configured_tools) == 1
    
    configured_tool = configured_tools[0]
    assert configured_tool.name == "read_google_sheet_logic_test_sheet"
    assert isinstance(configured_tool.func, partial)
    assert configured_tool.func.keywords["settings"]["credentials"] == "fake_creds_for_logic_test"

