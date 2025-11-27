"""
ComfyUI workflow management.

Handles loading and validating workflow JSON files.
"""

import json
import logging
from pathlib import Path
from typing import Any


class WorkflowError(Exception):
    """Workflow loading or validation error."""
    pass


class WorkflowManager:
    """Manages ComfyUI workflow files."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._cached_workflow = None
        self._cached_path = None
    
    def load(self, workflow_path: Path = None) -> dict[str, Any]:
        """
        Load workflow from JSON file.
        
        Args:
            workflow_path: Path to workflow file (defaults to config)
            
        Returns:
            Parsed workflow dict
        """
        if workflow_path is None:
            workflow_path = Path(self.config.comfyui.workflow_path).expanduser()
        
        # Check cache
        if self._cached_path == workflow_path and self._cached_workflow:
            return self._cached_workflow
        
        if not workflow_path.exists():
            raise WorkflowError(f"Workflow file not found: {workflow_path}")
        
        try:
            with open(workflow_path, 'r') as f:
                workflow = json.load(f)
        except json.JSONDecodeError as e:
            raise WorkflowError(f"Invalid JSON in workflow: {e}")
        
        # Basic validation
        if not isinstance(workflow, dict):
            raise WorkflowError("Workflow must be a JSON object")
        
        if not workflow:
            raise WorkflowError("Workflow is empty")
        
        self._cached_workflow = workflow
        self._cached_path = workflow_path
        
        self.logger.debug(f"Loaded workflow from {workflow_path} ({len(workflow)} nodes)")
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
