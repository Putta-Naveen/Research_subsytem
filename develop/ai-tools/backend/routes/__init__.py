"""
Initialize the routes package
"""

# Export the websearch router
from .websearch_routes import router as websearch_router
from .websearch_routes import configure_routes as configure_websearch_routes

# Export the RAG router
from .rag_routes import router as rag_router
from .rag_routes import configure_routes as configure_rag_routes
