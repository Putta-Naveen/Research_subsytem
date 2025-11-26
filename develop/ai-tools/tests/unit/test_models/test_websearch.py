import pytest
from unittest.mock import patch, MagicMock

# Import the module to test
from backend.models.websearch import StatusResponse, SearchRequest, SearchResult, SearchResponse


def test_status_response():
    """Test the StatusResponse model."""
    # Arrange & Act
    status = StatusResponse(
        status="ok",
        timestamp="2025-09-08T12:00:00Z",
        version="1.0",
        services={"search": "active"}
    )
    
    # Assert
    assert status.status == "ok"
    assert status.timestamp == "2025-09-08T12:00:00Z"
    assert status.version == "1.0"
    assert status.services == {"search": "active"}


def test_search_request():
    """Test the SearchRequest model."""
    # Arrange & Act
    request = SearchRequest(query="test search", count=10)
    
    # Assert
    assert request.query == "test search"
    assert request.count == 10
    assert request.cse_id is None
    
    # Test with custom cse_id
    request_with_cse = SearchRequest(query="test search", count=5, cse_id="custom-cse")
    assert request_with_cse.cse_id == "custom-cse"


def test_search_result():
    """Test the SearchResult model."""
    # Arrange & Act
    result = SearchResult(
        title="Test Result",
        snippet="This is a test result",
        link="https://example.com/result"
    )
    
    # Assert
    assert result.title == "Test Result"
    assert result.snippet == "This is a test result"
    assert result.link == "https://example.com/result"


def test_search_response():
    """Test the SearchResponse model."""
    # Arrange & Act
    results = [
        SearchResult(
            title="Result 1",
            snippet="First result",
            link="https://example.com/1"
        ),
        SearchResult(
            title="Result 2",
            snippet="Second result",
            link="https://example.com/2"
        )
    ]
    response = SearchResponse(results=results)
    
    # Assert
    assert len(response.results) == 2
    assert response.results[0].title == "Result 1"
    assert response.results[1].link == "https://example.com/2"
