

import time
import random
import logging
from typing import Dict, Any, Optional, Union, List
from urllib.parse import urlparse

import httpx

# Configure logger
logger = logging.getLogger("HttpUtils")

# Default timeouts and retry settings
DEFAULT_TIMEOUT = 12  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds
MAX_BACKOFF = 45  # seconds

# User agent pool - will be populated from config
UA_POOL = []

# Allowed domains - will be populated from config
ALLOWED_DOMAINS = []

def configure_http(domain_list: List[str], user_agent_pool: List[str]):
    """Configure the HTTP utilities with domain restrictions and user agents."""
    global ALLOWED_DOMAINS, UA_POOL
    ALLOWED_DOMAINS = domain_list
    UA_POOL = user_agent_pool

def get_random_headers() -> Dict[str, str]:
    """Generate random headers for HTTP requests to avoid detection."""
    return {
        "User-Agent": random.choice(UA_POOL) if UA_POOL else "Python/3.12 HttpUtils/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
    }

def is_allowed_url(url: str) -> bool:
    """Check if a URL is allowed based on domain restrictions."""
    try:
        host = urlparse(url).netloc.lower()
        return any(host.endswith(d) for d in ALLOWED_DOMAINS) if ALLOWED_DOMAINS else True
    except Exception as e:
        logger.warning(f"URL parsing error ({url}): {e}")
        return False

def is_probably_pdf(url: str, content_type: Optional[str]) -> bool:
    """Determine if a URL likely points to a PDF document."""
    if url.lower().endswith(".pdf"): 
        return True
    if content_type and "pdf" in content_type.lower(): 
        return True
    return False

async def fetch_url_async(url: str, timeout: int = DEFAULT_TIMEOUT, max_retries: int = MAX_RETRIES) -> Optional[httpx.Response]:
    """
    Fetch a URL with retries and error handling using httpx async client.
    
    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        
    Returns:
        httpx.Response object or None if all attempts failed
    """
    if not is_allowed_url(url):
        logger.warning(f"URL not allowed: {url}")
        return None
        
    headers = get_random_headers()
    backoff = RETRY_BACKOFF
    
    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                response = await client.get(
                    url, 
                    headers=headers, 
                    timeout=timeout, 
                    follow_redirects=True
                )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Too many requests
                    wait_time = min(backoff * (2 ** attempt), MAX_BACKOFF)
                    logger.warning(f"Rate limited for {url}, backing off for {wait_time}s")
                    time.sleep(wait_time)
                elif e.response.status_code >= 500:  # Server errors
                    wait_time = min(backoff * (2 ** attempt), MAX_BACKOFF)
                    logger.warning(f"Server error {e.response.status_code} for {url}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    logger.error(f"HTTP error {e.response.status_code} for {url}: {e}")
                    return None
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                wait_time = min(backoff * (2 ** attempt), MAX_BACKOFF)
                logger.warning(f"Connection error for {url}, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                return None
                
        logger.error(f"All {max_retries} attempts failed for {url}")
        return None

def fetch_url(url: str, timeout: int = DEFAULT_TIMEOUT, max_retries: int = MAX_RETRIES) -> Optional[httpx.Response]:
    """
    Synchronous version of fetch_url_async.
    
    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        
    Returns:
        httpx.Response object or None if all attempts failed
    """
    if not is_allowed_url(url):
        logger.warning(f"URL not allowed: {url}")
        return None
        
    headers = get_random_headers()
    backoff = RETRY_BACKOFF
    
    for attempt in range(max_retries):
        try:
            response = httpx.get(
                url, 
                headers=headers, 
                timeout=timeout, 
                follow_redirects=True
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Too many requests
                wait_time = min(backoff * (2 ** attempt), MAX_BACKOFF)
                logger.warning(f"Rate limited for {url}, backing off for {wait_time}s")
                time.sleep(wait_time)
            elif e.response.status_code >= 500:  # Server errors
                wait_time = min(backoff * (2 ** attempt), MAX_BACKOFF)
                logger.warning(f"Server error {e.response.status_code} for {url}, retrying in {wait_time}s")
                time.sleep(wait_time)
            else:
                logger.error(f"HTTP error {e.response.status_code} for {url}: {e}")
                return None
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            wait_time = min(backoff * (2 ** attempt), MAX_BACKOFF)
            logger.warning(f"Connection error for {url}, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None
            
    logger.error(f"All {max_retries} attempts failed for {url}")
    return None

def post_json(url: str, json_data: Dict[str, Any], headers: Optional[Dict[str, str]] = None, 
              timeout: int = DEFAULT_TIMEOUT, max_retries: int = MAX_RETRIES) -> Optional[httpx.Response]:
    """
    Post JSON data to a URL with retries and error handling.
    
    Args:
        url: The URL to post to
        json_data: The JSON data to post
        headers: Optional headers to include (will be merged with default headers)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        
    Returns:
        httpx.Response object or None if all attempts failed
    """
    # Merge headers with defaults, prioritizing passed headers
    request_headers = get_random_headers()
    request_headers.update({"Content-Type": "application/json"})
    if headers:
        request_headers.update(headers)
        
    backoff = RETRY_BACKOFF
    
    for attempt in range(max_retries):
        try:
            response = httpx.post(
                url, 
                json=json_data, 
                headers=request_headers, 
                timeout=timeout,
                follow_redirects=True
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Too many requests
                wait_time = min(backoff * (2 ** attempt), MAX_BACKOFF)
                logger.warning(f"Rate limited for POST to {url}, backing off for {wait_time}s")
                time.sleep(wait_time)
            elif e.response.status_code >= 500:  # Server errors
                wait_time = min(backoff * (2 ** attempt), MAX_BACKOFF)
                logger.warning(f"Server error {e.response.status_code} for POST to {url}, retrying in {wait_time}s")
                time.sleep(wait_time)
            else:
                logger.error(f"HTTP error {e.response.status_code} for POST to {url}: {e}")
                return None
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            wait_time = min(backoff * (2 ** attempt), MAX_BACKOFF)
            logger.warning(f"Connection error for POST to {url}, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)
        except Exception as e:
            logger.error(f"Unexpected error posting to {url}: {e}")
            return None
            
    logger.error(f"All {max_retries} POST attempts failed for {url}")
    return None
