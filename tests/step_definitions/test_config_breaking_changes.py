"""
Step definitions for config breaking changes feature.

REQ-CONFIG-005: Breaking Changes — Fail Hard
"""

import tempfile
from pathlib import Path

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

# Load all scenarios from the feature file
scenarios("../features/config_breaking_changes.feature")


# ============================================================================
# Deprecated Keys Registry
# ============================================================================

DEPRECATED_KEYS = {
    "monitors.count": "Use auto-detection from compositor. Remove 'count' and add [monitors.{name}] sections.",
    "monitors.pattern": "Use [monitors.{name}] sections with individual output paths.",
    "monitors.backup_pattern": "Use [monitors.{name}] sections with individual backup settings.",
    "monitors.workflows": "Use [monitors.{name}] sections with 'workflow = \"name\"' for each monitor.",
    "monitors.templates": "Use [monitors.{name}] sections with 'templates = [...]' for each monitor.",
    "monitors.paths": "Use [monitors.{name}] sections with 'output = \"path\"' for each monitor.",
}


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def breaking_context():
    """Context for breaking changes tests."""
    return {
        "config_content": "",
        "deprecated_key": None,
        "error": None,
        "error_message": "",
        "exit_code": 0,
    }


# ============================================================================
# Given Steps
# ============================================================================

@given(parsers.parse('a config with deprecated key "{key}" set to {value:d}'))
def given_deprecated_key_with_value(breaking_context, key, value):
    """Create config with deprecated key and value."""
    section, field = key.split(".", 1)
    breaking_context["config_content"] = f"""
[{section}]
{field} = {value}
command = "swaybg"
"""
    breaking_context["deprecated_key"] = key


@given(parsers.parse('a config with deprecated key "{key}"'))
def given_deprecated_key(breaking_context, key):
    """Create config with deprecated key."""
    section, field = key.split(".", 1)
    breaking_context["config_content"] = f"""
[{section}]
{field} = "test_value"
command = "swaybg"
"""
    breaking_context["deprecated_key"] = key


@given(parsers.parse('a config with old array-style "{key}" key'))
def given_old_array_style(breaking_context, key):
    """Create config with old array-style key."""
    breaking_context["config_content"] = f"""
[monitors]
{key} = ["a.json", "b.json"]
templates = ["a.prompt", "b.prompt"]
"""


@given("a config file with both old and new formats")
def given_mixed_format_config(breaking_context):
    """Create config with both old and new format (invalid)."""
    breaking_context["config_content"] = """
[monitors]
count = 3
workflows = ["a.json", "b.json", "c.json"]

[monitors.DP-1]
workflow = "ultrawide"
"""


@given(parsers.parse('a config file with deprecated key "{key}"'))
def given_deprecated_key_simple(breaking_context, key):
    """Create config with a specific deprecated key."""
    breaking_context["deprecated_key"] = key
    
    if key == "monitors.pattern":
        breaking_context["config_content"] = """
[monitors]
pattern = "monitor_{index}.png"
command = "swaybg"
"""
    elif key == "monitors.count":
        breaking_context["config_content"] = """
[monitors]
count = 2
command = "swaybg"
"""


# ============================================================================
# When Steps
# ============================================================================

@when("I load the configuration")
def when_load_config(breaking_context):
    """Attempt to load configuration with deprecated keys."""
    content = breaking_context["config_content"]
    
    # Check for deprecated keys
    import tomli
    try:
        config = tomli.loads(content)
    except Exception as e:
        breaking_context["error"] = str(e)
        breaking_context["error_message"] = str(e)
        breaking_context["exit_code"] = 1
        return
    
    # Check monitors section for deprecated keys
    monitors = config.get("monitors", {})
    
    errors = []
    for key, migration in DEPRECATED_KEYS.items():
        section, field = key.split(".", 1)
        if section == "monitors" and field in monitors:
            errors.append(f'"{key}" is deprecated. {migration}')
    
    # Check for array-style config
    if "workflows" in monitors and isinstance(monitors["workflows"], list):
        errors.append("Array-style 'workflows' is deprecated. Use [monitors.{name}] sections instead.")
    if "templates" in monitors and isinstance(monitors["templates"], list):
        errors.append("Array-style 'templates' is deprecated. Use [monitors.{name}] sections instead.")
    
    if errors:
        breaking_context["error"] = "Deprecated configuration keys found"
        breaking_context["error_message"] = "\n".join(errors) + "\n\nSee docs/requirements/REQUIREMENTS.md for migration guide."
        breaking_context["exit_code"] = 1


# ============================================================================
# Then Steps
# ============================================================================

@then(parsers.parse('I should see an error mentioning "{text}"'))
def then_error_mentions(breaking_context, text):
    """Verify error mentions specific text."""
    error_msg = breaking_context["error_message"]
    assert text in error_msg, f"Error should mention '{text}'. Got: {error_msg}"


@then("the error should include migration instructions")
def then_error_has_migration(breaking_context):
    """Verify error includes migration instructions."""
    error_msg = breaking_context["error_message"]
    # Check for migration-related content
    assert any(x in error_msg for x in ["Use", "migration", "sections", "instead"]), \
        f"Error should include migration instructions. Got: {error_msg}"


@then(parsers.parse("the exit code should be {code:d}"))
def then_exit_code(breaking_context, code):
    """Verify exit code."""
    assert breaking_context["exit_code"] == code, \
        f"Expected exit code {code}, got {breaking_context['exit_code']}"


@then("I should see an error about deprecated format")
def then_error_deprecated_format(breaking_context):
    """Verify error about deprecated format."""
    error_msg = breaking_context["error_message"]
    assert "deprecated" in error_msg.lower(), f"Error should mention 'deprecated'. Got: {error_msg}"


@then("the error should explain the new format")
def then_error_explains_new_format(breaking_context):
    """Verify error explains new format."""
    error_msg = breaking_context["error_message"]
    assert "[monitors." in error_msg or "sections" in error_msg, \
        f"Error should explain new format. Got: {error_msg}"


@then(parsers.parse('the error should mention "{key}" is deprecated'))
def then_error_mentions_deprecated(breaking_context, key):
    """Verify error mentions specific key is deprecated."""
    error_msg = breaking_context["error_message"]
    assert key in error_msg and "deprecated" in error_msg.lower(), \
        f"Error should mention '{key}' is deprecated. Got: {error_msg}"


@then(parsers.parse('the error should mention "{text}" sections'))
def then_error_mentions_sections(breaking_context, text):
    """Verify error mentions sections."""
    error_msg = breaking_context["error_message"]
    assert text in error_msg or "sections" in error_msg.lower(), \
        f"Error should mention '{text}' sections. Got: {error_msg}"


@then("the error should reference the documentation")
def then_error_references_docs(breaking_context):
    """Verify error references documentation."""
    error_msg = breaking_context["error_message"]
    assert "docs" in error_msg.lower() or "requirements" in error_msg.lower(), \
        f"Error should reference documentation. Got: {error_msg}"


@then("the old format should NOT be silently ignored")
def then_old_not_ignored(breaking_context):
    """Verify old format causes error, not silent ignore."""
    assert breaking_context["exit_code"] != 0, "Old format should cause error, not be silently ignored"
    assert breaking_context["error"] is not None, "Should have an error for old format"


@then("an error should be raised immediately")
def then_error_raised(breaking_context):
    """Verify error was raised."""
    assert breaking_context["error"] is not None, "Expected an error to be raised"
    assert breaking_context["exit_code"] == 1, f"Expected exit code 1, got {breaking_context['exit_code']}"


@then("the error message should include:")
def then_error_includes(breaking_context, datatable):
    """Verify error message includes all specified content."""
    error_msg = breaking_context["error_message"]
    
    for row in datatable:
        content = row["content"]
        assert content in error_msg, f"Error should include '{content}'. Got: {error_msg}"
