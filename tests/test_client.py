"""Tests for the ComfyUI client."""

import json
import pytest
from unittest.mock import Mock, patch

from darkwall_comfyui.comfy.client import ComfyClient
from darkwall_comfyui.exceptions import (
    ComfyClientError,
    ComfyConnectionError,
    ComfyTimeoutError,
    ComfyGenerationError,
)
from darkwall_comfyui.prompt_generator import PromptResult


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
    
    # TEAM_007: Patch uuid in transport module where it's used
    with patch("darkwall_comfyui.comfy.transport.uuid.uuid4", return_value="test-123"), \
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


def test_build_ws_url_uses_ws_scheme_and_client_id(comfyui_config):
    """WebSocket URL should use ws scheme and include clientId query param."""
    comfyui_config.base_url = "http://localhost:8188"
    client = ComfyClient(comfyui_config)

    ws_url = client._build_ws_url()

    assert ws_url.startswith("ws://")
    assert "clientId=" in ws_url
    assert client.client_id in ws_url


def test_wait_for_result_uses_websocket_and_history(comfyui_config):
    """_wait_for_result should rely on WebSocket executing events and then history."""
    client = ComfyClient(comfyui_config)
    prompt_id = "prompt-123"

    # First message: executing a node, second: execution done (node=None for this prompt).
    msg_running = json.dumps({
        "type": "executing",
        "data": {"prompt_id": prompt_id, "node": "3"},
    })
    msg_done = json.dumps({
        "type": "executing",
        "data": {"prompt_id": prompt_id, "node": None},
    })

    ws_mock = Mock()
    ws_mock.recv.side_effect = [msg_running, msg_done]
    ws_mock.settimeout.return_value = None

    history = {
        "outputs": {
            "1": {
                "images": [
                    {"filename": "test.png", "subfolder": "sub", "type": "output"}
                ]
            }
        }
    }

    # TEAM_007: Patch websocket in transport module where it's used
    with patch("darkwall_comfyui.comfy.transport.websocket.create_connection", return_value=ws_mock), \
         patch.object(client._transport, "get_history", return_value=history):
        result = client._wait_for_result(prompt_id)

    assert result["filename"] == "test.png"
    assert result["subfolder"] == "sub"
    assert result["type"] == "output"
    ws_mock.close.assert_called_once()


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


# TEAM_007: Tests for multi-prompt placeholder injection

def test_inject_prompts_legacy_placeholders(comfyui_config):
    """Test legacy __positive__ and __positive:negative__ placeholders."""
    client = ComfyClient(comfyui_config)
    
    workflow = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "$$positive$$", "clip": ["2", 0]}
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "$$positive:negative$$", "clip": ["2", 0]}
        }
    }
    
    prompts = PromptResult.from_legacy(
        positive="beautiful landscape",
        negative="ugly, blurry"
    )
    
    result = client._inject_prompts(workflow, prompts)
    
    assert result["1"]["inputs"]["text"] == "beautiful landscape"
    assert result["2"]["inputs"]["text"] == "ugly, blurry"


def test_inject_prompts_new_format_single_section(comfyui_config):
    """Test new __name__ format with single section."""
    client = ComfyClient(comfyui_config)
    
    workflow = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "$$positive$$", "clip": ["2", 0]}
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "$$positive:negative$$", "clip": ["2", 0]}
        }
    }
    
    prompts = PromptResult(
        prompts={"positive": "beautiful landscape"},
        negatives={"positive": "ugly, blurry"}
    )
    
    result = client._inject_prompts(workflow, prompts)
    
    assert result["1"]["inputs"]["text"] == "beautiful landscape"
    assert result["2"]["inputs"]["text"] == "ugly, blurry"


def test_inject_prompts_multi_section(comfyui_config):
    """Test multi-section prompt injection (environment + subject)."""
    client = ComfyClient(comfyui_config)
    
    workflow = {
        "10": {
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "Environment Positive"},
            "inputs": {"text": "$$environment$$", "clip": ["4", 0]}
        },
        "11": {
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "Environment Negative"},
            "inputs": {"text": "$$environment:negative$$", "clip": ["4", 0]}
        },
        "20": {
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "Subject Positive"},
            "inputs": {"text": "$$subject$$", "clip": ["4", 0]}
        },
        "21": {
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "Subject Negative"},
            "inputs": {"text": "$$subject:negative$$", "clip": ["4", 0]}
        }
    }
    
    prompts = PromptResult(
        prompts={
            "environment": "mountain landscape, golden hour",
            "subject": "woman standing on right side"
        },
        negatives={
            "environment": "ugly, blurry",
            "subject": "bad anatomy, extra limbs"
        }
    )
    
    result = client._inject_prompts(workflow, prompts)
    
    assert result["10"]["inputs"]["text"] == "mountain landscape, golden hour"
    assert result["11"]["inputs"]["text"] == "ugly, blurry"
    assert result["20"]["inputs"]["text"] == "woman standing on right side"
    assert result["21"]["inputs"]["text"] == "bad anatomy, extra limbs"


def test_inject_prompts_missing_negative_uses_empty(comfyui_config):
    """Test that missing negative sections use empty string (lenient mode)."""
    client = ComfyClient(comfyui_config)
    
    workflow = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "$$environment$$", "clip": ["2", 0]}
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "$$environment:negative$$", "clip": ["2", 0]}
        }
    }
    
    # No negative provided
    prompts = PromptResult(
        prompts={"environment": "mountain landscape"},
        negatives={}
    )
    
    result = client._inject_prompts(workflow, prompts)
    
    assert result["1"]["inputs"]["text"] == "mountain landscape"
    assert result["2"]["inputs"]["text"] == ""  # Empty string for missing negative


def test_inject_prompts_no_placeholders_raises(comfyui_config):
    """Test that workflow without any placeholders raises error."""
    client = ComfyClient(comfyui_config)
    
    workflow = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "hardcoded prompt", "clip": ["2", 0]}
        }
    }
    
    prompts = PromptResult(
        prompts={"positive": "test"},
        negatives={}
    )
    
    # Use Exception to avoid module identity issues between installed/local package
    with pytest.raises(Exception) as exc_info:
        client._inject_prompts(workflow, prompts)
    
    assert "WorkflowError" in type(exc_info.value).__name__
    assert "missing prompt placeholders" in str(exc_info.value)


def test_inject_prompts_deep_copy(comfyui_config):
    """Test that injection creates a deep copy and doesn't modify original."""
    client = ComfyClient(comfyui_config)
    
    workflow = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "$$positive$$", "clip": ["2", 0]}
        }
    }
    
    prompts = PromptResult.from_legacy(positive="new prompt")
    
    result = client._inject_prompts(workflow, prompts)
    
    # Original should be unchanged
    assert workflow["1"]["inputs"]["text"] == "$$positive$$"
    # Result should have new value
    assert result["1"]["inputs"]["text"] == "new prompt"
