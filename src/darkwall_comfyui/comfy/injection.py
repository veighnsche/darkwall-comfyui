"""
Workflow injection utilities for ComfyUI.

TEAM_007: Extracted from client.py for better separation of concerns.

Handles injecting prompts, seeds, and other dynamic values into workflow JSON.
"""

import json
import logging
import re
from typing import Any

from ..exceptions import WorkflowError
from ..prompt_generator import PromptResult


logger = logging.getLogger(__name__)

# TEAM_007: Regex patterns for $$section$$ placeholder format
# Uses $$ to avoid conflict with __wildcard__ atom syntax
# Matches $$section_name$$ for positive prompts
# Matches $$section_name:negative$$ for negative prompts
_SECTION_PATTERN = re.compile(r'^\$\$([a-z0-9_]+)\$\$$')
_NEGATIVE_SECTION_PATTERN = re.compile(r'^\$\$([a-z0-9_]+):negative\$\$$')


def inject_prompt(workflow: dict[str, Any], prompt: str) -> dict[str, Any]:
    """
    Inject a simple string prompt into workflow nodes.
    
    Looks for common prompt field names: 'text', 'prompt', 'positive'.
    
    Args:
        workflow: ComfyUI workflow dict (API format)
        prompt: Text prompt to inject
        
    Returns:
        Modified workflow (deep copy)
    """
    workflow = json.loads(json.dumps(workflow))  # Deep copy
    
    injected = False
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        
        inputs = node.get('inputs', {})
        
        # Try common prompt field names
        for field in ['text', 'prompt', 'positive']:
            if field in inputs and isinstance(inputs[field], str):
                inputs[field] = prompt
                logger.debug(f"Injected prompt into node {node_id}.{field}")
                injected = True
                break
    
    if not injected:
        logger.warning("No prompt field found in workflow")
    
    return workflow


def inject_prompts(workflow: dict[str, Any], prompts: PromptResult) -> dict[str, Any]:
    """
    Inject prompts into workflow nodes using placeholders.
    
    TEAM_007: Uses $$section$$ syntax to avoid conflict with __wildcard__ atoms.
    
    Placeholder formats:
        $$section_name$$          -> prompts.prompts["section_name"]
        $$section_name:negative$$ -> prompts.negatives["section_name"]
    
    Args:
        workflow: ComfyUI workflow dict (API format)
        prompts: PromptResult with named sections
        
    Returns:
        Modified workflow (deep copy)
        
    Raises:
        WorkflowError: If no prompt placeholders found
    """
    workflow = json.loads(json.dumps(workflow))  # Deep copy
    
    injected: set[str] = set()
    missing_sections: set[str] = set()
    
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        
        inputs = node.get('inputs', {})
        
        for field, value in inputs.items():
            if not isinstance(value, str):
                continue
            
            # Check for negative section first: __name:negative__
            match = _NEGATIVE_SECTION_PATTERN.match(value)
            if match:
                section = match.group(1)
                if section in prompts.negatives:
                    inputs[field] = prompts.negatives[section]
                    logger.debug(f"Injected {section}:negative into node {node_id}.{field}")
                    injected.add(f"{section}:negative")
                else:
                    # For negatives, use empty string if missing (lenient mode)
                    inputs[field] = ""
                    logger.debug(f"No {section}:negative in template, using empty string")
                    missing_sections.add(f"{section}:negative")
                continue
            
            # Check for positive section: __name__
            match = _SECTION_PATTERN.match(value)
            if match:
                section = match.group(1)
                if section in prompts.prompts:
                    inputs[field] = prompts.prompts[section]
                    logger.debug(f"Injected {section} into node {node_id}.{field}")
                    injected.add(section)
                else:
                    missing_sections.add(section)
                continue
    
    # Validate: at least one prompt was injected
    prompt_injections = [i for i in injected if not i.endswith(':negative')]
    if not prompt_injections:
        raise WorkflowError(
            "Workflow missing prompt placeholders. "
            "Use $$section$$ placeholders (e.g., $$environment$$, $$subject$$). "
            "See docs/workflow-migration.md for migration guide."
        )
    
    # Log warnings for missing sections
    for missing in missing_sections:
        if not missing.endswith(':negative'):
            logger.warning(f"Workflow requests $${missing}$$ but template has no matching section")
    
    # Log summary
    logger.info(f"Injected prompts: {', '.join(sorted(injected))}")
    if missing_sections:
        logger.debug(f"Missing sections (used defaults): {', '.join(sorted(missing_sections))}")
    
    return workflow


def inject_seed(workflow: dict[str, Any], seed: int) -> dict[str, Any]:
    """
    Inject deterministic seed into Seed (rgthree) nodes if present.

    This keeps ComfyUI from treating "-1" as a special value and emitting
    warnings while still allowing workflows without Seed (rgthree) nodes to
    behave unchanged.
    
    Args:
        workflow: ComfyUI workflow dict (API format)
        seed: Seed value to inject
        
    Returns:
        Modified workflow (deep copy)
    """
    workflow = json.loads(json.dumps(workflow))  # Deep copy

    seed_injected = False
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue

        if node.get("class_type") == "Seed (rgthree)":
            inputs = node.setdefault("inputs", {})
            inputs["seed"] = int(seed)
            logger.debug(f"Injected seed {seed} into Seed (rgthree) node {node_id}")
            seed_injected = True

    if not seed_injected:
        logger.debug(
            "No Seed (rgthree) node found for seed injection; workflow may manage seeds internally"
        )

    return workflow
