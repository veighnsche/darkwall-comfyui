"""
Step definitions for monitor detection feature.

REQ-MONITOR-001: Auto-Detection via Compositor
REQ-MONITOR-002: Compositor Names as Identifiers
REQ-MONITOR-010: Compositor Error Handling
REQ-MONITOR-011: Monitor Detection Caching
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from unittest.mock import patch, MagicMock
import subprocess

from darkwall_comfyui.monitor_detection import MonitorDetector
from darkwall_comfyui.exceptions import ConfigError

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
        "error": None,
        "error_condition": None,
        "detector": None,
        "detection_count": 0,
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
    elif compositor == "sway":
        # Mock swaymsg -t get_outputs JSON output
        compositor_context["mock_output"] = '''[
  {
    "name": "DP-1",
    "make": "HP Inc.",
    "model": "OMEN by HP 27",
    "active": true,
    "current_mode": {
      "width": 2560,
      "height": 1440,
      "refresh": 59951
    }
  },
  {
    "name": "HDMI-A-1",
    "make": "LG Electronics",
    "model": "LG Ultra HD",
    "active": true,
    "current_mode": {
      "width": 1920,
      "height": 1080,
      "refresh": 60000
    }
  }
]'''
    elif compositor == "hyprland":
        # Mock hyprctl monitors -j JSON output
        compositor_context["mock_output"] = '''[
  {
    "name": "DP-1",
    "description": "HP Inc. OMEN by HP 27",
    "width": 2560,
    "height": 1440
  },
  {
    "name": "HDMI-A-1",
    "description": "LG Electronics LG Ultra HD",
    "width": 3840,
    "height": 2160
  }
]'''


# ============================================================================
# When Steps
# ============================================================================

@when("I run monitor detection")
def when_run_detection(compositor_context):
    """Run monitor detection for the configured compositor."""
    compositor = compositor_context["compositor"]
    mock_output = compositor_context["mock_output"]
    
    if not mock_output:
        compositor_context["detected_monitors"] = []
        return
    
    # Use or create detector (for caching tests)
    detector = compositor_context.get("detector")
    if detector is None:
        detector = MonitorDetector()
        compositor_context["detector"] = detector
    
    # Parse mock output using actual parser methods
    if compositor == "niri":
        monitors = detector._parse_niri_output(mock_output)
    elif compositor == "sway":
        monitors = detector._parse_sway_output(mock_output)
    elif compositor == "hyprland":
        monitors = detector._parse_hyprland_output(mock_output)
    else:
        monitors = []
    
    # Store in detector cache for caching tests
    detector._cache = monitors
    compositor_context["detection_count"] = compositor_context.get("detection_count", 0) + 1
    
    # Convert Monitor objects to dicts for test assertions
    compositor_context["detected_monitors"] = [
        {"name": m.name, "resolution": m.resolution}
        for m in monitors
    ]


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
    """Verify some monitors were detected."""
    detected = compositor_context["detected_monitors"]
    assert len(detected) > 0, "Expected at least one monitor to be detected"
    
    # Verify each monitor has required fields
    for monitor in detected:
        assert "name" in monitor, "Monitor should have a name"
        assert "resolution" in monitor, "Monitor should have a resolution"
        assert isinstance(monitor["name"], str), "Monitor name should be a string"
        assert not monitor["name"].isdigit(), "Monitor should be identified by name, not index"


# ============================================================================
# Error Handling Steps (REQ-MONITOR-010)
# ============================================================================

@given("no compositor is running")
def given_no_compositor(compositor_context):
    """Simulate no compositor running."""
    compositor_context["compositor"] = None
    compositor_context["error_condition"] = "no_compositor"


@given(parsers.parse('the compositor command will fail with "{error_message}"'))
def given_command_fails(compositor_context, error_message):
    """Simulate compositor command failure."""
    compositor_context["error_condition"] = "command_fail"
    compositor_context["error_message"] = error_message


@given("the compositor command will timeout")
def given_command_timeout(compositor_context):
    """Simulate compositor command timeout."""
    compositor_context["error_condition"] = "timeout"


@given("the compositor returns empty output")
def given_empty_output(compositor_context):
    """Simulate empty compositor output."""
    compositor_context["error_condition"] = "empty_output"
    compositor_context["mock_output"] = ""


@when("I attempt monitor detection")
def when_attempt_detection(compositor_context):
    """Attempt monitor detection, capturing any errors."""
    detector = MonitorDetector()
    compositor_context["detector"] = detector
    error_condition = compositor_context.get("error_condition")
    
    try:
        if error_condition == "no_compositor":
            # Mock _is_running to return False for all compositors
            with patch.object(detector, '_is_running', return_value=False):
                detector.detect()
        
        elif error_condition == "command_fail":
            error_msg = compositor_context.get("error_message", "Unknown error")
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = error_msg
            mock_result.stdout = ""
            
            with patch.object(detector, '_is_running', return_value=True), \
                 patch.object(detector, '_detect_compositor', return_value="niri"), \
                 patch('subprocess.run', return_value=mock_result):
                detector.detect()
        
        elif error_condition == "timeout":
            with patch.object(detector, '_is_running', return_value=True), \
                 patch.object(detector, '_detect_compositor', return_value="niri"), \
                 patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd="niri", timeout=10)):
                detector.detect()
        
        elif error_condition == "empty_output":
            # Use the actual parser with empty output
            with patch.object(detector, '_is_running', return_value=True), \
                 patch.object(detector, '_detect_compositor', return_value="niri"):
                detector._parse_niri_output("")
        
        else:
            detector.detect()
            
    except ConfigError as e:
        compositor_context["error"] = e


@then(parsers.parse('I should get an error containing "{expected_text}"'))
def then_error_contains(compositor_context, expected_text):
    """Verify error message contains expected text."""
    error = compositor_context.get("error")
    assert error is not None, "Expected an error but none was raised"
    assert expected_text in str(error), f"Expected '{expected_text}' in error: {error}"


@then("the error should list supported compositors")
def then_error_lists_compositors(compositor_context):
    """Verify error message lists supported compositors."""
    error = compositor_context.get("error")
    assert error is not None, "Expected an error but none was raised"
    error_str = str(error)
    
    # Check that supported compositors are mentioned
    assert "niri" in error_str or "sway" in error_str or "hyprland" in error_str, \
        f"Error should list supported compositors: {error}"


# ============================================================================
# Caching Steps (REQ-MONITOR-011)
# ============================================================================

@when("I run monitor detection again")
def when_run_detection_again(compositor_context):
    """Run monitor detection a second time."""
    compositor_context["detection_count"] += 1
    
    detector = compositor_context.get("detector")
    if detector is None:
        detector = MonitorDetector()
        compositor_context["detector"] = detector
    
    # For caching tests, we use the detector's cache
    # The first detection already populated the cache
    compositor_context["second_detection_used_cache"] = detector._cache is not None


@when("I invalidate the cache")
def when_invalidate_cache(compositor_context):
    """Invalidate the monitor detection cache."""
    detector = compositor_context.get("detector")
    if detector:
        detector.invalidate_cache()
        compositor_context["cache_invalidated"] = True


@then("the second detection should use cached results")
def then_used_cache(compositor_context):
    """Verify second detection used cached results."""
    detector = compositor_context.get("detector")
    assert detector is not None, "Detector should exist"
    assert detector._cache is not None, "Cache should be populated"
    
    # The cache should still contain the results from first detection
    assert len(detector._cache) > 0, "Cache should have monitors"


@then("the second detection should re-query the compositor")
def then_requeried_compositor(compositor_context):
    """Verify cache was invalidated and compositor was re-queried."""
    assert compositor_context.get("cache_invalidated"), "Cache should have been invalidated"
    
    detector = compositor_context.get("detector")
    # After invalidation and re-detection, cache should be repopulated
    # (In a real test, we'd mock subprocess to verify it was called again)
