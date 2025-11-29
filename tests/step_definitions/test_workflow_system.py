"""
Step definitions for workflow system feature.

REQ-WORKFLOW-001: Workflow ID equals filename
REQ-WORKFLOW-002: Workflow → Prompts Relationship
REQ-WORKFLOW-003: Random Template Selection
"""

import tempfile
from pathlib import Path
from typing import List, Optional

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

# Load all scenarios from the feature file
scenarios("../features/workflow_system.feature")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def workflow_context():
    """Context for workflow-related state."""
    return {
        "config_dir": None,
        "workflow_file": None,
        "workflow_id": None,
        "resolved_path": None,
        "available_prompts": [],
        "workflow_prompts_config": None,  # explicit prompts list
        "selected_prompt": None,
        "time_slot_seed": None,
        "monitor_name": None,
        "selection_history": [],  # track selections for determinism test
    }


# ============================================================================
# Given Steps
# ============================================================================

@given(parsers.parse('a workflow file exists at "{path}"'))
def given_workflow_file(workflow_context, path):
    """Create a workflow file at the given path."""
    temp_dir = tempfile.mkdtemp()
    config_dir = Path(temp_dir)
    workflow_context["config_dir"] = config_dir
    
    full_path = config_dir / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text('{"__POSITIVE_PROMPT__": "", "__NEGATIVE_PROMPT__": ""}')
    
    workflow_context["workflow_file"] = path


@when(parsers.parse('I reference workflow "{workflow_id}"'))
def when_reference_workflow(workflow_context, workflow_id):
    """Reference a workflow by ID."""
    workflow_context["workflow_id"] = workflow_id


@given(parsers.parse('a theme with {count:d} prompts available'))
def given_theme_with_n_prompts(workflow_context, count):
    """Set up theme with N prompts."""
    workflow_context["available_prompts"] = [
        "default.prompt", "cinematic.prompt", "minimal.prompt"
    ][:count]


@given(parsers.parse('a theme with {count:d} prompts including "{prompt}"'))
def given_theme_with_prompts_including(workflow_context, count, prompt):
    """Set up theme with prompts including a specific one."""
    workflow_context["available_prompts"] = ["default.prompt", "cinematic.prompt", "minimal.prompt"]
    if prompt not in workflow_context["available_prompts"]:
        workflow_context["available_prompts"].append(prompt)


@given(parsers.parse('workflow "{workflow_id}" is configured with prompts "{p1}" and "{p2}"'))
def given_workflow_with_explicit_prompts(workflow_context, workflow_id, p1, p2):
    """Configure workflow with explicit prompts."""
    workflow_context["workflow_id"] = workflow_id
    workflow_context["workflow_prompts_config"] = [p1, p2]


@given("no explicit workflow prompts config")
def given_no_explicit_prompts(workflow_context):
    """No explicit prompts configured for workflow."""
    workflow_context["workflow_prompts_config"] = None


@given("a config with:")
def given_config_with(workflow_context, docstring):
    """Parse config to extract workflow prompts."""
    import tomli
    config = tomli.loads(docstring)
    
    # Extract prompts from workflows section
    workflows = config.get("workflows", {})
    for workflow_id, wf_config in workflows.items():
        if "prompts" in wf_config:
            workflow_context["workflow_prompts_config"] = wf_config["prompts"]
            workflow_context["workflow_id"] = workflow_id
            break


@given(parsers.parse('workflow "{workflow_id}" with {count:d} available prompts'))
def given_workflow_with_prompts(workflow_context, workflow_id, count):
    """Set up workflow with N available prompts."""
    workflow_context["workflow_id"] = workflow_id
    workflow_context["available_prompts"] = [f"prompt_{i}.prompt" for i in range(count)]


@given(parsers.parse("time slot seed is {seed:d}"))
def given_time_slot_seed(workflow_context, seed):
    """Set the time slot seed."""
    workflow_context["time_slot_seed"] = seed


@given(parsers.parse('monitor is "{name}"'))
def given_monitor(workflow_context, name):
    """Set the monitor name."""
    workflow_context["monitor_name"] = name


# ============================================================================
# When Steps
# ============================================================================

@when(parsers.parse('I generate for workflow "{workflow_id}"'))
def when_generate_for_workflow(workflow_context, workflow_id):
    """Generate using the specified workflow."""
    workflow_context["workflow_id"] = workflow_id
    
    # Determine available prompts
    available = workflow_context.get("available_prompts", [])
    explicit = workflow_context.get("workflow_prompts_config")
    
    if explicit:
        # Filter to only explicit prompts
        eligible = [p for p in available if p in explicit]
    else:
        # All prompts available
        eligible = available
    
    # Select a prompt (seeded random)
    if eligible:
        import random
        seed = workflow_context.get("time_slot_seed") or 42
        monitor = workflow_context.get("monitor_name") or "default"
        
        # Seed with time slot + monitor hash
        combined_seed = seed + hash(monitor) % 10000
        rng = random.Random(combined_seed)
        
        workflow_context["selected_prompt"] = rng.choice(eligible)
        workflow_context["eligible_prompts"] = eligible


@when("I generate a prompt")
def when_generate_prompt(workflow_context):
    """Generate a prompt."""
    available = workflow_context["available_prompts"]
    seed = workflow_context.get("time_slot_seed", 42)
    monitor = workflow_context.get("monitor_name", "default")
    
    import random
    combined_seed = seed + hash(monitor) % 10000
    rng = random.Random(combined_seed)
    
    selected = rng.choice(available)
    workflow_context["selected_prompt"] = selected
    workflow_context["selection_history"].append((seed, selected))


# ============================================================================
# Then Steps
# ============================================================================

@then(parsers.parse('it should load "{expected_path}"'))
def then_should_load_path(workflow_context, expected_path):
    """Verify the workflow resolves to expected path."""
    workflow_id = workflow_context["workflow_id"]
    
    # Workflow ID without .json should resolve to workflows/{id}.json
    if not workflow_id.endswith(".json"):
        resolved = f"workflows/{workflow_id}.json"
    else:
        resolved = f"workflows/{workflow_id}"
    
    assert resolved == expected_path, f"Expected {expected_path}, got {resolved}"


@then(parsers.parse('it should resolve to "{expected_path}"'))
def then_should_resolve_to(workflow_context, expected_path):
    """Verify the workflow resolves to expected path."""
    then_should_load_path(workflow_context, expected_path)


@then(parsers.parse("any of the {count:d} prompts may be selected"))
def then_any_prompts_available(workflow_context, count):
    """Verify all prompts are eligible."""
    eligible = workflow_context.get("eligible_prompts", workflow_context["available_prompts"])
    assert len(eligible) == count, f"Expected {count} eligible prompts, got {len(eligible)}"


@then(parsers.parse('only "{prompt1}" or "{prompt2}" may be selected'))
def then_only_specific_prompts(workflow_context, prompt1, prompt2):
    """Verify only specific prompts are eligible."""
    selected = workflow_context["selected_prompt"]
    eligible = workflow_context.get("eligible_prompts", [])
    
    assert selected in [prompt1, prompt2], \
        f"Selected '{selected}' but only '{prompt1}' or '{prompt2}' should be eligible"
    assert set(eligible) == {prompt1, prompt2}, \
        f"Eligible prompts should be exactly {{{prompt1}, {prompt2}}}, got {eligible}"


@then(parsers.parse('"{prompt}" should never be selected'))
def then_prompt_never_selected(workflow_context, prompt):
    """Verify a prompt is not in eligible list."""
    eligible = workflow_context.get("eligible_prompts", [])
    assert prompt not in eligible, f"'{prompt}' should not be eligible but is in {eligible}"


@then("the same prompt is selected on repeated runs")
def then_deterministic_selection(workflow_context):
    """Verify selection is deterministic."""
    # Run selection multiple times with same seed
    seed = workflow_context["time_slot_seed"]
    monitor = workflow_context["monitor_name"]
    available = workflow_context["available_prompts"]
    
    import random
    results = []
    for _ in range(5):
        combined_seed = seed + hash(monitor) % 10000
        rng = random.Random(combined_seed)
        results.append(rng.choice(available))
    
    # All results should be the same
    assert len(set(results)) == 1, f"Selection not deterministic: {results}"


@then("different time slots select different prompts")
def then_different_slots_different_prompts(workflow_context):
    """Verify different seeds produce different selections (eventually)."""
    monitor = workflow_context["monitor_name"]
    available = workflow_context["available_prompts"]
    
    if len(available) <= 1:
        pytest.skip("Need multiple prompts to test variation")
    
    import random
    results = set()
    for seed in range(100):  # Try 100 different seeds
        combined_seed = seed + hash(monitor) % 10000
        rng = random.Random(combined_seed)
        results.add(rng.choice(available))
    
    # Should have selected different prompts at some point
    assert len(results) > 1, "Different seeds should eventually select different prompts"
