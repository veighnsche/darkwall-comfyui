"""
ComfyUI workflow management.

Handles loading and validating workflow JSON files.
"""

import json
import logging
from pathlib import Path
from typing import Any

from ..config import Config, ComfyUIConfig
from ..exceptions import WorkflowError


class WorkflowManager:
    """Manages ComfyUI workflow files."""
    
    def __init__(self, comfyui_config: ComfyUIConfig) -> None:
        self.config = comfyui_config
        self.logger = logging.getLogger(__name__)
        self._cached_workflow: Optional[dict[str, Any]] = None
        self._cached_path: Optional[Path] = None
    
    def load(self, workflow_path: Path = None, config_dir: Path = None) -> dict[str, Any]:
        """
        Load workflow from JSON file.
        
        Args:
            workflow_path: Path to workflow file (defaults to config)
            config_dir: Config directory for resolving relative paths
            
        Returns:
            Parsed workflow dict
            
        Raises:
            WorkflowError: If loading fails
        """
        if workflow_path is None:
            workflow_path = Path(self.config.workflow_path).expanduser()
        
        # Resolve relative paths against config directory
        if not workflow_path.is_absolute():
            if config_dir is None:
                # Fallback to getting config directory from global config
                from ..config import Config
                config_dir = Config.get_config_dir()
            workflow_path = config_dir / workflow_path
        
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
        
        # Validate prompt placeholders
        self._validate_placeholders(workflow, workflow_path)
        
        # Cache the workflow
        self._cached_workflow = workflow
        self._cached_path = workflow_path
        
        self.logger.info(f"Loaded workflow from {workflow_path} ({len(workflow)} nodes)")
        return workflow
    
    def _validate_placeholders(self, workflow: dict[str, Any], workflow_path: Path) -> None:
        """Validate workflow contains proper prompt placeholders (REQUIRED)."""
        has_positive_placeholder = False
        has_negative_placeholder = False
        has_text_fields = False
        
        # Check for placeholders and text fields
        for node_id, node in workflow.items():
            if not isinstance(node, dict):
                continue
            
            inputs = node.get('inputs', {})
            for field, value in inputs.items():
                if isinstance(value, str):
                    has_text_fields = True
                    if value == "__POSITIVE_PROMPT__":
                        has_positive_placeholder = True
                    elif value == "__NEGATIVE_PROMPT__":
                        has_negative_placeholder = True
        
        # Provide validation feedback
        if not has_text_fields:
            self.logger.error(f"Workflow {workflow_path.name} has no text fields for prompt injection")
        
        if has_positive_placeholder:
            self.logger.info(f"Workflow {workflow_path.name} uses placeholder-based prompt injection")
            if has_negative_placeholder:
                self.logger.info(f"Workflow {workflow_path.name} supports negative prompts")
            else:
                self.logger.info(f"Workflow {workflow_path.name} doesn't support negative prompts (no __NEGATIVE_PROMPT__ placeholder)")
        else:
            self.logger.error(f"Workflow {workflow_path.name} doesn't use placeholder-based prompt injection")
            self.logger.error(f"Please update workflow to use __POSITIVE_PROMPT__ and __NEGATIVE_PROMPT__ placeholders")
            self.logger.error(f"See workflow migration guide for instructions")
    
    def validate(self, workflow_path: Path = None, config_dir: Path = None) -> list[str]:
        """
        Validate workflow file and return list of errors/warnings.
        
        Args:
            workflow_path: Path to workflow file
            config_dir: Config directory for resolving relative paths
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            workflow = self.load(workflow_path, config_dir)
            
            # Check for required placeholders
            has_positive_placeholder = False
            for node_id, node in workflow.items():
                if isinstance(node, dict):
                    inputs = node.get('inputs', {})
                    for field, value in inputs.items():
                        if isinstance(value, str) and value == "__POSITIVE_PROMPT__":
                            has_positive_placeholder = True
                            break
                    if has_positive_placeholder:
                        break
            
            if not has_positive_placeholder:
                errors.append("CRITICAL: Workflow missing __POSITIVE_PROMPT__ placeholder - prompt injection will fail")
                errors.append("Solution: Add __POSITIVE_PROMPT__ to a CLIPTextEncode node text field")
                errors.append("See workflow migration guide for detailed instructions")
            
        except WorkflowError as e:
            errors.append(f"Workflow validation failed: {e}")
        
        return errors
