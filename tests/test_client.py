"""Tests for the ComfyUI client."""

import json
import pytest
from unittest.mock import Mock, patch

from darkwall_comfyui.comfy.client import ComfyClient, ComfyClientError, ComfyConnectionError
from darkwall_comfyui.comfy.client import ComfyTimeoutError, ComfyGenerationError


def test_client_initialization(test_config):
    """Test that ComfyClient initializes correctly."""
    client = ComfyClient(test_config)
    
    assert client.config == test_config
    assert client.base_url == test_config.comfyui.base_url.rstrip('/')
    assert client.timeout == test_config.comfyui.timeout
    assert client.poll_interval == test_config.comfyui.poll_interval
    assert hasattr(client, 'session')
    assert hasattr(client, 'logger')


def test_health_check_success(test_config):
    """Test successful health check."""
    client = ComfyClient(test_config)
    
    with patch.object(client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = client.health_check()
        
        assert result is True
        mock_get.assert_called_once_with(
            f"{client.base_url}/system_stats",
            timeout=5
        )


def test_health_check_failure_status(test_config):
    """Test health check with non-200 status."""
    client = ComfyClient(test_config)
    
    with patch.object(client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = client.health_check()
        
        assert result is False


def test_health_check_connection_error(test_config):
    """Test health check with connection error."""
    client = ComfyClient(test_config)
    
    with patch.object(client.session, 'get') as mock_get:
        mock_get.side_effect = ConnectionError("Connection failed")
        
        result = client.health_check()
        
        assert result is False


def test_prompt_injection(test_config):
    """Test prompt injection into workflow."""
    client = ComfyClient(test_config)
    
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


def test_prompt_injection_multiple_fields(test_config):
    """Test prompt injection finds multiple possible field names."""
    client = ComfyClient(test_config)
    
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


def test_prompt_injection_no_prompt_field(test_config):
    """Test prompt injection when no prompt field is found."""
    client = ComfyClient(test_config)
    
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


def test_submit_workflow_success(test_config):
    """Test successful workflow submission."""
    client = ComfyClient(test_config)
    
    workflow = {"1": {"class_type": "TestNode", "inputs": {}}}
    
    with patch.object(client.session, 'post') as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {"prompt_id": "test-123"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        prompt_id = client._submit(workflow)
        
        assert prompt_id == "test-123"
        mock_post.assert_called_once_with(
            f"{client.base_url}/prompt",
            json={"prompt": workflow},
            timeout=30
        )


def test_submit_workflow_no_prompt_id(test_config):
    """Test workflow submission when no prompt_id is returned."""
    client = ComfyClient(test_config)
    
    workflow = {"1": {"class_type": "TestNode", "inputs": {}}}
    
    with patch.object(client.session, 'post') as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        with pytest.raises(ComfyGenerationError, match="No prompt_id"):
            client._submit(workflow)


def test_submit_workflow_connection_error(test_config):
    """Test workflow submission with connection error."""
    client = ComfyClient(test_config)
    
    workflow = {"1": {"class_type": "TestNode", "inputs": {}}}
    
    with patch.object(client.session, 'post') as mock_post:
        mock_post.side_effect = ConnectionError("Connection failed")
        
        with pytest.raises(ComfyConnectionError):
            client._submit(workflow)


def test_get_history_success(test_config):
    """Test successful history retrieval."""
    client = ComfyClient(test_config)
    
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


def test_get_history_not_found(test_config):
    """Test history retrieval when prompt is not found."""
    client = ComfyClient(test_config)
    
    with patch.object(client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_get.return_value = mock_response
        
        history = client._get_history("test-123")
        
        assert history is None


def test_download_image_success(test_config):
    """Test successful image download."""
    client = ComfyClient(test_config)
    
    test_image_data = b"fake image data"
    
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


def test_download_image_empty_data(test_config):
    """Test image download with empty data."""
    client = ComfyClient(test_config)
    
    with patch.object(client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.content = b""
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with pytest.raises(ComfyClientError, match="Empty image data"):
            client._download_image("test.png")


def test_download_image_too_small(test_config):
    """Test image download with data that's too small."""
    client = ComfyClient(test_config)
    
    with patch.object(client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.content = b"x" * 50  # Less than 100 bytes
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with pytest.raises(ComfyClientError, match="Image data too small"):
            client._download_image("test.png")


def test_download_image_not_found(test_config):
    """Test image download when image is not found."""
    client = ComfyClient(test_config)
    
    with patch.object(client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_get.return_value = mock_response
        
        with pytest.raises(ComfyClientError, match="Image not found"):
            client._download_image("test.png")
