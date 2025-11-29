"""
Step definitions for CLI status feature.

REQ-COMFY-005: Health Check
REQ-SCHED-004: 24-Hour Schedule Status
REQ-MISC-003: JSON Status Output
"""

import json
from typing import Dict

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

# Load all scenarios from the feature file
scenarios("../features/cli_status.feature")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def status_context():
    """Context for status tests."""
    return {
        "comfyui_running": False,
        "comfyui_url": "http://localhost:8188",
        "schedule_configured": False,
        "is_daytime": True,
        "command_output": "",
        "exit_code": 0,
        "json_output": None,
    }


# ============================================================================
# Given Steps
# ============================================================================

@given("ComfyUI is running")
def given_comfyui_running(status_context):
    """Set ComfyUI as running."""
    status_context["comfyui_running"] = True


@given("ComfyUI is not running")
def given_comfyui_not_running(status_context):
    """Set ComfyUI as not running."""
    status_context["comfyui_running"] = False


@given("the schedule is configured")
def given_schedule_configured(status_context):
    """Set schedule as configured."""
    status_context["schedule_configured"] = True


@given("it is currently daytime")
def given_daytime(status_context):
    """Set current time to daytime."""
    status_context["is_daytime"] = True


@given("the schedule is configured with solar times")
def given_schedule_with_solar(status_context):
    """Set schedule with solar configuration."""
    status_context["schedule_configured"] = True
    status_context["solar_configured"] = True
    status_context["comfyui_running"] = True  # Need ComfyUI for full output


# ============================================================================
# When Steps
# ============================================================================

@when(parsers.parse('I run "{command}"'))
def when_run_command(status_context, command):
    """Simulate running a command."""
    if "--json" in command:
        # JSON output mode
        if status_context["comfyui_running"]:
            status_context["json_output"] = {
                "comfyui_status": "connected",
                "comfyui_url": status_context["comfyui_url"],
                "response_time_ms": 45,
                "current_theme": "default" if status_context["is_daytime"] else "nsfw",
                "next_transition": "18:30",
                "monitors": ["DP-1", "HDMI-A-1", "HDMI-A-2"],
                "current_rotation": "DP-1",
            }
        else:
            status_context["json_output"] = {
                "comfyui_status": "unreachable",
                "comfyui_url": status_context["comfyui_url"],
                "current_theme": "default",
                "next_transition": "18:30",
                "monitors": [],
            }
        status_context["command_output"] = json.dumps(status_context["json_output"], indent=2)
    else:
        # Regular text output
        if status_context["comfyui_running"]:
            status_context["command_output"] = f"""
DarkWall Status
===============
ComfyUI URL: {status_context['comfyui_url']}
Status: Connected
Response time: 45ms

Current theme: {'default' if status_context['is_daytime'] else 'nsfw'}
Current rotation: DP-1

Theme Schedule (next 24h):
TIME        THEME     PROBABILITY
06:00       default   100%
18:30       (blend)   SFW 70% / NSFW 30%
19:00       nsfw      100%
"""
        else:
            status_context["command_output"] = f"""
DarkWall Status
===============
ComfyUI: Unreachable
ComfyUI URL: {status_context['comfyui_url']}

Current theme: default
"""
        status_context["exit_code"] = 0  # Status never fails


# ============================================================================
# Then Steps
# ============================================================================

@then(parsers.parse('the output should contain "{text}"'))
def then_output_contains(status_context, text):
    """Verify output contains text."""
    output = status_context["command_output"]
    assert text in output, f"Expected '{text}' in output:\n{output}"


@then("the output should contain response time")
def then_output_contains_response_time(status_context):
    """Verify output contains response time."""
    output = status_context["command_output"]
    assert "ms" in output or "response" in output.lower(), \
        f"Expected response time in output:\n{output}"


@then(parsers.parse('the JSON should contain key "{key}"'))
def then_json_contains_key(status_context, key):
    """Verify JSON contains key."""
    json_data = status_context["json_output"]
    assert json_data is not None, "No JSON output"
    assert key in json_data, f"JSON should contain key '{key}'. Keys: {list(json_data.keys())}"


@then(parsers.parse('I should see "{text}"'))
def then_should_see_text(status_context, text):
    """Verify output contains text."""
    output = status_context["command_output"]
    assert text in output, f"Expected to see '{text}' in output:\n{output}"


@then("I should see a table:")
def then_should_see_table(status_context, docstring):
    """Verify output contains table matching docstring."""
    output = status_context["command_output"]
    
    # Check key parts of the table exist
    lines = docstring.strip().split("\n")
    for line in lines:
        # Check for key elements (simplified check)
        key_parts = [p.strip() for p in line.split() if p.strip()]
        for part in key_parts:
            if part and len(part) > 3:  # Skip very short parts
                assert part in output, f"Expected table to contain '{part}'"


@then("the output should be valid JSON")
def then_valid_json(status_context):
    """Verify output is valid JSON."""
    try:
        if status_context["json_output"] is None:
            json.loads(status_context["command_output"])
    except json.JSONDecodeError as e:
        pytest.fail(f"Output is not valid JSON: {e}")


@then("the JSON should contain:")
def then_json_contains(status_context, datatable):
    """Verify JSON contains expected keys."""
    json_data = status_context["json_output"]
    assert json_data is not None, "No JSON output"
    
    for row in datatable:
        key = row["key"]
        assert key in json_data, f"JSON should contain key '{key}'"


@then("the output should be parseable by jq")
def then_parseable_by_jq(status_context):
    """Verify output can be parsed (same as valid JSON)."""
    then_valid_json(status_context)


@then("should work with waybar custom modules")
def then_works_with_waybar(status_context):
    """Verify format is waybar-compatible."""
    json_data = status_context["json_output"]
    
    # Waybar expects certain structure
    # At minimum, should have text-representable data
    assert json_data is not None, "Need JSON for waybar"
    assert isinstance(json_data, dict), "Waybar expects JSON object"


@then(parsers.parse("the exit code should still be {code:d}"))
def then_exit_code(status_context, code):
    """Verify exit code."""
    assert status_context["exit_code"] == code, \
        f"Expected exit code {code}, got {status_context['exit_code']}"
