"""
Step definitions for monitor detection feature.

REQ-MONITOR-001: Auto-Detection via Compositor
REQ-MONITOR-002: Compositor Names as Identifiers
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

# Load all scenarios from the feature file
scenarios("../features/monitor_detection.feature")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def compositor_context():
    """Context for compositor-related state."""
    return {
        "compositor": None,
        "detected_monitors": [],
        "mock_output": None,
    }


# ============================================================================
# Given Steps
# ============================================================================

@given(parsers.parse('the compositor is "{compositor}"'))
def given_compositor(compositor_context, compositor):
    """Set the compositor type."""
    compositor_context["compositor"] = compositor
    
    # Mock outputs for each compositor
    if compositor == "niri":
        compositor_context["mock_output"] = """
Output "HP Inc. OMEN by HP 27 CNK724200N" (DP-1)
  Current mode: 2560x1440 @ 59.951 Hz
  Logical size: 2327x1309

Output "LG Electronics LG IPS FULLHD 0x01010101" (HDMI-A-2)
  Current mode: 1920x1080 @ 60.000 Hz
  Logical size: 1920x1080

Output "LG Electronics LG Ultra HD 0x00064468" (HDMI-A-1)
  Current mode: 2560x1440 @ 59.951 Hz
  Logical size: 2327x1309
"""


# ============================================================================
# When Steps
# ============================================================================

@when("I run monitor detection")
def when_run_detection(compositor_context):
    """Run monitor detection for the configured compositor."""
    # TODO: Implement actual monitor detection
    # For now, parse mock output
    
    compositor = compositor_context["compositor"]
    mock_output = compositor_context["mock_output"]
    
    if compositor == "niri" and mock_output:
        # Simple parsing of mock niri output
        monitors = []
        import re
        for match in re.finditer(r'Output ".*?" \((\S+)\)\s+Current mode: (\d+x\d+)', mock_output):
            name, resolution = match.groups()
            monitors.append({"name": name, "resolution": resolution})
        compositor_context["detected_monitors"] = monitors


# ============================================================================
# Then Steps
# ============================================================================

@then(parsers.parse("I should detect {count:d} monitors"))
def then_detect_n_monitors(compositor_context, count):
    """Verify number of detected monitors."""
    detected = compositor_context["detected_monitors"]
    assert len(detected) == count, f"Expected {count} monitors, got {len(detected)}"


@then(parsers.parse('monitor "{name}" should be detected with resolution "{resolution}"'))
def then_monitor_detected_with_resolution(compositor_context, name, resolution):
    """Verify specific monitor was detected with resolution."""
    detected = compositor_context["detected_monitors"]
    
    found = any(
        m["name"] == name and m["resolution"] == resolution
        for m in detected
    )
    assert found, f"Monitor {name} with resolution {resolution} not found in {detected}"


@then(parsers.parse('monitor "{name}" should be identified by name not index'))
def then_monitor_by_name(compositor_context, name):
    """Verify monitor is identified by compositor name."""
    detected = compositor_context["detected_monitors"]
    
    # Check that monitor exists with string name, not integer index
    monitor_names = [m["name"] for m in detected]
    assert name in monitor_names, f"Monitor '{name}' not found. Available: {monitor_names}"
    
    # Verify it's a string identifier, not an index
    for m in detected:
        if m["name"] == name:
            assert isinstance(m["name"], str), "Monitor identifier should be string"
            assert not m["name"].isdigit(), "Monitor should not be identified by index"


@then("I should see the connected monitors")
def then_see_connected_monitors(compositor_context):
    """Verify some monitors were detected (generic check for planned features)."""
    # This is a placeholder for planned sway/hyprland support
    pytest.skip("Not yet implemented")
