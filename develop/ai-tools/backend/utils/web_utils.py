import time
import random
import logging
from queue import Queue
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse
from bs4 import BeautifulSoup

import google.generativeai as genai

# Get references to global variables from app module
from models import QueryState

# Configure logger
logger = logging.getLogger("WebUtils")

# Get environment variables
ALLOWED_DOMAINS = [] 
UA_POOL = []  
gemini_model = None  

# ------------------------ UTILITY FUNCTIONS ------------------------
def sleep_backoff() -> None:
    """Sleep for a fixed duration when rate limited."""
    time.sleep(45)

def allowed_url(url: str) -> bool:
    """
    Check if a URL is allowed.
    NOTE: Google CSE already filters results to configured domains,
    so this is now a simple passthrough.
    We keep this function for backward compatibility.
    """
    # Google CSE has already filtered results, so all URLs from CSE are allowed
    return True

def get_headers() -> Dict[str, str]:
    """Generate random headers for HTTP requests."""
    return {
        "User-Agent": random.choice(UA_POOL),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
    }

def is_probably_pdf(url: str, content_type: Optional[str]) -> bool:
    """Determine if a URL likely points to a PDF document."""
    if url.lower().endswith(".pdf"): return True
    if content_type and "pdf" in content_type.lower(): return True
    return False

def dedupe_by_link(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate a list of items based on their link/url."""
    seen, out = set(), []
    for r in items:
        k = (r.get("link") or r.get("url") or "").strip()
        if k and k not in seen:
            seen.add(k)
            out.append(r)
    return out

async def get_concise_summary(text: str) -> str:
    """Get a concise summary of text using Gemini API."""
    for attempt in range(3):
        try:
            prompt = f"Provide a very concise summary (max 50 words) of the following text:\n\n{(text or '')[:2000]}"
            logger.info(f"get_concise_summary prompt: {prompt}")
            resp = await gemini_model.generate_content_async(prompt)
            logger.info(f"get_concise_summary response: {resp}")
            return (resp.text or "").strip()
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                logger.warning("Rate limit in get_concise_summary; retry in 45s")
                sleep_backoff()
            else:
                logger.error(f"Gemini concise summarization error: {e}")
                logger.error(f"get_concise_summary input text: {text}")
                return "Summary not available due to API error."

def expand_and_summarize_web(link: Dict[str, Any], query: str, queue: Queue):
    """Expand a web search result by fetching the page and summarizing it."""
    try:
        # Use http_utils instead of direct httpx
        from utils.http_utils import fetch_url, is_allowed_url, is_probably_pdf
        
        url = link.get("link") or link.get("url") or ""
        if not url or not is_allowed_url(url):
            link["summary"] = "Filtered or invalid URL"
            queue.put(link); return

        title = link.get("title", link.get("displayLink", "Source"))
        snippet = link.get("snippet", "")
        page_text = ""

        try:
            resp = fetch_url(url, timeout=12)
            if resp is None:
                link["summary"] = "Failed to fetch page."
                link["title"] = title
                queue.put(link); return
                
            ctype = resp.headers.get("content-type", "")
            if is_probably_pdf(url, ctype):
                link["summary"] = "PDF detected; skipped parsing."
                link["title"] = title
                queue.put(link); return

            content = resp.content.decode("utf-8", errors="replace")
            soup = BeautifulSoup(content, "html.parser")
            for tag in soup(["script","style","form","ad","advertisement","noscript","iframe"]):
                tag.decompose()
            page_text = soup.get_text(separator=" ", strip=True)
            if not page_text or len(page_text) < 120:
                page_text = snippet or (soup.title.string if soup.title else "")
        except Exception as e:
            logger.warning(f"Fetch fail {url}: {e}")
            page_text = snippet

        prompt = (
            f"Question: {query}\n\n"
            f"Provide a concise summarization (max 50 words) of the following text:\n\n{(page_text or '')[:2000]}"
        )
        for attempt in range(3):
            try:
                summary = gemini_model.generate_content(prompt).text.strip()
                link["summary"] = summary
                link["title"] = title
                break
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    logger.warning("Rate limit in expand_and_summarize_web; retry 45s")
                    sleep_backoff()
                else:
                    logger.error(f"Gemini summarization error: {e}")
                    link["summary"] = f"Error: {e}"
                    break
    except Exception as e:
        logger.error(f"Error processing link: {e}")
        link["summary"] = f"Error: {e}"
    finally:
        queue.put(link)

def web_context(results: List[Dict[str, Any]]) -> str:
    """Format web search results as a string."""
    return "\n".join([f"[{r.get('n')}]\nTitle: {r.get('title','')}\nSummary: {r.get('summary','No summary')}" for r in results[:3]])

def rag_context(state: QueryState) -> str:
    """Format RAG response as a string."""
    return f"RAG Answer: {state.rag_answer[:500]}\nRAG Summary: {state.rag_summary}" if state.rag_answer else ""

def configure_utils(domain_list, user_agent_pool, gemini_model_instance):
    """Configure the utility module with global variables."""
    global ALLOWED_DOMAINS, UA_POOL, gemini_model
    ALLOWED_DOMAINS = domain_list
    UA_POOL = user_agent_pool
    gemini_model = gemini_model_instance
