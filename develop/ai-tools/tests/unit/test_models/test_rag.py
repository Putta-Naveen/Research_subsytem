import pytest
from unittest.mock import patch, MagicMock

# Import the module to test
from backend.models.rag import SearchQuery, END_USER_ID

def test_search_query_model():
    """Test the SearchQuery model."""
    # Arrange & Act
    query = SearchQuery(query="What is RAG?")
    
    # Assert
    assert query.query == "What is RAG?"
    assert query.end_user_id is None or query.end_user_id == END_USER_ID


def test_search_query_with_custom_user():
    """Test the SearchQuery model with a custom user ID."""
    # Arrange & Act
    custom_user = "test-user-123"
    query = SearchQuery(query="What is RAG?", end_user_id=custom_user)
    
    # Assert
    assert query.query == "What is RAG?"
    assert query.end_user_id == custom_user


@patch("backend.models.rag.END_USER_ID", "default-test-user")
def test_search_query_with_default_user():
    """Test the SearchQuery model uses the default END_USER_ID."""
    # Arrange & Act
    query = SearchQuery(query="What is RAG?")
    
    # Assert
    assert query.query == "What is RAG?"
    assert query.end_user_id == "default-test-user"


# If the file is run directly, use pytest to run the tests
if __name__ == "__main__":
    # Import pytest and run the current file
    import pytest
    import sys
    sys.exit(pytest.main(["-v", __file__]))
