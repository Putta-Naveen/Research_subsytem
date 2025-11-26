"""
Configuration module for the AI Tools.
"""

import os
import warnings
import logging
import random
from typing import Dict, Any
import google.generativeai as genai
from bs4 import XMLParsedAsHTMLWarning

# Suppress unnecessary warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

def get_config() -> Dict[str, Any]:
    """
    Returns the configuration dictionary for the application.
    """
    # API Keys and URLs
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GENAI_RAG_URL = os.getenv("GENAI_RAG_URL")
    GENAI_RAG_TOKEN = os.getenv("GENAI_RAG_TOKEN")          
    MCP_SEARCH_URL = os.getenv("MCP_SEARCH_URL")
    END_USER_ID = os.getenv("END_USER_ID")
    
    # Google Custom Search Engine (CSE) - for automatic domain filtering
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

    # Algorithm parameters
    MIN_OVERALL = float(os.getenv("MIN_OVERALL", "0.7"))
    MAX_LOOPS = int(os.getenv("MAX_LOOPS", "3"))
    SUBQ_SEARCH_COUNT = int(os.getenv("SUBQ_SEARCH_COUNT", "3"))
    MAX_SOURCES_FOR_CITATIONS = int(os.getenv("MAX_SOURCES_FOR_CITATIONS", "10"))
    MAX_EVIDENCE_SNIPPETS = int(os.getenv("MAX_EVIDENCE_SNIPPETS", "5"))

    # Domain restrictions - Now handled by Google CSE
    # No need to maintain allowed_domains list here
    # Google CSE filters results automatically based on configured sites
    ALLOWED_DOMAINS = set()  # Empty - Google CSE does the filtering

    # User agent pool
    UA_POOL = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
    ]

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("Config")

    # Check for required keys
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set. Set it in env before running.")
    
    # Configure Gemini
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.5-flash-lite", generation_config={"temperature": 0.2})
    gemini_json = genai.GenerativeModel("gemini-2.5-flash-lite", generation_config={"temperature": 0.0, "response_mime_type": "application/json"})
    
    # Assemble and return the config
    return {
        # API Keys and URLs
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "GENAI_RAG_URL": GENAI_RAG_URL,
        "GENAI_RAG_TOKEN": GENAI_RAG_TOKEN,
        "MCP_SEARCH_URL": MCP_SEARCH_URL,
        "END_USER_ID": END_USER_ID,
        
        # Google Custom Search Engine (CSE) credentials
        "GOOGLE_API_KEY": GOOGLE_API_KEY,
        "GOOGLE_CSE_ID": GOOGLE_CSE_ID,
        
        # Algorithm parameters
        "MIN_OVERALL": MIN_OVERALL,
        "MAX_LOOPS": MAX_LOOPS,
        "SUBQ_SEARCH_COUNT": SUBQ_SEARCH_COUNT,
        "MAX_SOURCES_FOR_CITATIONS": MAX_SOURCES_FOR_CITATIONS,
        "MAX_EVIDENCE_SNIPPETS": MAX_EVIDENCE_SNIPPETS,
        
        # Domain restrictions - now empty (Google CSE handles filtering)
        "ALLOWED_DOMAINS": ALLOWED_DOMAINS,
        "UA_POOL": UA_POOL,
        
        # Models
        "gemini_model": gemini_model,
        "gemini_json": gemini_json,
        
        # Loggers
        "logger": logger
    }
