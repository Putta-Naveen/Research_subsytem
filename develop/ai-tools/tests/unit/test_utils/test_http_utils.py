import pytest
from unittest.mock import patch, MagicMock
import httpx

# Import the module to test
from backend.utils.http_utils import configure_http, fetch_url, is_allowed_url, get_random_headers

def test_configure_http():
    """Test configure_http function."""
    # Arrange
    allowed_domains = ["example.com", "test.org"]
    ua_pool = ["Mozilla/5.0", "Chrome/90.0"]
    
    # Act
    configure_http(allowed_domains, ua_pool)
    
    # Assert
@patch("utils.http_utils.httpx.get")
def test_fetch_url_success(mock_get):
    """Test fetch_url function with a successful response."""
    # Arrange
    url = "https://example.com/api"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}
    mock_get.return_value = mock_response
    
    # Act
    result = fetch_url(url)
    
    # Assert
    mock_get.assert_called_once()
    assert url in mock_get.call_args[0]  # Check URL was passed correctly
    assert result == mock_response  # Check response is returned


@patch("utils.http_utils.httpx.get")
def test_fetch_url_error(mock_get):
    """Test fetch_url function with an error response."""
    # Arrange
    url = "https://example.com/api"
    mock_get.side_effect = httpx.HTTPStatusError(
        "404 Not Found", 
        request=MagicMock(), 
        response=MagicMock(status_code=404, text="Not Found")
    )
    
    # Act
    result = fetch_url(url)
    
    # Assert
    mock_get.assert_called_once()
    assert result is None  


def test_is_allowed_url():
    """Test is_allowed_url function."""
    # Arrange
    with patch("utils.http_utils.ALLOWED_DOMAINS", ["example.com", "test.org"]):
        # Act & Assert
        assert is_allowed_url("https://example.com/page") is True
        assert is_allowed_url("https://subdomain.example.com/page") is True
        assert is_allowed_url("https://malicious.com/page") is False


def test_get_random_headers():
    """Test get_random_headers function."""
    # Arrange
    ua_pool = ["UA1", "UA2"]
    
    # Act
    with patch("backend.utils.http_utils.UA_POOL", ua_pool):
        headers = get_random_headers()
    
    # Assert
    assert "User-Agent" in headers
    assert headers["User-Agent"] in ua_pool
    assert "Accept" in headers
    assert "Accept-Language" in headers
