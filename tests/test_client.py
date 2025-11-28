"""Tests for the ComfyUI client."""

import json
import pytest
from unittest.mock import Mock, patch

from darkwall_comfyui.comfy.client import ComfyClient, ComfyClientError, ComfyConnectionError
from darkwall_comfyui.comfy.client import ComfyTimeoutError, ComfyGenerationError


def test_client_initialization(comfyui_config):
    """Test that ComfyClient initializes correctly."""
    client = ComfyClient(comfyui_config)
    
    assert client.config == comfyui_config
    assert client.base_url == comfyui_config.base_url.rstrip('/')
    assert client.timeout == comfyui_config.timeout
    assert client.poll_interval == comfyui_config.poll_interval
    assert hasattr(client, 'session')
    assert hasattr(client, 'logger')


def test_health_check_success(comfyui_config):
    """Test successful health check."""
    client = ComfyClient(comfyui_config)
    
    with patch.object(client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = client.health_check()
        
        assert result is True
        mock_get.assert_called_once_with(
            f"{client.base_url}/system_stats",
            timeout=10
        )


def test_health_check_failure_status(comfyui_config):
    """Test health check with non-200 status."""
    client = ComfyClient(comfyui_config)
    
    with patch.object(client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = client.health_check()
        
        assert result is False


def test_health_check_connection_error(comfyui_config):
    """Test health check with connection error."""
    client = ComfyClient(comfyui_config)
    
    with patch.object(client.session, 'get') as mock_get:
        mock_get.side_effect = ConnectionError("Connection failed")
        
        result = client.health_check()
        
        assert result is False


def test_prompt_injection(comfyui_config):
    """Test prompt injection into workflow."""
    client = ComfyClient(comfyui_config)
    
    workflow = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "original prompt",
                "clip": ["2", 0]
            }
        },
        "2": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "test.safetensors"
            }
        }
    }
    
    new_workflow = client._inject_prompt(workflow, "new prompt")
    
    # Should be a deep copy
    assert new_workflow is not workflow
    assert new_workflow["1"] is not workflow["1"]
    
    # Prompt should be injected
    assert new_workflow["1"]["inputs"]["text"] == "new prompt"
    assert workflow["1"]["inputs"]["text"] == "original prompt"  # Original unchanged


def test_prompt_injection_multiple_fields(comfyui_config):
    """Test prompt injection into multiple text fields."""
    client = ComfyClient(comfyui_config)
    
    workflow = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "positive": "original prompt",
                "clip": ["2", 0]
            }
        }
    }
    
    new_workflow = client._inject_prompt(workflow, "new prompt")
    
    assert new_workflow["1"]["inputs"]["positive"] == "new prompt"


def test_prompt_injection_no_prompt_field(comfyui_config):
    """Test workflow with no prompt field."""
    client = ComfyClient(comfyui_config)
    
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "test.safetensors"
            }
        }
    }
    
    new_workflow = client._inject_prompt(workflow, "new prompt")
    
    # Should return unchanged workflow but log warning
    assert new_workflow == workflow


def test_submit_workflow_success(comfyui_config):
    """Test successful workflow submission."""
    client = ComfyClient(comfyui_config)
    
    workflow = {"1": {"class_type": "TestNode", "inputs": {}}}
    
    with patch("darkwall_comfyui.comfy.client.uuid.uuid4", return_value="test-123"), \
         patch.object(client.session, 'post') as mock_post:
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        prompt_id = client._submit(workflow)
        
        assert prompt_id == "test-123"
        mock_post.assert_called_once_with(
            f"{client.base_url}/prompt",
            json={
                "prompt": workflow,
                "client_id": client.client_id,
                "prompt_id": "test-123",
            },
            timeout=30,
        )


def test_submit_workflow_no_prompt_id(comfyui_config):
    """Test workflow submission with no prompt ID in response."""
    client = ComfyClient(comfyui_config)
    
    workflow = {"1": {"class_type": "TestNode", "inputs": {}}}
    
    with patch.object(client.session, 'post') as mock_post:
        import requests
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.status_code = 400
        mock_response.text = "No prompt_id in response"
        
        # Create a proper HTTPError with response
        http_error = requests.HTTPError("No prompt_id")
        http_error.response = mock_response
        mock_post.side_effect = http_error
        
        with pytest.raises(ComfyGenerationError, match="Invalid workflow"):
            client._submit(workflow)


def test_submit_workflow_connection_error(comfyui_config):
    """Test workflow submission with connection error."""
    client = ComfyClient(comfyui_config)
    
    workflow = {"1": {"class_type": "TestNode", "inputs": {}}}
    
    with patch.object(client.session, 'post') as mock_post:
        import requests
        mock_post.side_effect = requests.ConnectionError("Connection failed")
        
        with pytest.raises(ComfyConnectionError):
            client._submit(workflow)


def test_get_history_success(comfyui_config):
    """Test successful history retrieval."""
    client = ComfyClient(comfyui_config)
    
    with patch.object(client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = {
            "test-123": {
                "outputs": {
                    "1": {"images": [{"filename": "test.png"}]}
                }
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        history = client._get_history("test-123")
        
        assert history is not None
        assert "outputs" in history
        mock_get.assert_called_once_with(
            f"{client.base_url}/history/test-123",
            timeout=10
        )


def test_get_history_not_found(comfyui_config):
    """Test history retrieval with non-existent prompt."""
    client = ComfyClient(comfyui_config)
    
    with patch.object(client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_get.return_value = mock_response
        
        history = client._get_history("test-123")
        
        assert history is None


def test_download_image_success(comfyui_config):
    """Test successful image download."""
    client = ComfyClient(comfyui_config)
    
    test_image_data = b"x" * 150  # Make sure it's over 100 bytes
    
    with patch.object(client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.content = test_image_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        image_data = client._download_image("test.png")
        
        assert image_data == test_image_data
        mock_get.assert_called_once_with(
            f"{client.base_url}/view",
            params={"filename": "test.png", "subfolder": "", "type": "output"},
            timeout=60
        )


def test_download_image_empty_data(comfyui_config):
    """Test image download with empty data."""
    client = ComfyClient(comfyui_config)
    
    with patch.object(client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.content = b""
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with pytest.raises(ComfyClientError, match="Empty image data"):
            client._download_image("test.png")


def test_download_image_too_small(comfyui_config):
    """Test image download with data that's too small."""
    client = ComfyClient(comfyui_config)
    
    with patch.object(client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.content = b"x" * 50  # Less than 100 bytes
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with pytest.raises(ComfyClientError, match="Image data too small"):
            client._download_image("test.png")


def test_download_image_not_found(comfyui_config):
    """Test image download with 404 error."""
    client = ComfyClient(comfyui_config)
    
    with patch.object(client.session, 'get') as mock_get:
        import requests
        mock_response = Mock()
        mock_response.status_code = 404
        
        # Create a proper HTTPError with response
        http_error = requests.HTTPError("HTTP 404")
        http_error.response = mock_response
        mock_get.side_effect = http_error
        
        with pytest.raises(ComfyClientError, match="Image not found"):
            client._download_image("test.png")
