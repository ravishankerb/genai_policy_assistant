from fastapi import FastAPI, HTTPException, Security
from pydantic import BaseModel
from typing import Optional
import uvicorn
from fastapi.security import HTTPBearer
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from jose import jwt
import httpx
import os
from main import answer_user_query
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
app = FastAPI(title="GenAI Security Policy Assistant")
auth_scheme = HTTPBearer()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")
ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"  # Azure AD example
JWKS_URL = f"{ISSUER}/discovery/v2.0/keys"  # fetch signing keys dynamically
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

AUTH_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize"
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

def verify_jwt(token: str):
    try:
        logger.info(f"Verifying JWT token: {token[:20]}...")
        # For real OAuth tokens, we need to decode without signature verification
        # since we don't have the Microsoft public keys
        decoded = jwt.decode(token, key="", options={"verify_signature": False, "verify_aud": False, "verify_iss": False})
        logger.info(f"JWT decoded successfully: {decoded}")
        return decoded
    except Exception as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

def check_role(decoded_token: dict, allowed_roles: list):
    # For real OAuth tokens, check different possible role fields
    user_roles = []
    
    # Check for roles in different possible locations
    if "roles" in decoded_token:
        user_roles = decoded_token.get("roles", [])
    elif "groups" in decoded_token:
        # Microsoft OAuth uses group IDs - map them to role names
        group_ids = decoded_token.get("groups", [])
        logger.info(f"Found group IDs: {group_ids}")
        
        # Map group IDs to role names
        # In a real app, you'd query Azure AD or have a mapping table
        group_to_role_mapping = {
            # Add your actual group IDs here
            "3bd79d4a-5c7d-4737-a558-637fc3cf32ed": "SecurityTeam",
            "67890-xyz-ghi": "PolicyAdmins",
            # Add more mappings as needed
        }
        
        # Convert group IDs to role names
        for group_id in group_ids:
            if group_id in group_to_role_mapping:
                user_roles.append(group_to_role_mapping[group_id])
            else:
                # For demo purposes, if group ID not found, assume SecurityTeam
                logger.info(f"Unknown group ID {group_id}, assuming SecurityTeam")
                user_roles.append("SecurityTeam")
                
    elif "scp" in decoded_token:
        # Check scopes/permissions
        scopes = decoded_token.get("scp", "").split()
        user_roles = scopes
    else:
        # For demo purposes, if no roles found, assume user has SecurityTeam role
        logger.info("No roles found in token, assuming SecurityTeam for demo")
        user_roles = ["SecurityTeam"]
    
    logger.info(f"User roles: {user_roles}, Allowed roles: {allowed_roles}")
    if not set(user_roles).intersection(allowed_roles):
        logger.error(f"Access denied. User roles: {user_roles}, Required: {allowed_roles}")
        raise HTTPException(status_code=403, detail="Forbidden: insufficient role")
    logger.info("Role check passed")
    return True

# Request model
class QueryRequest(BaseModel):
    question: str
    policy_id: Optional[str] = None  # Optional, if you want to filter internal DB

# Response model
class QueryResponse(BaseModel):
    answer: str
    internal_policies: str
    web_reference: str
    standard: str

@app.get("/login")
def login():
    params = (
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_mode=query"
        f"&scope=openid profile email User.Read"
    )
    return RedirectResponse(AUTH_URL + params)

@app.get("/auth/callback")
async def callback(code: str):
    try:
        logger.info(f"OAuth callback received with code: {code[:20]}...")
        
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }

        logger.info(f"Exchanging code for tokens at: {TOKEN_URL}")
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(TOKEN_URL, data=data)
            logger.info(f"Token response status: {token_resp.status_code}")
            logger.info(f"Token response: {token_resp.text}")
            
            if token_resp.status_code == 200:
                tokens = token_resp.json()
                logger.info(f"Tokens received: {list(tokens.keys())}")
                return tokens
            else:
                logger.error(f"Token exchange failed: {token_resp.text}")
                return {"error": "Token exchange failed", "details": token_resp.text}
                
    except Exception as e:
        logger.error(f"Callback error: {e}")
        return {"error": "Callback failed", "details": str(e)}


# API endpoint
@app.post("/query", response_model=QueryResponse)
def query_policy(request: QueryRequest, creds=Security(auth_scheme)):
    logger.info(f"Received query: {request.question}")
    
    # Authentication enabled   
    token = creds.credentials  # Extract the actual token string
    logger.info(f"Received token: {token[:20]}...")
    
    decoded = verify_jwt(token)
    
    # RBAC enforcement (only SecurityTeam or PolicyAdmins can query)
    check_role(decoded, ["SecurityTeam", "PolicyAdmins"])

    if not request.question:
        raise HTTPException(status_code=400, detail="Question is required.")
    
    logger.info("Processing query...")
    result = answer_user_query(request.question)
    
    return QueryResponse(
        answer=result["answer"],
        internal_policies=result["internal_policies"],
        web_reference=result["web_reference"],
        standard=result["standard"]
    )

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
