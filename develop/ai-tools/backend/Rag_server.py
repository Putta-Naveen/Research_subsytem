from fastapi import FastAPI
import requests, os, logging
from datetime import datetime
from dotenv import load_dotenv 
load_dotenv()

# Import models and routes
from models import SearchQuery
from routes import rag_router, configure_rag_routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RAG setup (Ensure these environment variables are set or provided)
GENAI_BASE_URL = os.getenv("GENAI_BASE_URL")
COPILOT_ID = os.getenv("COPILOT_ID")
END_USER_ID = os.getenv("END_USER_ID")

# Credentials for JWT token fetch
CLIENT_ID = os.getenv("GENAI_CLIENT_ID")
CLIENT_SECRET = os.getenv("GENAI_CLIENT_SECRET")


from utils import MemoryCache
rag_answer_cache = MemoryCache(ttl=3600)  # Cache entries expire after 1 hour

def fetch_jwt_token():
    """
    Fetch JWT token from GenAI API using client_id and client_secret.
    """
    token_url = f"{GENAI_BASE_URL}/client/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post(token_url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        token_data = resp.json()
        token = token_data.get("access_token")
        if not token:
            logger.error(f"Token response did not contain 'access_token': {token_data}")
            return None
        return token
    except Exception as e:
        logger.error(f"Failed to fetch JWT token: {e}")
        return None

# Fetch and set JWT_TOKEN at startup
JWT_TOKEN = fetch_jwt_token()

# Update the module in models/rag.py with our END_USER_ID
import models.rag
models.rag.END_USER_ID = END_USER_ID

# FastAPI app Creation
app = FastAPI(title="GenAI RAG Server")

# Configure the rag routes with necessary variables
configure_rag_routes(
    base_url=GENAI_BASE_URL, 
    copilot_id=COPILOT_ID, 
    token=JWT_TOKEN,
    token_fetch_func=fetch_jwt_token,
    cache=rag_answer_cache
)

# Include the rag router
app.include_router(rag_router)

# Routes are now in routes/rag_routes.py
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("Rag_server:app", host="0.0.0.0", port=8001, reload=True)