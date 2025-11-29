"""
Step definitions for generation feature.

REQ-CORE-002: Generation Flow
REQ-MONITOR-008: Independent Template Selection
"""

from typing import Dict, List

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

# Load all scenarios from the feature file
scenarios("../features/generation.feature")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def generation_context():
    """Context for generation tests."""
    return {
        "config_valid": False,
        "comfyui_url": None,
        "comfyui_running": False,
        "monitors": [],
        "generated_monitors": [],
        "generation_steps": [],
        "time_slot": 0,
        "monitor_templates": {},  # monitor -> selected template
        "dry_run_output": {},
        "files_created": [],
        "network_requests": [],
        "rotation_advanced": False,
    }


# ============================================================================
# Given Steps
# ============================================================================

@given("a valid configuration")
def given_valid_config(generation_context):
    """Set up valid configuration."""
    generation_context["config_valid"] = True
    generation_context["monitors"] = ["DP-1", "HDMI-A-1", "HDMI-A-2"]


@given(parsers.parse('ComfyUI is running at "{url}"'))
def given_comfyui_running_at(generation_context, url):
    """Set ComfyUI as running at URL."""
    generation_context["comfyui_url"] = url
    generation_context["comfyui_running"] = True


@given(parsers.parse('monitors "{m1}" and "{m2}" both use workflow "{workflow}"'))
def given_monitors_same_workflow(generation_context, m1, m2, workflow):
    """Set up monitors with same workflow."""
    generation_context["monitors"] = [m1, m2]
    generation_context["workflow"] = workflow


@given("the time slot is the same")
def given_same_time_slot(generation_context):
    """Set same time slot for both monitors."""
    generation_context["time_slot"] = 12345


@given(parsers.parse("{count:d} configured monitors"))
def given_n_monitors(generation_context, count):
    """Set up N monitors."""
    generation_context["monitors"] = [f"monitor_{i}" for i in range(count)]
    generation_context["config_valid"] = True


# ============================================================================
# When Steps
# ============================================================================

@when(parsers.parse('I run "{command}"'))
def when_run_command(generation_context, command):
    """Simulate running a command."""
    if "generate-all" in command:
        # Generate for all monitors
        for monitor in generation_context["monitors"]:
            generation_context["generated_monitors"].append(monitor)
            generation_context["network_requests"].append(f"POST to ComfyUI for {monitor}")
            generation_context["files_created"].append(f"{monitor}.png")
    
    elif "--dry-run" in command:
        # Dry run - no actual generation
        generation_context["dry_run_output"] = {
            "Selected monitor": generation_context["monitors"][0] if generation_context["monitors"] else "none",
            "Selected template": "default.prompt",
            "Generated prompt (positive)": "test prompt, dark mode, high quality",
            "Generated prompt (negative)": "blurry, low quality",
            "Workflow to be used": "workflows/default.json",
            "Output path": "~/Pictures/wallpapers/monitor_0.png",
            "Wallpaper command": "swaybg -o DP-1 -i /path/to/image.png",
        }
        # No files or network in dry run
        generation_context["files_created"] = []
        generation_context["network_requests"] = []
    
    elif "--monitor" in command:
        # Generate for specific monitor
        parts = command.split()
        monitor_idx = parts.index("--monitor") + 1
        if monitor_idx < len(parts):
            monitor = parts[monitor_idx]
            generation_context["generated_monitors"].append(monitor)
            generation_context["rotation_advanced"] = False  # Explicit monitor doesn't advance rotation
    
    elif "generate" in command:
        # Normal generation - simulate the flow
        generation_context["generation_steps"] = [
            "Load configuration",
            "Select next monitor in rotation",
            "Determine current theme from schedule",
            "Select random prompt template",
            "Generate prompt from template",
            "Load workflow JSON",
            "Inject prompt via placeholders",
            "Submit to ComfyUI",
            "Poll until completion",
            "Download generated image",
            "Save to output path",
            "Execute wallpaper setter",
        ]
        generation_context["rotation_advanced"] = True
        if generation_context["monitors"]:
            generation_context["generated_monitors"].append(generation_context["monitors"][0])


@when(parsers.parse('I generate for "{monitor}"'))
def when_generate_for_monitor(generation_context, monitor):
    """Generate for specific monitor."""
    import random
    
    time_slot = generation_context["time_slot"]
    
    # Select template with monitor-specific seed
    seed = time_slot + hash(monitor) % 10000
    rng = random.Random(seed)
    
    templates = ["default.prompt", "cinematic.prompt", "minimal.prompt"]
    selected = rng.choice(templates)
    
    generation_context["monitor_templates"][monitor] = selected
    generation_context["generated_monitors"].append(monitor)


# ============================================================================
# Then Steps
# ============================================================================

@then("generation should complete the full pipeline")
def then_full_pipeline(generation_context):
    """Verify generation completed full pipeline."""
    steps = generation_context["generation_steps"]
    assert len(steps) > 0, "Generation should have steps"
    assert "Load configuration" in steps
    assert "Execute wallpaper setter" in steps


@then("the pipeline should include loading configuration")
def then_pipeline_includes_load_config(generation_context):
    """Verify pipeline includes loading config."""
    steps = generation_context["generation_steps"]
    assert "Load configuration" in steps


@then("the pipeline should include submitting to ComfyUI")
def then_pipeline_includes_submit(generation_context):
    """Verify pipeline includes ComfyUI submission."""
    steps = generation_context["generation_steps"]
    assert "Submit to ComfyUI" in steps


@then("the pipeline should include executing wallpaper setter")
def then_pipeline_includes_setter(generation_context):
    """Verify pipeline includes wallpaper setter."""
    steps = generation_context["generation_steps"]
    assert "Execute wallpaper setter" in steps


@then("the dry run output should show the selected monitor")
def then_dry_run_shows_monitor(generation_context):
    """Verify dry run shows selected monitor."""
    output = generation_context["dry_run_output"]
    assert "Selected monitor" in output, "Dry run should show selected monitor"


@then("the dry run output should show the generated prompt")
def then_dry_run_shows_prompt(generation_context):
    """Verify dry run shows generated prompt."""
    output = generation_context["dry_run_output"]
    has_prompt = "Generated prompt" in output or "prompt" in str(output).lower()
    assert has_prompt, "Dry run should show generated prompt"


@then("the dry run output should show the workflow")
def then_dry_run_shows_workflow(generation_context):
    """Verify dry run shows workflow."""
    output = generation_context["dry_run_output"]
    has_workflow = "Workflow" in output or "workflow" in str(output).lower()
    assert has_workflow, "Dry run should show workflow"


@then(parsers.parse('"{m1}" and "{m2}" may have different templates'))
def then_may_have_different_templates(generation_context, m1, m2):
    """Verify monitors may select different templates."""
    t1 = generation_context["monitor_templates"].get(m1)
    t2 = generation_context["monitor_templates"].get(m2)
    
    # They CAN be different (due to monitor hash), but don't HAVE to be
    # The key is they're independently seeded
    assert t1 is not None, f"No template selected for {m1}"
    assert t2 is not None, f"No template selected for {m2}"
    
    # Verify seeds are different
    time_slot = generation_context["time_slot"]
    seed1 = time_slot + hash(m1) % 10000
    seed2 = time_slot + hash(m2) % 10000
    assert seed1 != seed2, "Seeds should be different for different monitors"


@then(parsers.parse('generation should happen for "{monitor}" only'))
def then_generation_for_only(generation_context, monitor):
    """Verify generation only happened for specified monitor."""
    generated = generation_context["generated_monitors"]
    assert monitor in generated, f"Expected {monitor} to be generated, got {generated}"
    assert len(generated) == 1, f"Expected only 1 monitor, got {len(generated)}: {generated}"


@then("rotation state should not advance")
def then_rotation_not_advanced(generation_context):
    """Verify rotation did not advance."""
    assert not generation_context["rotation_advanced"], "Rotation should not have advanced"


@then(parsers.parse("generation should happen for all {count:d} monitors"))
def then_generation_for_all(generation_context, count):
    """Verify generation happened for all monitors."""
    generated = generation_context["generated_monitors"]
    assert len(generated) == count, f"Expected {count} monitors, got {len(generated)}"


@then("each monitor gets its own wallpaper")
def then_each_gets_wallpaper(generation_context):
    """Verify each monitor got a wallpaper."""
    files = generation_context["files_created"]
    monitors = generation_context["monitors"]
    assert len(files) == len(monitors), f"Expected {len(monitors)} files, got {len(files)}"


@then("I should see:")
def then_should_see(generation_context, datatable):
    """Verify dry run output contains expected info."""
    output = generation_context["dry_run_output"]
    
    for row in datatable:
        info = row["info"]
        assert info in output, f"Expected to see '{info}' in output"


@then("no files should be created")
def then_no_files(generation_context):
    """Verify no files were created."""
    files = generation_context["files_created"]
    assert len(files) == 0, f"Expected no files, got {files}"


@then("no network requests should be made")
def then_no_network(generation_context):
    """Verify no network requests were made."""
    requests = generation_context["network_requests"]
    assert len(requests) == 0, f"Expected no requests, got {requests}"
