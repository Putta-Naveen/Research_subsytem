import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def test_rag_query_endpoint(rag_server_client, mock_requests_post):
    """Test the RAG query endpoint."""
    # Arrange
    mock_response = {
        "answer": "This is the RAG answer",
        "citations": [{"text": "Source", "url": "http://example.com"}]
    }
    mock_requests_post.return_value.json.return_value = mock_response
    
    # Act
    response = rag_server_client.post(
        "/rag/query",
        json={"query": "What is RAG?", "context": ["RAG is a technique that combines a large language model (LLM) with an external information retrieval system to improve the accuracy and relevance of generated text"]}
    )
    
    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert "answer" in response_data
    assert "mock RAG answer" in response_data["answer"]
    assert "citations" in response_data
    assert len(response_data["citations"]) == 1
def test_rag_query_endpoint_error(rag_server_client, mock_requests_post):
    """Test the RAG query endpoint with an error response."""
    # Arrange
    mock_requests_post.side_effect = Exception("API Error")
    
    # Act
    response = rag_server_client.post(
        "/rag/query",
        json={"query": "What is RAG?", "context": ["RAG is a technique in NLP"]}
    )
    
    # Assert
    assert response.status_code == 200
