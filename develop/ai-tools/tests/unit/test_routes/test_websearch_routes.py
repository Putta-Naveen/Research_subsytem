import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Import the module to test
from backend.routes.websearch_routes import configure_routes


def test_search_endpoint(websearch_server_client, mock_requests_get):
    """Test the search endpoint."""
    # Arrange
    mock_search_results = {
        "results": [
            {
                "title": "Test Result 1",
                "link": "https://example.com/result1",
                "snippet": "This is the first result"
            },
            {
                "title": "Test Result 2", 
                "link": "https://example.com/result2",
                "snippet": "This is the second result"
            }
        ]
    }
    mock_requests_get.return_value.json.return_value = mock_search_results
    
    # Act
    response = websearch_server_client.get(
        "/search",
        params={"query": "test search", "count": 2}
    )
    
    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert "results" in response_data
    assert len(response_data["results"]) == 2
    assert response_data["results"][0]["title"] == "Test Result 1"


def test_search_endpoint_error(websearch_server_client, mock_requests_get):
    """Test the search endpoint with an error response."""
    # Arrange
    mock_requests_get.side_effect = Exception("API Error")
    
    # Act
    response = websearch_server_client.get(
        "/search",
        params={"query": "test search"}
    )
    
    # Assert
    assert response.status_code == 200
