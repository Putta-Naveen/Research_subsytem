from fastapi import APIRouter, HTTPException, Depends
import logging
import requests
import time
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
from typing import Callable, Dict, Any, Optional

# Import models
from models import SearchQuery

# Create router instance
router = APIRouter()

# Logger
logger = logging.getLogger(__name__)

# These will be set by the main application through the configure_routes function
GENAI_BASE_URL = None
COPILOT_ID = None
JWT_TOKEN = None
fetch_jwt_token = None  # Function to fetch a new token when needed

# Use MemoryCache instead of a simple dictionary
from utils import MemoryCache
rag_answer_cache = MemoryCache(ttl=3600)  # Cache RAG answers for 1 hour

@router.post("/searchrag", summary="Search using GenAI RAG", tags=["GenAI RAG"])
async def search_mcp_tool(search_data: SearchQuery):
    """
    Performs a search query using the GenAI Copilot service.
    Returns only the available structured fields from the response.
    """
    global JWT_TOKEN
    
    # Using the query string as the cache key
    cache_key = search_data.query.strip()
    cached_result = rag_answer_cache.get(cache_key)
    if cached_result is not None:
        logger.info("Returning cached RAG answer for query.")
        return cached_result

    current_token = JWT_TOKEN
    if not current_token or current_token == "PLACEHOLDER_INVALID_TOKEN":
        logger.error("Attempted /search with missing or placeholder JWT_TOKEN.")
        raise HTTPException(status_code=401, detail="Authentication token (JWT_TOKEN) is missing or invalid. Please configure it.")

    url = f"{GENAI_BASE_URL}/copilots/{COPILOT_ID}/preview"
    headers = {
        "Authorization": f"Bearer {current_token}"
    }
    payload = {
        "query": (None, search_data.query),
        "end_user_id": (None, search_data.end_user_id)
    }

    logger.info(f"Sending search to {url} with query: {search_data.query}")

    try:
        start_time = time.time()
        # Helper function to call RAG API with a given token
        def call_rag_api(token):
            hdrs = {"Authorization": f"Bearer {token}"}
            logger.info(f"[TIMING] About to call RAG API at {time.time()-start_time:.2f}s")
            response = requests.post(url, headers=hdrs, files=payload, timeout=60)
            logger.info(f"[TIMING] RAG API response received at {time.time()-start_time:.2f}s, status: {response.status_code}")
            return response

        response = call_rag_api(current_token)
        logger.info(f"[TIMING] After first call at {time.time()-start_time:.2f}s")
        
        if response.status_code == 401 and fetch_jwt_token:
            logger.warning(f"[TIMING] JWT token expired at {time.time()-start_time:.2f}s, refreshing...")
            # Use the token refresh function from the main app
            try:
                logger.info(f"[TIMING] Starting token refresh at {time.time()-start_time:.2f}s")
                JWT_TOKEN = fetch_jwt_token()
                logger.info(f"[TIMING] Token refresh completed at {time.time()-start_time:.2f}s")
                current_token = JWT_TOKEN
                if not current_token:
                    logger.error("Failed to refresh JWT token")
                    raise HTTPException(status_code=401, detail="Token refresh failed")
                response = call_rag_api(current_token)
                logger.info(f"[TIMING] After retry at {time.time()-start_time:.2f}s")
            except Exception as e:
                logger.error(f"Token refresh error: {e}")
                raise HTTPException(status_code=401, detail=f"Token refresh failed: {e}")
        
        logger.info(f"[TIMING] About to raise_for_status at {time.time()-start_time:.2f}s")
        response.raise_for_status()
        logger.info(f"[TIMING] After raise_for_status at {time.time()-start_time:.2f}s")

        full_response = response.json()
        logger.info(f"[TIMING] Response parsed at {time.time()-start_time:.2f}s, response keys: {list(full_response.keys())}")
        logger.info("Search response received")

        keys_to_include = {
            "output_text": "output_text",
            "relevance_scores": "output_relevance_scores",
            "source_files": "output_file_names",
            "grounded_qa": "output_groundings",
            "suggested_followups": "output_next_questions"
        }

        safe_output = {}
        for friendly_key, actual_genai_key in keys_to_include.items():
            if actual_genai_key in full_response:
                safe_output[friendly_key] = full_response[actual_genai_key]
            elif "executions" in full_response and full_response["executions"]:
                first_execution = full_response["executions"][0]
                if actual_genai_key in first_execution:
                    safe_output[friendly_key] = first_execution[actual_genai_key]

        if not safe_output or (len(safe_output) == 1 and "output_text" in safe_output):
            logger.warning("Only output_text or no expected structured keys found. Returning raw response for inspection.")
            rag_answer_cache.put(cache_key, full_response)
            return full_response

        # Cache the answer for future requests
        rag_answer_cache.put(cache_key, safe_output)

        return safe_output

    except HTTPError as e:
        error_detail = f"GenAI API Error: {e.response.status_code} - {e.response.text}"
        logger.error(f"HTTPError: {error_detail}")
        raise HTTPException(status_code=e.response.status_code, detail=error_detail)

    except ConnectionError as e:
        logger.error(f"ConnectionError: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to GenAI Copilot search service: {e}")
        
    except Timeout as e:
        logger.error(f"Timeout: {e}")
        raise HTTPException(status_code=504, detail=f"GenAI Copilot search service timed out: {e}")
        
    except RequestException as e:
        logger.error(f"RequestException: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected request error occurred during search: {e}")
        
    except Exception as e:
        logger.exception("Unexpected error during search:")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

def configure_routes(base_url: str, copilot_id: str, 
                    token: str, token_fetch_func: Callable, 
                    cache: Optional[Any] = None):
    """
    Configure the routes with necessary variables from the main application
    """
    global GENAI_BASE_URL, COPILOT_ID, JWT_TOKEN, fetch_jwt_token, rag_answer_cache
    
    GENAI_BASE_URL = base_url
    COPILOT_ID = copilot_id
    JWT_TOKEN = token
    fetch_jwt_token = token_fetch_func
    
    if cache is not None:
        rag_answer_cache = cache
