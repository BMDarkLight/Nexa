import pytest
import asyncio
from bson import ObjectId
import datetime
from functools import partial

# Assuming your app and dbs are accessible for testing
from api.auth import orgs_db
from api.agent import agents_db, connectors_db, get_agent_components
from api.tools.web import search_web
from api.tools.google_sheet import read_google_sheet

# --- Fixtures ---
@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_db():
    """A fixture to clean the database before and after all tests in this module."""
    orgs_db.delete_many({})
    agents_db.delete_many({})
    connectors_db.delete_many({})
    yield
    orgs_db.delete_many({})
    agents_db.delete_many({})
    connectors_db.delete_many({})

@pytest.fixture(scope="module")
def test_organization():
    """Creates a test organization and returns its ID."""
    org = orgs_db.insert_one({"name": "ConnectorLogicTestCorp"})
    return org.inserted_id

@pytest.fixture(scope="module")
def agent_with_web_tool(test_organization):
    """Creates an agent that only has a built-in tool."""
    now = datetime.datetime.now(datetime.UTC).isoformat()
    agent_doc = {
        "name": "Web Search Agent",
        "org": test_organization,
        "model": "gpt-4o-mini",
        "description": "An agent for searching the web.",
        "tools": ["search_web"],
        "created_at": now,
        "updated_at": now,
        "temperature": 0.1
    }
    result = agents_db.insert_one(agent_doc)
    return str(result.inserted_id)

@pytest.fixture(scope="module")
def agent_with_connector(test_organization):
    """Creates an agent and associates a Google Sheet connector with it."""
    now = datetime.datetime.now(datetime.UTC).isoformat()
    agent_doc = {
        "name": "Sheet Agent",
        "org": test_organization,
        "model": "gpt-4",
        "description": "An agent for reading spreadsheets.",
        "tools": [], # No built-in tools for this one
        "created_at": now,
        "updated_at": now,
        "temperature": 0.1
    }
    agent_result = agents_db.insert_one(agent_doc)
    agent_id = agent_result.inserted_id

    connector_doc = {
        "agent_id": agent_id,
        "name": "My Test Sheet",
        "connector_type": "google_sheet",
        "settings": {"credentials": "fake_creds_12345", "scope": "read_only"}
    }
    connectors_db.insert_one(connector_doc)
    return str(agent_id)


# --- Test Cases for Connector Logic ---

@pytest.mark.asyncio
async def test_components_for_agent_with_only_built_in_tools(test_organization, agent_with_web_tool):
    """
    Tests that get_agent_components correctly identifies and prepares an agent's
    built-in tools when no connectors are present.
    """
    llm, _, _, _ = await get_agent_components(
        question="What is the weather?",
        organization_id=test_organization,
        agent_id=agent_with_web_tool
    )

    # The LLM should be configured with tools
    assert "tools" in llm.model_kwargs
    configured_tools = llm.model_kwargs["tools"]
    assert len(configured_tools) == 1
    # Check that the tool is the correct function from the tools module
    # --- CHANGE: Use .name instead of .__name__ ---
    assert configured_tools[0].name == search_web.name

@pytest.mark.asyncio
async def test_components_for_agent_with_connector_tool(test_organization, agent_with_connector):
    """
    Tests that get_agent_components finds an agent's connector, configures the
    connector's tool with the correct settings, and prepares it for the LLM.
    """
    llm, _, _, _ = await get_agent_components(
        question="Read data from my sheet.",
        organization_id=test_organization,
        agent_id=agent_with_connector
    )

    assert "tools" in llm.model_kwargs
    configured_tools = llm.model_kwargs["tools"]
    assert len(configured_tools) == 1
    
    configured_tool = configured_tools[0]
    
    # The tool should be a LangChain 'Tool' object
    assert configured_tool.name == "read_google_sheet_my_test_sheet"
    
    # The function within the tool should be a 'partial' function, pre-loaded with settings
    assert isinstance(configured_tool.func, partial)
    assert configured_tool.func.func.name == read_google_sheet.name
    
    # Verify that the settings from the database were correctly injected
    injected_settings = configured_tool.func.keywords.get("settings")
    assert injected_settings is not None
    assert injected_settings["credentials"] == "fake_creds_12345"
    assert injected_settings["scope"] == "read_only"

@pytest.mark.asyncio
async def test_components_for_generalist_agent_has_no_tools(test_organization):
    """
    Tests that when no specific agent is selected (or routed to), the resulting
    'Generalist' agent has no tools configured.
    """
    # We pass an invalid agent_id on purpose to force the 'Generalist' path
    # in a predictable way for this test.
    llm, _, agent_name, _ = await get_agent_components(
        question="Just a general question.",
        organization_id=test_organization,
        agent_id=str(ObjectId()) # An ID that won't be found
    )

    assert agent_name == "Generalist"
    # The generalist model should not have any tools by default
    assert "tools" not in llm.model_kwargs or not llm.model_kwargs["tools"]
