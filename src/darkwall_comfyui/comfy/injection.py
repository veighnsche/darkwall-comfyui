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

# TEAM_007: Regex patterns for multi-prompt placeholder format
_PROMPT_PATTERN = re.compile(r'^__PROMPT:([a-z0-9_]+)__$')
_NEGATIVE_PATTERN = re.compile(r'^__NEGATIVE:([a-z0-9_]+)__$')


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
    
    TEAM_007: Supports arbitrary named sections.
    
    Placeholder formats:
        __PROMPT:section_name__   -> prompts.prompts["section_name"]
        __NEGATIVE:section_name__ -> prompts.negatives["section_name"]
        __POSITIVE_PROMPT__       -> prompts.prompts["positive"] (legacy)
        __NEGATIVE_PROMPT__       -> prompts.negatives["positive"] (legacy)
    
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
            
            # Check for new format: __PROMPT:name__
            match = _PROMPT_PATTERN.match(value)
            if match:
                section = match.group(1)
                if section in prompts.prompts:
                    inputs[field] = prompts.prompts[section]
                    logger.debug(f"Injected PROMPT:{section} into node {node_id}.{field}")
                    injected.add(f"PROMPT:{section}")
                else:
                    missing_sections.add(f"PROMPT:{section}")
                continue
            
            # Check for new format: __NEGATIVE:name__
            match = _NEGATIVE_PATTERN.match(value)
            if match:
                section = match.group(1)
                if section in prompts.negatives:
                    inputs[field] = prompts.negatives[section]
                    logger.debug(f"Injected NEGATIVE:{section} into node {node_id}.{field}")
                    injected.add(f"NEGATIVE:{section}")
                else:
                    # For negatives, use empty string if missing (lenient mode)
                    inputs[field] = ""
                    logger.debug(f"No NEGATIVE:{section} in template, using empty string")
                    missing_sections.add(f"NEGATIVE:{section}")
                continue
            
            # Legacy: __POSITIVE_PROMPT__ -> prompts["positive"]
            if value == "__POSITIVE_PROMPT__":
                inputs[field] = prompts.prompts.get("positive", "")
                logger.debug(f"Injected legacy positive prompt into node {node_id}.{field}")
                injected.add("PROMPT:positive")
                continue
            
            # Legacy: __NEGATIVE_PROMPT__ -> negatives["positive"]
            if value == "__NEGATIVE_PROMPT__":
                neg = prompts.negatives.get("positive", "")
                if neg:
                    inputs[field] = neg
                    logger.debug(f"Injected legacy negative prompt into node {node_id}.{field}")
                    injected.add("NEGATIVE:positive")
                continue
    
    # Validate: at least one prompt was injected
    prompt_injections = [i for i in injected if i.startswith("PROMPT:")]
    if not prompt_injections:
        raise WorkflowError(
            "Workflow missing prompt placeholders. "
            "Use __PROMPT:section__ or __POSITIVE_PROMPT__ placeholders. "
            "See docs/workflow-migration.md for migration guide."
        )
    
    # Log warnings for missing sections
    for missing in missing_sections:
        if missing.startswith("PROMPT:"):
            logger.warning(f"Workflow requests {missing} but template has no matching section")
    
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
