import asyncio
import requests
import logging
from typing import Dict, Any, List
from datetime import datetime
import json
import os
import httpx
from googleapiclient.discovery import build
import google.generativeai as genai

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Import routes
from routes import websearch_router, configure_websearch_routes as configure_routes

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables and constants
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DEFAULT_CSE_ID = os.getenv("GOOGLE_CSE_ID")
DEFAULT_PORT = int(os.getenv("MY_PORT", 8003))
DEFAULT_SEARCH_COUNT = int(os.getenv("MY_DEFAULT_SEARCH_COUNT", 10))

# FastAPI app
app = FastAPI(
    title="FastAPI Web Search Server",
    description="A server providing only the web search functionality.",
    version="1.0.0"
)

# Configure routes with necessary environment variables
configure_routes(GOOGLE_API_KEY, DEFAULT_CSE_ID, DEFAULT_SEARCH_COUNT)

# Include the websearch router
app.include_router(websearch_router)


# Run the server
if __name__ == "__main__":
    import uvicorn    
    uvicorn.run("websearch_server:app", host="0.0.0.0", port=8003, reload=True)