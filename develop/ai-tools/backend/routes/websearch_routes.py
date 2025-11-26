from fastapi import APIRouter, HTTPException
from datetime import datetime
import logging

from models import StatusResponse, SearchRequest, SearchResult, SearchResponse
from googleapiclient.discovery import build

# Access logger created in main app
logger = logging.getLogger(__name__)

# Constants - these will be imported from the main file
GOOGLE_API_KEY = None
DEFAULT_CSE_ID = None
DEFAULT_SEARCH_COUNT = 10

# Create router instance
router = APIRouter()

@router.get("/", tags=["Root"])
async def root():
    """Root endpoint with basic information"""
    return {
        "message": "FastAPI Web Search Server",
        "swagger_ui": "/docs",
        "redoc": "/redoc",
        "available_endpoints": ["/mcp/Websearch"]
    }

@router.get("/status", response_model=StatusResponse, tags=["System"])
async def get_status():
    """Get server status and health information"""
    return StatusResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        services={
            "fastapi": "running",
            "swagger_ui": "available"
        }
    )

@router.post("/mcp/Websearch", response_model=SearchResponse, tags=["Web Search"])
async def mcp_websearch(request: SearchRequest):
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
    cse_id = request.cse_id if request.cse_id else DEFAULT_CSE_ID
    num_count = request.count if request.count else DEFAULT_SEARCH_COUNT

    try:
        logger.info(f"Starting Google Search for: {request.query}")
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)

        response = service.cse().list(
            q=request.query,
            cx=cse_id,
            num=num_count
        ).execute()

        logger.info("Search complete. Returning results.")

        results = []
        for item in response.get("items", []):
            results.append({
                "title": item["title"],
                "snippet": item.get("snippet", ""),
                "link": item["link"],
            })

        final_results = [SearchResult(**r) for r in results]
        return SearchResponse(results=final_results)

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

def configure_routes(api_key, cse_id, search_count):
    """Configure the routes with necessary environment variables"""
    global GOOGLE_API_KEY, DEFAULT_CSE_ID, DEFAULT_SEARCH_COUNT
    GOOGLE_API_KEY = api_key
    DEFAULT_CSE_ID = cse_id
    DEFAULT_SEARCH_COUNT = search_count
