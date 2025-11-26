"""
Main entry point for the AI Tools.
This file orchestrates the different components of the system.
"""

import os
import argparse
import logging
import uvicorn
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Import components
from config import get_config
from api import create_app
from utils.web_utils import configure_utils
from utils.http_utils import configure_http
from utils.logging_utils import configure_app_logging
from workflows.graph import create_workflow_graph
from workflows.agents import configure_nodes

def main():
   
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="AI Tools Backend Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=9001, help="Port to bind the server to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    # Get configuration
    config = get_config()
    
    # Configure utility functions
    configure_utils(config["ALLOWED_DOMAINS"], config["UA_POOL"], config["gemini_model"])
    
    # Configure HTTP utilities
    configure_http(config["ALLOWED_DOMAINS"], config["UA_POOL"])
    
    # Configure logging
    loggers = configure_app_logging(
        app_name="AITools",
        log_level=config.get("LOG_LEVEL", logging.INFO),
        modules={
            "http": logging.INFO,
            "rag": logging.INFO,
            "websearch": logging.INFO
        }
    )
    
    # Configure workflow nodes
    configure_nodes(config)
    
    # Create workflow graph
    workflow_graph = create_workflow_graph()
    
    # Create FastAPI application
    app = create_app(workflow_graph, config)
    
    # Start the server
    print(f"Starting server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)

# Standard Python idiom for making the script executable
if __name__ == "__main__":
    main()
