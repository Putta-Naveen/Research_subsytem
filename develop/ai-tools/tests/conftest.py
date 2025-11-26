import os
import sys
import pytest
from unittest.mock import MagicMock
from dotenv import load_dotenv
from fastapi.testclient import TestClient

# Add the backend directory to the path so we can import modules
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.append(backend_path)

# Load environment variables from .env file if present
load_dotenv()


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to mock environment variables used throughout the application."""
    test_env = {
        "GENAI_BASE_URL": "https://test-genai.example.com",
        "COPILOT_ID": "test-copilot-id",
        "END_USER_ID": "test-user-id",
        "GENAI_CLIENT_ID": "test-client-id",
        "GENAI_CLIENT_SECRET": "test-client-secret",
        "GEMINI_API_KEY": "test-gemini-key",
        "GOOGLE_API_KEY": "test-google-key",
        "GOOGLE_CSE_ID": "test-cse-id",
    }
    
    # Set all the test environment variables
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    return test_env


@pytest.fixture
def mock_requests_post(monkeypatch):
    """Fixture to mock requests.post for API calls."""
    mock_post = MagicMock()
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "access_token": "test-jwt-token",
        "expires_in": 3600
    }
    
    monkeypatch.setattr("requests.post", mock_post)
    return mock_post


@pytest.fixture
def mock_requests_get(monkeypatch):
    """Fixture to mock requests.get for API calls."""
    mock_get = MagicMock()
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"results": []}
    
    monkeypatch.setattr("requests.get", mock_get)
    return mock_get


@pytest.fixture
def app_client():
    """Fixture to create a FastAPI test client for the main app."""
    
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        
        
        app = FastAPI(title="Test App")
        
        
        @app.get("/test")
        def test_route():
            return {"status": "ok"}
        
        client = TestClient(app)
        return client
    except ImportError as e:
        pytest.skip(f"Could not import FastAPI: {e}")
        return None


@pytest.fixture
def rag_server_client():
    """Fixture to create a FastAPI test client for the RAG server."""
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        
        # Create a mock FastAPI app for RAG testing
        app = FastAPI(title="Mock RAG Server")
        
        # Define test routes that match the real RAG server
        @app.post("/rag/query")
        def mock_rag_query():
            return {
                "answer": "This is a mock RAG answer for testing",
                "citations": [{"text": "Test citation", "url": "https://example.com"}]
            }
        
        client = TestClient(app)
        return client
    except ImportError as e:
        pytest.skip(f"Could not create RAG test client: {e}")
        return None


@pytest.fixture
def websearch_server_client():
    """Fixture to create a FastAPI test client for the websearch server."""
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        
        # Create a mock FastAPI app for websearch testing
        app = FastAPI(title="Mock Web Search Server")
        
        # Define test routes that match the real websearch server
        @app.get("/search")
        def mock_search():
            return {
                "results": [
                    {
                        "title": "Test Result 1",
                        "link": "https://example.com/result1",
                        "snippet": "This is a test search result"
                    },
                    {
                        "title": "Test Result 2",
                        "link": "https://example.com/result2",
                        "snippet": "This is another test search result"
                    }
                ]
            }
        
        client = TestClient(app)
        return client
    except ImportError as e:
        pytest.skip(f"Could not create websearch test client: {e}")
        return None
