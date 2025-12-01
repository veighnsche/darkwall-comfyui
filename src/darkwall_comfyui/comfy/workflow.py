"""
ComfyUI workflow management.

Handles loading and validating workflow JSON files.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from ..config import Config, ComfyUIConfig
from ..exceptions import WorkflowError

# Regex patterns for $$section$$ placeholder format (same as injection.py)
# No anchors - matches placeholders anywhere in string
_SECTION_PATTERN = re.compile(r'\$\$([a-z0-9_]+)\$\$')
_NEGATIVE_SECTION_PATTERN = re.compile(r'\$\$([a-z0-9_]+):negative\$\$')


def _is_web_format(workflow: dict[str, Any]) -> bool:
    """Detect if workflow is in web/Litegraph format vs API format."""
    return 'nodes' in workflow and isinstance(workflow.get('nodes'), list)


def _iter_text_fields(workflow: dict[str, Any]):
    """Iterate over text fields in workflow, auto-detecting format.
    
    Yields: (node_id, value)
    """
    if _is_web_format(workflow):
        # Web format: nodes array with widgets_values
        for node in workflow.get('nodes', []):
            if not isinstance(node, dict):
                continue
            node_id = node.get('id', 'unknown')
            for value in node.get('widgets_values', []):
                if isinstance(value, str):
                    yield node_id, value
    else:
        # API format: node_id keys with inputs dict
        for node_id, node in workflow.items():
            if not isinstance(node, dict):
                continue
            for value in node.get('inputs', {}).values():
                if isinstance(value, str):
                    yield node_id, value


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
        """Validate workflow contains proper prompt placeholders (REQUIRED).
        
        TEAM_007: Updated to check for $$section$$ format instead of legacy __POSITIVE_PROMPT__.
        Supports both API format and web/Litegraph format workflows.
        """
        found_sections: set[str] = set()
        found_negatives: set[str] = set()
        has_text_fields = False
        
        is_web = _is_web_format(workflow)
        self.logger.debug(f"Workflow format: {'web/Litegraph' if is_web else 'API'}")
        
        # Check for placeholders and text fields using format-aware iterator
        for node_id, value in _iter_text_fields(workflow):
            has_text_fields = True
            
            # Find all $$section:negative$$ placeholders
            for match in _NEGATIVE_SECTION_PATTERN.finditer(value):
                found_negatives.add(match.group(1))
            
            # Find all $$section$$ placeholders
            for match in _SECTION_PATTERN.finditer(value):
                found_sections.add(match.group(1))
        
        # Provide validation feedback
        if not has_text_fields:
            self.logger.error(f"Workflow {workflow_path.name} has no text fields for prompt injection")
        
        if found_sections:
            self.logger.debug(f"Workflow {workflow_path.name} has section placeholders: {', '.join(sorted(found_sections))}")
            if found_negatives:
                self.logger.debug(f"Workflow {workflow_path.name} has negative placeholders: {', '.join(sorted(found_negatives))}")
        else:
            self.logger.error(f"Workflow {workflow_path.name} has no $$section$$ placeholders for prompt injection")
            self.logger.error(f"Please add $$environment$$, $$subject$$ etc. to CLIPTextEncode nodes")
            self.logger.error(f"See docs/workflow-migration.md for instructions")
    
    def validate(self, workflow_path: Path = None, config_dir: Path = None) -> list[str]:
        """
        Validate workflow file and return list of errors/warnings.
        
        TEAM_007: Updated to check for $$section$$ format.
        
        Args:
            workflow_path: Path to workflow file
            config_dir: Config directory for resolving relative paths
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            workflow = self.load(workflow_path, config_dir)
            
            # Check for required placeholders ($$section$$ format)
            found_sections: set[str] = set()
            for node_id, value in _iter_text_fields(workflow):
                for match in _SECTION_PATTERN.finditer(value):
                    found_sections.add(match.group(1))
            
            if not found_sections:
                errors.append("CRITICAL: Workflow missing $$section$$ placeholders - prompt injection will fail")
                errors.append("Solution: Add $$environment$$, $$subject$$ etc. to CLIPTextEncode node text fields")
                errors.append("See docs/workflow-migration.md for detailed instructions")
            
        except WorkflowError as e:
            errors.append(f"Workflow validation failed: {e}")
        
        return errors
