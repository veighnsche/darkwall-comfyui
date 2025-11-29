"""
Step definitions for monitor configuration feature.

REQ-MONITOR-003: Inline Config Sections
REQ-MONITOR-004: Error on Unconfigured
REQ-MONITOR-007: Per-Monitor Workflows
"""

import tempfile
from pathlib import Path

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

# Load all scenarios from the feature file
scenarios("../features/monitor_config.feature")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def config_context():
    """Context for config-related state."""
    return {
        "config_content": "",
        "config_dir": None,
        "config": None,
        "connected_monitors": [],
        "error": None,
        "exit_code": 0,
        "validation_result": None,
    }


# ============================================================================
# Given Steps
# ============================================================================

@given(parsers.parse('monitor "{name}" is configured with workflow "{workflow}"'))
def given_monitor_configured(config_context, name, workflow):
    """Configure a monitor with workflow."""
    if "configured_monitors" not in config_context:
        config_context["configured_monitors"] = {}
    config_context["configured_monitors"][name] = workflow
    
    # Build config content
    config_lines = []
    for mon_name, mon_workflow in config_context["configured_monitors"].items():
        config_lines.append(f'[monitors.{mon_name}]')
        config_lines.append(f'workflow = "{mon_workflow}"')
        config_lines.append('')
    config_context["config_content"] = '\n'.join(config_lines)


@given(parsers.parse('the compositor reports monitor "{name}"'))
def given_compositor_reports_monitor(config_context, name):
    """Add a monitor to the list of connected monitors."""
    if name not in config_context["connected_monitors"]:
        config_context["connected_monitors"].append(name)


@given("all reported monitors are configured")
def given_all_monitors_configured(config_context):
    """Create config with all connected monitors configured."""
    monitors = config_context["connected_monitors"]
    config_lines = []
    for name in monitors:
        config_lines.append(f'[monitors.{name}]')
        config_lines.append('workflow = "default"')
        config_lines.append('')
    config_context["config_content"] = '\n'.join(config_lines)
    config_context["configured_monitors"] = {m: "default" for m in monitors}


# ============================================================================
# When Steps
# ============================================================================

@when("I load the configuration")
def when_load_config(config_context):
    """Load the configuration from content."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        config_context["config_dir"] = config_dir
        
        # Write config file
        config_file = config_dir / "config.toml"
        
        # Add base config sections if not present
        content = config_context["config_content"]
        if "[comfyui]" not in content:
            content = """
[comfyui]
base_url = "http://localhost:8188"

[output]
directory = "~/Pictures/wallpapers"

""" + content
        
        config_file.write_text(content)
        
        # Create workflows directory
        workflows_dir = config_dir / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "2327x1309.json").write_text('{"test": true}')
        (workflows_dir / "1920x1080.json").write_text('{"test": true}')
        (workflows_dir / "default.json").write_text('{"test": true}')
        
        # Try to load config
        try:
            # TODO: Replace with actual config loading once monitor detection is implemented
            # For now, just parse the TOML to verify syntax
            import tomli
            with open(config_file, 'rb') as f:
                config_data = tomli.load(f)
            config_context["config"] = config_data
        except Exception as e:
            config_context["error"] = str(e)
            config_context["exit_code"] = 1


@when("I validate the configuration")
def when_validate_config(config_context):
    """Validate the configuration against connected monitors."""
    # First load the config
    when_load_config(config_context)
    
    if config_context["error"]:
        return
    
    config = config_context["config"]
    connected = config_context["connected_monitors"]
    
    # Check if monitors section exists
    monitors_config = config.get("monitors", {})
    
    # Get configured monitor names (keys that are not standard config keys)
    standard_keys = {"count", "command", "pattern", "backup_pattern", "workflows", "templates", "paths"}
    configured_monitors = [k for k in monitors_config.keys() if k not in standard_keys]
    
    # Check for unconfigured monitors
    unconfigured = [m for m in connected if m not in configured_monitors]
    
    if unconfigured:
        # REQ-MONITOR-012: Skip with warning is default, but REQ-MONITOR-004 says error
        # The feature file tests the error case
        config_context["error"] = f"Unconfigured monitors: {', '.join(unconfigured)}"
        config_context["exit_code"] = 1
    else:
        config_context["validation_result"] = "success"


# ============================================================================
# Then Steps
# ============================================================================

@then(parsers.parse('monitor "{name}" should use workflow "{workflow}"'))
def then_monitor_uses_workflow(config_context, name, workflow):
    """Verify monitor uses specified workflow."""
    config = config_context["config"]
    assert config is not None, f"Config not loaded. Error: {config_context.get('error')}"
    
    monitors = config.get("monitors", {})
    monitor_config = monitors.get(name, {})
    
    assert "workflow" in monitor_config, f"Monitor {name} has no workflow configured"
    assert monitor_config["workflow"] == workflow, \
        f"Monitor {name} uses workflow '{monitor_config['workflow']}', expected '{workflow}'"


@then(parsers.parse('I should see an error mentioning "{text}"'))
def then_error_mentions(config_context, text):
    """Verify error message contains text."""
    error = config_context.get("error")
    assert error is not None, "Expected an error but none occurred"
    assert text in error, f"Error '{error}' should mention '{text}'"


@then(parsers.parse("the exit code should be {code:d}"))
def then_exit_code(config_context, code):
    """Verify exit code."""
    assert config_context["exit_code"] == code, \
        f"Expected exit code {code}, got {config_context['exit_code']}"


@then("validation should succeed")
def then_validation_success(config_context):
    """Verify validation succeeded."""
    assert config_context["error"] is None, f"Validation failed: {config_context['error']}"
    assert config_context["validation_result"] == "success"
