import pytest
from unittest.mock import patch, MagicMock

# Import the module to test
from backend.utils.web_utils import configure_utils, get_headers, allowed_url

def test_configure_utils():
    """Test configure_utils function."""
    # Arrange
    allowed_domains = ["example.com", "test.org"]
    ua_pool = ["Mozilla/5.0", "Chrome/90.0"]
    gemini_model = "gemini-pro"
    
    # Act
    configure_utils(allowed_domains, ua_pool, gemini_model)
    
    # Assert

def test_get_headers():
    """Test get_headers function."""
    # Arrange
    ua_pool = ["UA1", "UA2", "UA3"]
    
    # Act
    with patch("backend.utils.web_utils.UA_POOL", ua_pool):
        # Call the function multiple times to ensure randomness works
        results = [get_headers()["User-Agent"] for _ in range(10)]
    
    # Assert
    for ua in results:
        assert ua in ua_pool
    
    
    assert len(set(results)) > 1, "Expected random selection from UA pool"


def test_allowed_url():
    """Test allowed_url function."""
    # Arrange
    allowed_domains = ["example.com", "test.org"]
    
    # Act & Assert
    with patch("utils.web_utils.ALLOWED_DOMAINS", allowed_domains):
        assert allowed_url("https://example.com/page") is True
        assert allowed_url("https://subdomain.example.com/page") is True
        assert allowed_url("https://test.org/api") is True
        assert allowed_url("https://malicious.com/page") is False
