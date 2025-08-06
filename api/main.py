from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from dotenv import load_dotenv
from typing import List, Optional, Dict

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

load_dotenv()

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
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            operation["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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
            <div style="display: flex; justify-content: space-between; border: 1px solid #ccc; padding: 20px; margin: 20px; border-radius: 10px;background-color: #f9f9f9; text-align: center;">
                <form id="login-form" style="display: inline-block;">
                    <label for="login-username">Username:</label>
                    <input type="text" id="login-username" name="username" required></p>
                    <p><label for="login-password">Password:</label>
                    <input type="password" id="login-password" name="password" required></p>
                    <button type="submit">Sign In</button>
                </form>
            </div>

            <h1>Sign Up</h1>
            <div style="display: flex; justify-content: space-between; border: 1px solid #ccc; padding: 20px; margin: 20px; border-radius: 10px;background-color: #f9f9f9; text-align: center;">
                <form id="signup-form" style="display: inline-block;">
                    <p><label for="signup-username">Username:</label>
                    <input type="text" id="signup-username" name="username" required></p>
                    <p><label for="signup-password">Password:</label>
                    <input type="password" id="signup-password" name="password" required></p>
                    <button type="submit">Sign Up</button>
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
            });

            document.getElementById("signup-form").addEventListener("submit", async function(e) {
                e.preventDefault();
                const username = document.getElementById("signup-username").value;
                const password = document.getElementById("signup-password").value;
                const formData = new URLSearchParams();
                formData.append("username", username);
                formData.append("password", password);

                const response = await fetch("/signup", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        username: username,
                        password: password,
                        firstname: "",
                        lastname: "",
                        email: "",
                        phone: ""
                    })
                });

                const result = await response.json();
                document.getElementById("output").textContent = JSON.stringify(result, null, 2);
            });
            </script>
        </body>
    </html>
    """

# --- Authentication Routes ---
from api.auth import create_access_token, verify_token, users_db
import datetime

from pydantic import BaseModel

class SignupModel(BaseModel):
    username: str
    password: str
    firstname: str = ""
    lastname: str = ""
    email: str = ""
    phone: str = ""

@app.post("/signup")
@app.post("/signup")
def signup(form_data: SignupModel):
    if users_db.find_one({"username": form_data.username}):
        raise HTTPException(status_code=400, detail="User already exists")
    
    hashed_password = pwd_context.hash(form_data.password)

    result = users_db.insert_one({
        "username": form_data.username,
        "password": hashed_password,
        "firstname": form_data.firstname,
        "lastname": form_data.lastname,
        "email": form_data.email,
        "phone": form_data.phone,
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow(),
        "permission": "user"
    })

    if not result.acknowledged:
        raise HTTPException(status_code=500, detail="User creation failed")
    
    return {"message": "User created successfully", "_id": str(result.inserted_id)}

@app.post("/signin")
def signin(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.find_one({"username": form_data.username})
    if not user or not pwd_context.verify(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user["username"]})

    return {"access_token": access_token, "token_type": "bearer"}

# --- User Management Routes ---
@app.get("/users", response_model=List[dict])
def list_users(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    users = list(users_db.find({}, {"_id": 0, "password": 0}))
    return users

@app.get("/users/{username}")
def get_user(username: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "admin" or user["username"] != username:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    user_data = users_db.find_one({"username": username}, {"_id": 0, "password": 0})

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_data

@app.delete("/users/{username}")
def delete_user(username: str, token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated") 
    try:
        user = verify_token(token)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    
    if user.get("permission") != "admin" or user["username"] != username:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    result = users_db.delete_one({"username": username})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": f"User '{username}' deleted successfully"}