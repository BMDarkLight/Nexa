import pytest
from fastapi.testclient import TestClient
from bson import ObjectId
from unittest.mock import patch

from api.main import app, pwd_context
from api.auth import users_db
from api.agent import sessions_db

client = TestClient(app)

# --- Fixtures ---
@pytest.fixture(autouse=True)
def cleanup_db():
    """A fixture to automatically clean the database before and after each test."""
    users_db.delete_many({})
    sessions_db.delete_many({})
    yield
    users_db.delete_many({})
    sessions_db.delete_many({})

@pytest.fixture
def authenticated_user_token():
    """
    Creates a user, saves it to the DB, and returns a valid authentication token and user ID.
    This reduces code duplication in tests that require an authenticated user.
    """
    password = "testpassword123"
    user_doc = {
        "username": "test_session_user",
        "password": pwd_context.hash(password),
        "permission": "orguser",
        "status": "active"
    }
    result = users_db.insert_one(user_doc)
    user_id = result.inserted_id

    # Sign in to get a token
    resp = client.post("/signin", data={"username": user_doc["username"], "password": password})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    
    return token, str(user_id)

def auth_header(token):
    """Helper function to create authorization headers."""
    return {"Authorization": f"Bearer {token}"}


# --- Test Cases ---

@patch('api.main.agent_node')
def test_ask_creates_new_session(mock_agent_node, authenticated_user_token):
    """
    Tests that calling /ask without a session_id creates a new session in the database.
    """
    # Setup: Mock the AI agent's response
    mock_agent_node.return_value = {
        "agent": "TestAgent",
        "answer": "This is a mocked AI response.",
        "chat_history": [] 
    }
    
    token, user_id = authenticated_user_token
    query_payload = {"query": "Hello, world!"}
    
    # Action: Call the /ask endpoint
    resp = client.post("/ask", headers=auth_header(token), json=query_payload)
    
    # Assertions
    assert resp.status_code == 200
    assert resp.json()["response"] == "This is a mocked AI response."
    
    # Verify a new session was created in the database for the correct user
    assert sessions_db.count_documents({}) == 1
    session = sessions_db.find_one()
    assert session["user_id"] == user_id
    assert len(session["chat_history"]) == 1
    assert session["chat_history"][0]["user"] == "Hello, world!"

@patch('api.main.agent_node')
def test_ask_updates_existing_session(mock_agent_node, authenticated_user_token):
    """
    Tests that calling /ask with an existing session_id correctly appends to the chat history.
    """
    token, user_id = authenticated_user_token
    session_id = "test-session-123"
    
    # Setup 1: Manually create an existing session for the user
    sessions_db.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "chat_history": [{"user": "First question", "assistant": "First answer"}]
    })

    # Setup 2: Mock the AI agent's response
    mock_agent_node.return_value = {
        "agent": "TestAgent",
        "answer": "This is the second response.",
        "chat_history": [] # The function updates history itself
    }
    
    query_payload = {"query": "Second question", "session_id": session_id}
    
    # Action: Call the /ask endpoint with the existing session_id
    resp = client.post("/ask", headers=auth_header(token), json=query_payload)
    
    # Assertions
    assert resp.status_code == 200
    
    # Verify the session was updated, not replaced
    updated_session = sessions_db.find_one({"session_id": session_id})
    assert sessions_db.count_documents({}) == 1
    assert updated_session["chat_history"][0]["user"] == "Second question"
    assert updated_session["chat_history"][0]["assistant"] == "This is the second response."

def test_list_sessions_for_user(authenticated_user_token):
    """
    Tests that the /sessions endpoint returns only the sessions for the authenticated user.
    """
    token, user_id = authenticated_user_token
    
    # Setup: Create sessions for two different users
    sessions_db.insert_one({"session_id": "user1-session1", "user_id": user_id, "chat_history": []})
    sessions_db.insert_one({"session_id": "user1-session2", "user_id": user_id, "chat_history": []})
    sessions_db.insert_one({"session_id": "user2-session1", "user_id": "other_user_id", "chat_history": []})
    
    # Action: Call the /sessions endpoint
    resp = client.get("/sessions", headers=auth_header(token))
    
    # Assertions
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2 # Should only return the 2 sessions for the authenticated user
    session_ids = {s["session_id"] for s in data}
    assert "user1-session1" in session_ids
    assert "user1-session2" in session_ids

@patch('api.main.ChatOpenAI')
def test_get_specific_session(MockChatOpenAI, authenticated_user_token):
    """
    Tests retrieving a single, specific session by its ID.
    """
    # Setup 1: Mock the title generation AI call
    mock_instance = MockChatOpenAI.return_value
    mock_instance.invoke.return_value.content = "Mocked Session Title"

    token, user_id = authenticated_user_token
    session_id = "my-specific-session"
    chat_history = [{"user": "question", "assistant": "answer"}]
    
    # Setup 2: Create the session in the database
    sessions_db.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "chat_history": chat_history
    })
    
    # Action: Call the endpoint for the specific session
    resp = client.get(f"/sessions/{session_id}", headers=auth_header(token))
    
    # Assertions
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["chat_history"] == chat_history
    assert data["title"] == "Mocked Session Title"

def test_delete_session(authenticated_user_token):
    """
    Tests that a user can delete their own session.
    """
    token, user_id = authenticated_user_token
    session_id = "session-to-delete"
    
    # Setup: Create a session to be deleted
    sessions_db.insert_one({"session_id": session_id, "user_id": user_id})
    assert sessions_db.count_documents({"session_id": session_id}) == 1
    
    # Action: Call the delete endpoint
    resp = client.delete(f"/sessions/{session_id}", headers=auth_header(token))
    
    # Assertions
    assert resp.status_code == 200
    assert "deleted successfully" in resp.json()["message"]
    assert sessions_db.count_documents({"session_id": session_id}) == 0