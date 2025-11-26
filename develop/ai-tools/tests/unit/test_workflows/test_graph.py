import pytest
from unittest.mock import patch, MagicMock

# Import the module to test
from backend.workflows.graph import create_workflow_graph


def test_create_workflow_graph():
    """Test the creation of the workflow graph."""
    # Act
    workflow_graph = create_workflow_graph()
    
    # Assert
    
    assert workflow_graph is not None
    assert hasattr(workflow_graph, "nodes")  


@patch("backend.workflows.agents.configure_nodes")
def test_workflow_execution(mock_configure_nodes):
    """Test the workflow graph execution."""
    # Arrange
    workflow_graph = create_workflow_graph()
    
    # Create a test input
    test_input = {"query": "What is AI?"}
    assert workflow_graph is not None
