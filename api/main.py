from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from passlib.context import CryptContext
from dotenv import load_dotenv, find_dotenv
from typing import List
from pydantic import BaseModel
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
    public_paths = {"/signin", "/signup", "/login", "/", "/invite/signup/{username}"}
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

# --- Home Page ---
@app.get("/", response_class=HTMLResponse)
async def main_page():
    return """
    <html>
        <head>
            <title>Organizational AI API</title>
            <meta charset="UTF-8" />
        </head>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; color: #333; padding: 20px;">
            <h1>Organizational AI</h1>
            <p>Gen-AI for Organizations. Streamline all workflows across messenger, workspaces and organizational system in one place, and make them smart using AI.</p>
            <h1>API Documentation</h1>
            <p>To access the API, <a href="/login">Login Here</a> and get an access token.</p>
            <p>To explore the API documentation, Visit <a href="/docs">Documentation</a></p>
            <h1>GitHub Repository</h1>
            <p>For source code and contributions, visit the <a href="https://github.com/BMDarkLight/Organizational-AI">GitHub repository</a>.</p>
        </body>
    </html>
    """

# --- Embedded Login Page ---
@app.get("/login", response_class=HTMLResponse)
def login():
    return """
    <html>
        <head>
            <title>Organizational AI API</title>
            <meta charset="UTF-8" />
        </head>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; color: #333; padding: 20px;">
            <h1>Login</h1>
            <div id="login" style="display: flex; justify-content: space-between; border: 1px solid #ccc; padding: 20px; margin: 20px; border-radius: 10px;background-color: #f9f9f9; text-align: center;">
                <form id="login-form" style="display: inline-block;">
                    <label for="login-username">Username:</label>
                    <input type="text" id="login-username" name="username" required></p>
                    <p><label for="login-password">Password:</label>
                    <input type="password" id="login-password" name="password" required></p>
                    <button type="submit">Sign In</button>
                </form>
            </div>

            <pre id="output"></pre>

            <script>
                document.getElementById("login-form").addEventListener("submit", async function(e) {
                    e.preventDefault();
                    const username = document.getElementById("login-username").value;
                    const password = document.getElementById("login-password").value;
                    const formData = new URLSearchParams();
                    formData.append("username", username);
                    formData.append("password", password);

                    const response = await fetch("/signin", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/x-www-form-urlencoded"
                        },
                        body: formData
                    });

                    const result = await response.json();
                    document.getElementById("output").textContent = JSON.stringify(result, null, 2);
                    document.getElementById("login").style.display = "none";
                });
            </script>
        </body>
    </html>
    """

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

@app.post("/signin")
def signin(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.find_one({"username": form_data.username})
    if not user or not pwd_context.verify(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.get("status") == "pending":
        raise HTTPException(status_code=403, detail="User is pending approval")
    
    access_token = create_access_token(data={"sub": user["username"]})

    return {"access_token": access_token, "token_type": "bearer"}

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
    
    result = prospective_users_db.delete_one({"username": username})
    if result.deleted_count == 0:
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
    user = users_db.find_one({"invite_code": form_data,invite_code})
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
