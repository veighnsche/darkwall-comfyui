"""
ComfyUI workflow management.

Handles loading and validating workflow JSON files.
"""

import json
import logging
from pathlib import Path
from typing import Any

from ..config import Config


class WorkflowError(Exception):
    """Workflow loading or validation error."""
    pass


class WorkflowManager:
    """Manages ComfyUI workflow files."""
    
    def __init__(self, config: Config) -> None:
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._cached_workflow: Optional[dict[str, Any]] = None
        self._cached_path: Optional[Path] = None
    
    def load(self, workflow_path: Path = None) -> dict[str, Any]:
        """
        Load workflow from JSON file.
        
        Args:
            workflow_path: Path to workflow file (defaults to config)
            
        Returns:
            Parsed workflow dict
            
        Raises:
            WorkflowError: If loading fails
        """
        if workflow_path is None:
            workflow_path = Path(self.config.comfyui.workflow_path).expanduser()
        
        # Resolve relative paths against config directory
        if not workflow_path.is_absolute():
            workflow_path = self.config.get_config_dir() / workflow_path
        
        # Check cache
        if self._cached_path == workflow_path and self._cached_workflow:
            self.logger.debug(f"Using cached workflow: {workflow_path}")
            return self._cached_workflow
        
        self.logger.debug(f"Loading workflow from: {workflow_path}")
        
        # Validate file path
        if not workflow_path.exists():
            raise WorkflowError(f"Workflow file not found: {workflow_path}")
        
        if not workflow_path.is_file():
            raise WorkflowError(f"Workflow path is not a file: {workflow_path}")
        
        # Check file size
        try:
            file_size = workflow_path.stat().st_size
            if file_size == 0:
                raise WorkflowError(f"Workflow file is empty: {workflow_path}")
            
            if file_size > 10 * 1024 * 1024:  # 10MB sanity check
                raise WorkflowError(f"Workflow file too large: {workflow_path} ({file_size} bytes)")
                
        except OSError as e:
            raise WorkflowError(f"Cannot access workflow file: {workflow_path}: {e}")
        
        # Load and parse JSON
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
        except json.JSONDecodeError as e:
            raise WorkflowError(f"Invalid JSON in workflow file {workflow_path}: {e}")
        except UnicodeDecodeError as e:
            raise WorkflowError(f"Invalid encoding in workflow file {workflow_path}: {e}")
        except OSError as e:
            raise WorkflowError(f"Failed to read workflow file {workflow_path}: {e}")
        
        # Validate workflow structure
        if not isinstance(workflow, dict):
            raise WorkflowError(f"Workflow must be a JSON object, got {type(workflow).__name__}")
        
        if not workflow:
            raise WorkflowError("Workflow is empty")
        
        # Cache the workflow
        self._cached_workflow = workflow
        self._cached_path = workflow_path
        
        self.logger.info(f"Loaded workflow from {workflow_path} ({len(workflow)} nodes)")
        return workflow
    
    def validate(self, workflow: dict[str, Any]) -> list[str]:
        """
        Validate workflow structure.
        
        Returns:
            List of warning messages (empty if valid)
        """
        warnings = []
        
        has_prompt_node = False
        has_output_node = False
        
        for node_id, node in workflow.items():
            if not isinstance(node, dict):
                continue
            
            class_type = node.get('class_type', '')
            inputs = node.get('inputs', {})
            
            # Check for prompt input nodes
            if 'text' in inputs or 'prompt' in inputs or 'positive' in inputs:
                has_prompt_node = True
            
            # Check for output nodes
            if 'SaveImage' in class_type or 'PreviewImage' in class_type:
                has_output_node = True
        
        if not has_prompt_node:
            warnings.append("No text/prompt input node found - prompt injection may fail")
        
        if not has_output_node:
            warnings.append("No SaveImage/PreviewImage node found - may not produce output")
        
        return warnings
