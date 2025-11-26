import pytest
from unittest.mock import patch, MagicMock
import sys

# Import the module to test
from backend.app import create_app, main


def test_create_app():
    """Test the create_app function."""
    # Arrange
    workflow_graph = MagicMock()
    config = {
        "ALLOWED_DOMAINS": ["example.com"],
        "UA_POOL": ["Mozilla/5.0"],
        "gemini_model": "gemini-pro",
        "LOG_LEVEL": "INFO"
    }
    
    # Act
    app = create_app(workflow_graph, config)
    
    # Assert
    assert app is not None
    # FastAPI app should have these attributes
    assert hasattr(app, "router")
    assert hasattr(app, "routes")


@patch("backend.app.uvicorn.run")
@patch("backend.app.argparse.ArgumentParser.parse_args")
@patch("backend.app.get_config")
@patch("backend.app.configure_utils")
@patch("backend.app.configure_http")
@patch("backend.app.configure_app_logging")
@patch("backend.app.configure_nodes")
@patch("backend.app.create_workflow_graph")
@patch("backend.app.create_app")
def test_main_function(
    mock_create_app, mock_create_workflow_graph, mock_configure_nodes,
    mock_configure_app_logging, mock_configure_http, mock_configure_utils,
    mock_get_config, mock_parse_args, mock_uvicorn_run
):
    """Test the main function."""
    # Arrange
    mock_args = MagicMock()
    mock_args.host = "0.0.0.0"
    mock_args.port = 9001
    mock_args.debug = False
    mock_parse_args.return_value = mock_args
    
    mock_config = {
        "ALLOWED_DOMAINS": ["example.com"],
        "UA_POOL": ["Mozilla/5.0"],
        "gemini_model": "gemini-pro",
        "LOG_LEVEL": "INFO"
    }
    mock_get_config.return_value = mock_config
    
    mock_workflow_graph = MagicMock()
    mock_create_workflow_graph.return_value = mock_workflow_graph
    
    mock_app = MagicMock()
    mock_create_app.return_value = mock_app
    
    original_argv = sys.argv
    sys.argv = ["app.py"]
    
    # Act
    try:
        main()
    finally:        
        sys.argv = original_argv
    
    # Assert
    mock_get_config.assert_called_once()
    mock_configure_utils.assert_called_once_with(
        mock_config["ALLOWED_DOMAINS"], 
        mock_config["UA_POOL"], 
        mock_config["gemini_model"]
    )
    mock_configure_http.assert_called_once_with(
        mock_config["ALLOWED_DOMAINS"], 
        mock_config["UA_POOL"]
    )
    mock_configure_app_logging.assert_called_once()
    mock_configure_nodes.assert_called_once_with(mock_config)
    mock_create_workflow_graph.assert_called_once()
    mock_create_app.assert_called_once_with(mock_workflow_graph, mock_config)
    mock_uvicorn_run.assert_called_once_with(mock_app, host=mock_args.host, port=mock_args.port)
