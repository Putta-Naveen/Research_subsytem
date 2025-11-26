"""
Utility functions for the AI Tools backend.
"""

# Web utilities
from .web_utils import (
    sleep_backoff, 
    allowed_url, 
    get_headers, 
    is_probably_pdf, 
    dedupe_by_link, 
    get_concise_summary, 
    expand_and_summarize_web, 
    web_context, 
    rag_context
)

# HTTP utilities
from .http_utils import (
    configure_http,
    get_random_headers,
    is_allowed_url,
    fetch_url,
    fetch_url_async,
    post_json
)

# Logging utilities
from .logging_utils import (
    configure_logger,
    configure_app_logging,
    log_exception,
    RequestLogger
)

# Cache utilities
from .cache_utils import (
    MemoryCache,
    DiskCache,
    memoize
)

__all__ = [
    # Web utilities
    "sleep_backoff", 
    "allowed_url", 
    "get_headers", 
    "is_probably_pdf", 
    "dedupe_by_link", 
    "get_concise_summary", 
    "expand_and_summarize_web", 
    "web_context", 
    "rag_context",
    
    # HTTP utilities
    "configure_http",
    "get_random_headers",
    "is_allowed_url",
    "fetch_url",
    "fetch_url_async",
    "post_json",
    
    # Logging utilities
    "configure_logger",
    "configure_app_logging",
    "log_exception",
    "RequestLogger",
    
    # Cache utilities
    "MemoryCache",
    "DiskCache",
    "memoize"
]
