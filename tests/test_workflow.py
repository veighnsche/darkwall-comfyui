"""Tests for the workflow manager."""

import json
import pytest
from pathlib import Path

from darkwall_comfyui.comfy.workflow import WorkflowManager, WorkflowError


def test_workflow_manager_initialization(comfyui_config):
    """Test that WorkflowManager initializes correctly."""
    mgr = WorkflowManager(comfyui_config)
    
    assert mgr.config == comfyui_config
    assert hasattr(mgr, 'logger')
    assert mgr._cached_workflow is None
    assert mgr._cached_path is None


def test_workflow_loading_success(comfyui_config, config_dir, test_workflow_json):
    """Test successful workflow loading."""
    mgr = WorkflowManager(comfyui_config)
    
    # Create a temporary workflow file
    workflow_file = config_dir / "test_workflow.json"
    workflow_file.write_text(test_workflow_json)
    
    # Update config to use test workflow
    comfyui_config.workflow_path = str(workflow_file)
    
    workflow = mgr.load()
    
    assert isinstance(workflow, dict)
    assert "1" in workflow
    assert "2" in workflow
    assert "3" in workflow
    
    # Check workflow structure
    assert workflow["1"]["class_type"] == "CLIPTextEncode"
    assert workflow["2"]["class_type"] == "CheckpointLoaderSimple"
    assert workflow["3"]["class_type"] == "SaveImage"


def test_workflow_loading_file_not_found(comfyui_config):
    """Test workflow loading when file doesn't exist."""
    mgr = WorkflowManager(comfyui_config)
    
    # Update config to non-existent file
    comfyui_config.workflow_path = "/nonexistent/workflow.json"
    
    with pytest.raises(WorkflowError, match="Workflow file not found"):
        mgr.load()


def test_workflow_loading_invalid_json(comfyui_config, config_dir):
    """Test workflow loading with invalid JSON."""
    mgr = WorkflowManager(comfyui_config)
    
    # Create invalid JSON file
    workflow_file = config_dir / "invalid.json"
    workflow_file.write_text("{ invalid json content")
    
    comfyui_config.workflow_path = str(workflow_file)
    
    with pytest.raises(WorkflowError, match="Invalid JSON"):
        mgr.load()


def test_workflow_loading_empty_file(comfyui_config, config_dir):
    """Test workflow loading with empty file."""
    mgr = WorkflowManager(comfyui_config)
    
    # Create empty file
    workflow_file = config_dir / "empty.json"
    workflow_file.write_text("")
    
    comfyui_config.workflow_path = str(workflow_file)
    
    with pytest.raises(WorkflowError, match="Workflow file is empty"):
        mgr.load()


def test_workflow_loading_not_a_dict(comfyui_config, config_dir):
    """Test workflow loading when JSON is not a dict."""
    mgr = WorkflowManager(comfyui_config)
    
    # Create file with array instead of object
    workflow_file = config_dir / "array.json"
    workflow_file.write_text('["not", "a", "dict"]')
    
    comfyui_config.workflow_path = str(workflow_file)
    
    with pytest.raises(WorkflowError, match="Workflow must be a JSON object"):
        mgr.load()


def test_workflow_validation(comfyui_config, config_dir, test_workflow_json):
    """Test workflow validation."""
    mgr = WorkflowManager(comfyui_config)
    
    # Create test workflow file
    workflow_file = config_dir / "test_workflow.json"
    workflow_file.write_text(test_workflow_json)
    
    comfyui_config.workflow_path = str(workflow_file)
    workflow = mgr.load()
    
    warnings = mgr.validate(workflow)
    
    assert isinstance(warnings, list)
    # Our test workflow should have prompt input and save image nodes
    # So it should have minimal warnings
    assert len(warnings) == 0


def test_workflow_validation_missing_prompt_node(comfyui_config):
    """Test workflow validation with missing prompt node."""
    mgr = WorkflowManager(comfyui_config)
    
    # Create workflow without prompt inputs
    workflow_no_prompt = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "test.safetensors"}
        },
        "2": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "test"}
        }
    }
    
    warnings = mgr.validate(workflow_no_prompt)
    
    assert isinstance(warnings, list)
    assert any("prompt" in warning.lower() for warning in warnings)


def test_workflow_validation_missing_output_node(comfyui_config):
    """Test workflow validation with missing output node."""
    mgr = WorkflowManager(comfyui_config)
    
    # Create workflow without save image nodes
    workflow_no_output = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "test", "clip": ["2", 0]}
        },
        "2": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "test.safetensors"}
        }
    }
    
    warnings = mgr.validate(workflow_no_output)
    
    assert isinstance(warnings, list)
    assert any("output" in warning.lower() for warning in warnings)


def test_workflow_caching(comfyui_config, config_dir, test_workflow_json):
    """Test that workflow loading uses caching."""
    mgr = WorkflowManager(comfyui_config)
    
    # Create test workflow file
    workflow_file = config_dir / "test_workflow.json"
    workflow_file.write_text(test_workflow_json)
    
    comfyui_config.workflow_path = str(workflow_file)
    
    # First load should populate cache
    workflow1 = mgr.load()
    assert mgr._cached_workflow is not None
    assert mgr._cached_path == workflow_file
    
    # Second load should use cache
    workflow2 = mgr.load()
    assert workflow1 is workflow2  # Same object due to caching


def test_workflow_cache_invalidation(comfyui_config, config_dir, test_workflow_json):
    """Test that cache is invalidated when loading different file."""
    mgr = WorkflowManager(comfyui_config)
    
    # Create test workflow file
    workflow_file = config_dir / "test_workflow.json"
    workflow_file.write_text(test_workflow_json)
    
    comfyui_config.workflow_path = str(workflow_file)
    
    # Load first workflow
    workflow1 = mgr.load()
    
    # Create a different workflow file
    workflow_file2 = config_dir / "test_workflow2.json"
    workflow_file2.write_text('{"1": {"class_type": "TestNode", "inputs": {}}}')
    
    # Load from different path - should get new content
    workflow2 = mgr.load(workflow_path=workflow_file2)
    assert workflow1 != workflow2
    assert workflow2["1"]["class_type"] == "TestNode"
