from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Form
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from passlib.context import CryptContext
from dotenv import load_dotenv, find_dotenv
from typing import List, Optional
from pydantic import BaseModel, Field
from bson import ObjectId

from api.auth import create_access_token, verify_token, prospective_users_db, users_db, orgs_db
from api.mail import send_email

import datetime
import secrets

app = FastAPI(title="Organizational AI API")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/signin")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv(dotenv_path=find_dotenv())

# --- Authorization Compatible Swagger UI ---
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Organizational AI API",
        version="1.0.0",
        description="Gen-AI for Organizations. Streamline all workflows across messenger, workspaces and organizational system in one place, and make them smart using AI.",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2Password": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/signin",
                    "scopes": {}
                }
            }
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    public_paths = {"/signin", "/signup", "/login", "/", "/forgot-password", "/reset-password", "/invite/signup/{username}"}
    for path_name, path in openapi_schema["paths"].items():
        if path_name in public_paths:
            continue
        for operation in path.values():
            operation["security"] = [{"OAuth2Password": []}, {"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# --- Database Initialization ---
import os
import secrets
import datetime

def create_initial_sysadmin():
    if users_db.count_documents({"permission": "sysadmin"}) < 1:
        username = os.getenv("SYSADMIN_USERNAME")
        password = os.getenv("SYSADMIN_PASSWORD")
        firstname = os.getenv("SYSADMIN_FIRSTNAME", "")
        lastname = os.getenv("SYSADMIN_LASTNAME", "")
        email = os.getenv("SYSADMIN_EMAIL", "")
        phone = os.getenv("SYSADMIN_PHONE", "")
        if not username or not password:
            print("SYSADMIN_USERNAME or SYSADMIN_PASSWORD not set in env; skipping sysadmin creation")
            return
        
        hashed_password = pwd_context.hash(password)
        user = {
            "username": username,
            "password": hashed_password,
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "phone": phone,
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow(),
            "permission": "sysadmin",
        }
        user_result = users_db.insert_one(user)

        if user_result.acknowledged:
            print(f"Created initial sysadmin user: {username}")
        else:
            print("Failed to create initial sysadmin user")

create_initial_sysadmin()

SERVER_URL = os.getenv("SERVER_URL", "http://localhost")
UI_PORT = os.getenv("UI_PORT", "3000")
API_PORT = os.getenv("API_PORT", "8000")

# --- Home Page ---
@app.get("/", response_class=HTMLResponse)
async def main_page():
    with open("api/pages/home.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content)

# --- Embedded Login Page ---
@app.get("/login", response_class=HTMLResponse)
def login():
    with open("api/pages/login.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content)

# --- Embedded Chatbot Page ---
@app.get("/chatbot", response_class=HTMLResponse)
def chatbot():
    with open("api/pages/chatbot.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content)

# --- Authentication Routes ---
class SignupModel(BaseModel):
    username: str
    password: str
    firstname: str = ""
    lastname: str = ""
    email: str = ""
    phone: str = ""
    organization: str
    plan: str = "free"

@app.post("/signup")
def signup(form_data: SignupModel):
    if users_db.find_one({"username":form_data.username}) or prospective_users_db.find_one({"username": form_data.username}):
        raise HTTPException(status_code=400, detail="User already exists")
    hashed_password = pwd_context.hash(form_data.password)
    if orgs_db.find_one({"name": form_data.organization}):
        raise HTTPException(status_code=400, detail="Organization already exists")
    
    result = prospective_users_db.insert_one({
        "username": form_data.username,
        "password": hashed_password,
        "firstname": form_data.firstname,
        "lastname": form_data.lastname,
        "email": form_data.email,
        "phone": form_data.phone or "",
        "organization": None,
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow(),
        "permission": "orgadmin"
    })
    user_id = result.inserted_id
    result_org = orgs_db.insert_one({
        "name": form_data.organization,
        "owner": user_id,
        "users": [user_id],
        "description": "",
        "plan": form_data.plan or "free",
        "settings": {},
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow()
    })
    org_id = result_org.inserted_id
    prospective_users_db.update_one(
        {"_id": user_id},
        {"$set": {"organization": org_id}}
    )
    if not result.acknowledged:
        raise HTTPException(status_code=500, detail="User creation failed")
    if not result_org.acknowledged:
        raise HTTPException(status_code=500, detail="Organization creation failed")
    return {"message": "User successfully registered in prospect list", "_id": str(user_id)}

class SigninModel(BaseModel):
    username: str
    password: str

@app.post("/signin")
def signin(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.find_one({"username": form_data.username})
    if not user or not pwd_context.verify(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.get("status") == "pending":
        raise HTTPException(status_code=403, detail="User is pending approval")
    
    access_token = create_access_token(data={"sub": user["username"]})

    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/forgot-password")
def forgot_password(username: str):
    user = users_db.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    reset_token = secrets.token_urlsafe(16)
    users_db.update_one({"username": username}, {"$set": {"reset_token": reset_token}})
    
    reset_link = f"{SERVER_URL}:{UI_PORT}/login/reset-password?token={reset_token}&username={username}"
    
    if user["email"]:
        send_email(
            to=user["email"],
            subject="Password Reset Request",
            body=f"Click the link to reset your password: {reset_link}"
        )
    else:
        raise HTTPException(status_code=400, detail="User does not have an email set")
    
    return {"message": "Password reset link sent to your email"}

@app.post("/reset-password")
def reset_password(username: str, token: str, new_password: str):
    user = users_db.find_one({"username": username, "reset_token": token})
    if not user:
        raise HTTPException(status_code=404, detail="Invalid credentials")
    
    hashed_password = pwd_context.hash(new_password)
    users_db.update_one(
        {"username": username},
        {
            "$set": {
                "password": hashed_password,
                "reset_token": None,
                "updated_at": datetime.datetime.utcnow()
            }
        }
    )
    
    return {"message": "Password reset successfully"}

# --- Prospective Users Routes ---
@app.post("/signup/approve/{username}")
def approve_signup(username: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    prospective_user = prospective_users_db.find_one({"username": username})
    if not prospective_user:
        raise HTTPException(status_code=404, detail="Prospective user not found")
    
    if users_db.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="User already exists")
    
    hashed_password = prospective_user["password"]
    result = users_db.insert_one({
        "username": prospective_user["username"],
        "password": hashed_password,
        "firstname": prospective_user["firstname"],
        "lastname": prospective_user["lastname"],
        "email": prospective_user["email"],
        "phone": prospective_user["phone"],
        "organization": prospective_user["organization"],
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow(),
        "permission": prospective_user["permission"]
    })
    user_id = result.inserted_id
    orgs_db.update_one(
        {"_id": prospective_user["organization"]},
        {
            "$set": {"owner": user_id},
            "$addToSet": {"users": user_id}
        }
    )
    if not result.acknowledged:
        raise HTTPException(status_code=500, detail="User creation failed")
    
    prospective_users_db.delete_one({"username": username})

    return {"message": "User approved and created successfully", "_id": str(user_id)}

@app.post("/signup/reject/{username}")
def reject_signup(username: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    prospective_user = prospective_users_db.find_one({"username": username})
    if not prospective_user:
        raise HTTPException(status_code=404, detail="Prospective user not found")
    
    org_result = orgs_db.delete_one({"_id": prospective_user["organization"]})
    result = prospective_users_db.delete_one({"username": username})
    if result.deleted_count == 0 or org_result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to reject user")
    
    return {"message": "User rejected successfully"}

@app.get("/signup/prospective-users", response_model=List[dict])
def list_prospective_users(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    prospective_users = list(prospective_users_db.find({}, {"_id": 0, "password": 0}))
    return prospective_users

@app.get("/signup/prospective-users/{username}", response_model=dict)
def get_prospective_user(username: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    prospective_user = prospective_users_db.find_one({"username": username}, {"_id": 0, "password": 0})

    if not prospective_user:
        raise HTTPException(status_code=404, detail="Prospective user not found")
    
    return prospective_user

# --- Organization Management Routes ---
@app.get("/organizations", response_model=dict)
def organization(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return orgs_db.find({}, {"_id": 0})

@app.get("/organizations/{name}", response_model=dict)
def get_organization(name: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    organization = orgs_db.find_one({"name": name}, {"_id": 0})
    
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return organization

# --- Organization User Routes ---
@app.post("/invite/{username}")
def invite_user(username: str, email: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if users_db.find_one({"username":username}) or prospective_users_db.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="User already exists")

    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied")

    organization = orgs_db.find_one({"owner": ObjectId(user["_id"])})
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    invite_code = secrets.token_urlsafe(16)

    users_db.insert_one({
        "username": username,
        "email": email,
        "organization": organization["_id"],
        "permission": "orguser",
        "invite_code": invite_code,
        "status": "pending",
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow()
    })

    send_email(
        to=email,
        subject="Invitation to Join Organization",
        body=(
            f"You have been invited to join the organization '{organization['name']}'. "
            f"Use the following invitation code to complete your signup:\n\n{invite_code}"
        )
    )

    return {"message": f"User '{username}' invited successfully"}

class InviteSignupModel(BaseModel):
    invite_code: str
    password: str
    firstname: str = ""
    lastname: str = ""
    phone: str = ""


@app.post("/invite/signup/{username}")
def invite_signin(
    form_data: InviteSignupModel
):
    user = users_db.find_one({"invite_code": form_data.invite_code})
    if not user:
        raise HTTPException(status_code=404, detail="Invite not found")

    if user.get("password"):
        raise HTTPException(status_code=400, detail="User already has a password set")

    if user.get("status") != "pending":
        raise HTTPException(status_code=403, detail="User is not in pending status")
    
    username = user["username"]

    hashed_password = pwd_context.hash(form_data.password)

    result = users_db.update_one(
        {"username": username},
        {
            "$set": {
                "password": hashed_password,
                "firstname": form_data.firstname,
                "lastname": form_data.lastname,
                "phone": form_data.phone or "",
                "status": "active",
                "updated_at": datetime.datetime.utcnow()
            },
            "$unset": {"invite_code": ""}
        }
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to register invited user")

    orgadmin = users_db.find_one({
        "organization": user["organization"],
        "permission": "orgadmin"
    })

    if orgadmin and orgadmin.get("email"):
        send_email(
            to=orgadmin["email"],
            subject=f"Invited user {username} has signed up, Please approve them.",
            body=f"The user '{username}' has signed up with the organization '{user['organization']}'."
        )

        send_email(
            to=user["email"],
            subject=f"Welcome to the Organization {user['organization']}",
            body=f"Your account has been signed up {form_data.firstname}!"
        )

    return {"message": "Invited user signed up successfully."}

# --- User Management Routes ---
@app.get("/users", response_model=List[dict])
def list_users(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") == "sysadmin":
        query = {}
    elif user.get("permission") == "orgadmin":
        query = {"organization": user.get("organization")}
    else:
        raise HTTPException(status_code=403, detail="Permission denied")

    users = list(users_db.find(query, {"_id": 0, "password": 0}))

    for user in users:
        if "organization" in user and isinstance(user.get("organization"), ObjectId):
            user["organization"] = str(user["organization"])

    return users

@app.get("/users/{username}")
def get_user(username: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if not (user.get("permission") == "sysadmin" or user["username"] == username):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    user_data = users_db.find_one({"username": username}, {"_id": 0, "password": 0})

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("permission") != "sysadmin" and user_data.get("organization") != user.get("organization"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return user_data

@app.delete("/users/{username}")
def delete_user(username: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated") 
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if not (user.get("permission") == "sysadmin" or user["username"] == username):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if user.get("permission") != "sysadmin" and user.get("organization") != users_db.find_one({"username": username}).get("organization"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    result = users_db.delete_one({"username": username})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": f"User '{username}' deleted successfully"}

# --- Agent Routes ---
from api.agent import get_agent_components, sessions_db, agents_db

import uuid

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    agent_id: Optional[str] = None

class QueryResponse(BaseModel):
    agent_name: str
    response: str
    session_id: str

def save_chat_history(session_id: str, user_id: str, chat_history: list, query: str, answer: str, agent_id: str, agent_name: str):
    new_history_entry = {
        "user": query,
        "assistant": answer,
        "agent_id": agent_id,
        "agent_name": agent_name
    }
    updated_chat_history = chat_history + [new_history_entry]
    sessions_db.update_one(
        {"session_id": session_id},
        {"$set": {"chat_history": updated_chat_history, "user_id": user_id}},
        upsert=True
    )

@app.post("/ask")
async def ask(
    query: QueryRequest, 
    background_tasks: BackgroundTasks, 
    token: str = Depends(oauth2_scheme)
):
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise e

    if not query.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    if not user.get("organization") and user.get("permission") != "sysadmin":
        raise HTTPException(status_code=403, detail="User is not associated with any organization.")

    agent_id_to_use = None
    if query.agent_id:
        if not ObjectId.is_valid(query.agent_id):
            raise HTTPException(status_code=400, detail="Invalid agent_id format.")

        agent_query = {"_id": ObjectId(query.agent_id)}
        if user.get("permission") != "sysadmin":
            agent_query["org"] = user["organization"]
        agent = agents_db.find_one(agent_query)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to use it.")
        agent_id_to_use = query.agent_id

    session_id = query.session_id or str(uuid.uuid4())
    session = sessions_db.find_one({"session_id": session_id})

    if session and session.get("user_id") != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Permission denied for this session.")

    chat_history = session.get("chat_history", []) if session else []

    org_id = user.get("organization") if user.get("organization") else None

    llm, messages, agent_name, agent_id = await get_agent_components(
        question=query.query,
        organization_id=org_id,
        chat_history=chat_history,
        agent_id=agent_id_to_use
    )

    async def response_generator():
        full_answer = ""
        async for chunk in llm.astream(messages):
            content = chunk.content or ""
            full_answer += content
            yield content
        
        background_tasks.add_task(
            save_chat_history,
            session_id=session_id,
            user_id=str(user["_id"]),
            chat_history=chat_history,
            query=query.query,
            answer=full_answer,
            agent_id=agent_id,
            agent_name=agent_name
        )

    return StreamingResponse(response_generator(), media_type="text/plain", headers={
        "X-Agent-Name": agent_name,
        "X-Session-Id": session_id,
        "Access-Control-Expose-Headers": "X-Agent-Name, X-Session-Id"
    })

# --- Session Management Routes ---
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage

@app.get("/sessions", response_model=List[dict])
def list_sessions(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    sessions = list(sessions_db.find({"user_id": str(user["_id"])}, {"_id": 0}))
    return sessions

@app.get("/sessions/{session_id}", response_model=dict)
def get_session(session_id: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    session = sessions_db.find_one({"session_id": session_id, "user_id": str(user["_id"])}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    title_generator = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)

    chat_history = session["chat_history"]

    prompts = [
        SystemMessage("You are a title generator. You receive the users chat history in the chatbot and generate a short title based on it. The title should represent what is going on in the chat, the title shouldn't be flashy or trendy, just helpful and straight to the point."),
    ]

    for entry in chat_history:
        prompts.append(HumanMessage(content=entry["user"]))
        prompts.append(AIMessage(content=entry["assistant"]))
    
    title = title_generator.invoke(prompts)
    
    return {**session, "title":title.content}

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    result = sessions_db.delete_one({
        "session_id": session_id,
        "user_id": str(user["_id"])
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": f"Session '{session_id}' deleted successfully"}

# --- Agent Management Routes ---
from api.agent import Agent, AgentCreate, AgentUpdate

@app.get("/agents", response_model=List[Agent])
def list_agents(token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    if not user.get("organization"):
        return []
    
    agents_cursor = agents_db.find({"org": ObjectId(user["organization"])})
    return [Agent(**agent) for agent in agents_cursor]


@app.post("/agents", response_model=Agent)
def create_agent(agent: AgentCreate, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)

    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can create agents.")

    agent_data = agent.model_dump(by_alias=True, exclude={"id"}) 
    
    agent_data["org"] = ObjectId(user["organization"])
    agent_data["created_at"] = datetime.datetime.utcnow().isoformat()
    agent_data["updated_at"] = agent_data["created_at"]

    result = agents_db.insert_one(agent_data)
    
    created_agent = agents_db.find_one({"_id": result.inserted_id})
    if not created_agent:
        raise HTTPException(status_code=500, detail="Failed to create and retrieve the agent.")
        
    return Agent(**created_agent)


@app.get("/agents/{agent_id}", response_model=Agent)
def get_agent(agent_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    
    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID format.")
    
    agent = agents_db.find_one({
        "_id": ObjectId(agent_id), 
        "org": ObjectId(user["organization"])
    })

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to view it.")
    
    return Agent(**agent)


@app.put("/agents/{agent_id}", response_model=Agent)
def update_agent(agent_id: str, agent_update: AgentUpdate, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    
    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can update agents.")

    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID format.")

    if not agents_db.find_one({"_id": ObjectId(agent_id), "org": ObjectId(user["organization"])}):
        raise HTTPException(status_code=404, detail="Agent not found.")
    
    update_data = agent_update.model_dump(exclude_unset=True, exclude_none=True)
    
    for field in ["id", "_id", "org", "created_at"]:
        update_data.pop(field, None)

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid update data provided.")

    update_data["updated_at"] = datetime.datetime.utcnow().isoformat()

    agents_db.update_one(
        {"_id": ObjectId(agent_id)},
        {"$set": update_data}
    )

    updated_agent = agents_db.find_one({"_id": ObjectId(agent_id)})
    return Agent(**updated_agent)


@app.delete("/agents/{agent_id}")
def delete_agent(agent_id: str, token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    
    if user.get("permission") != "orgadmin":
        raise HTTPException(status_code=403, detail="Permission denied: Only organization admins can delete agents.")

    if not ObjectId.is_valid(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent ID format.")
    
    result = agents_db.delete_one({
        "_id": ObjectId(agent_id), 
        "org": ObjectId(user["organization"])
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found or you do not have permission to delete it.")
    
    return {"message": f"Agent '{agent_id}' deleted successfully."}