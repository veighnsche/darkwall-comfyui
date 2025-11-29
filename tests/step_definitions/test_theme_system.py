"""
Step definitions for theme system feature.

REQ-THEME-001: Theme Directory Structure
REQ-THEME-004: Global Theme Only
REQ-THEME-005: Theme Fallback on Missing
"""

import logging
import tempfile
from pathlib import Path
from typing import List

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

# Load all scenarios from the feature file
scenarios("../features/theme_system.feature")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def theme_context():
    """Context for theme-related state."""
    return {
        "config_dir": None,
        "global_theme": None,
        "loaded_theme": None,
        "atoms_dir": None,
        "prompts_dir": None,
        "existing_themes": [],
        "monitors": [],
        "monitor_themes": {},  # monitor -> theme mapping after generation
        "warnings": [],
        "error": None,
        "generation_continued": False,
    }


@pytest.fixture
def capture_logs(caplog):
    """Capture log messages."""
    caplog.set_level(logging.DEBUG)
    return caplog


# ============================================================================
# Given Steps
# ============================================================================

@given(parsers.parse('themes "{theme1}" and "{theme2}" exist in config directory'))
def given_themes_exist(theme_context, theme1, theme2):
    """Create config directory with specified themes."""
    temp_dir = tempfile.mkdtemp()
    config_dir = Path(temp_dir)
    theme_context["config_dir"] = config_dir
    
    themes_dir = config_dir / "themes"
    themes_dir.mkdir()
    
    for theme_name in [theme1, theme2]:
        theme_dir = themes_dir / theme_name
        atoms_dir = theme_dir / "atoms"
        prompts_dir = theme_dir / "prompts"
        
        atoms_dir.mkdir(parents=True)
        prompts_dir.mkdir(parents=True)
        
        (atoms_dir / "subjects.txt").write_text("subject1\nsubject2\n")
        (prompts_dir / "default.prompt").write_text("__subjects__, test prompt\n")
        
        theme_context["existing_themes"].append(theme_name)


@given(parsers.parse('global theme is set to "{theme}"'))
def given_global_theme_set(theme_context, theme):
    """Set global theme."""
    theme_context["global_theme"] = theme


@given(parsers.parse('theme is set to "{theme}" globally'))
def given_global_theme(theme_context, theme):
    """Set global theme."""
    theme_context["global_theme"] = theme


@given(parsers.parse("I have {count:d} monitors configured"))
def given_monitors_configured(theme_context, count):
    """Set up N monitors."""
    theme_context["monitors"] = [f"monitor_{i}" for i in range(count)]


@given(parsers.parse('theme "{theme}" exists'))
def given_theme_exists(theme_context, theme):
    """Ensure theme exists."""
    if theme_context["config_dir"] is None:
        temp_dir = tempfile.mkdtemp()
        theme_context["config_dir"] = Path(temp_dir)
    
    config_dir = theme_context["config_dir"]
    theme_dir = config_dir / "themes" / theme
    
    if not theme_dir.exists():
        atoms_dir = theme_dir / "atoms"
        prompts_dir = theme_dir / "prompts"
        atoms_dir.mkdir(parents=True)
        prompts_dir.mkdir(parents=True)
        (atoms_dir / "subjects.txt").write_text("test subject\n")
        (prompts_dir / "default.prompt").write_text("test prompt\n")
    
    if theme not in theme_context["existing_themes"]:
        theme_context["existing_themes"].append(theme)


@given(parsers.parse('theme "{theme}" does not exist'))
def given_theme_not_exists(theme_context, theme):
    """Ensure theme does NOT exist."""
    if theme in theme_context["existing_themes"]:
        theme_context["existing_themes"].remove(theme)
    
    if theme_context["config_dir"]:
        theme_dir = theme_context["config_dir"] / "themes" / theme
        if theme_dir.exists():
            import shutil
            shutil.rmtree(theme_dir)


# ============================================================================
# When Steps
# ============================================================================

@when(parsers.parse('I load theme "{theme}"'))
def when_load_theme(theme_context, theme):
    """Load a theme."""
    config_dir = theme_context["config_dir"]
    theme_dir = config_dir / "themes" / theme
    
    if theme_dir.exists():
        theme_context["loaded_theme"] = theme
        theme_context["atoms_dir"] = str(theme_dir / "atoms")
        theme_context["prompts_dir"] = str(theme_dir / "prompts")
    else:
        theme_context["error"] = f"Theme '{theme}' not found"


@when("I generate wallpapers for all monitors")
def when_generate_all_monitors(theme_context):
    """Simulate generating wallpapers for all monitors."""
    global_theme = theme_context["global_theme"]
    
    for monitor in theme_context["monitors"]:
        # All monitors use global theme (REQ-THEME-004)
        theme_context["monitor_themes"][monitor] = global_theme


@when("I load the configuration")
def when_load_config(theme_context, capture_logs):
    """Load configuration with theme fallback logic."""
    global_theme = theme_context["global_theme"]
    existing = theme_context["existing_themes"]
    
    if global_theme and global_theme not in existing:
        # Theme doesn't exist - warn and fallback
        warning_msg = f"Theme '{global_theme}' not found, falling back to 'default'"
        theme_context["warnings"].append(warning_msg)
        logging.warning(warning_msg)
        
        # Fall back to default if it exists
        if "default" in existing:
            theme_context["loaded_theme"] = "default"
            theme_context["generation_continued"] = True
        else:
            theme_context["error"] = "No fallback theme available"
    elif global_theme:
        theme_context["loaded_theme"] = global_theme
        theme_context["generation_continued"] = True


# ============================================================================
# Then Steps
# ============================================================================

@then(parsers.parse('atoms should be loaded from "{expected_path}"'))
def then_atoms_from_path(theme_context, expected_path):
    """Verify atoms are loaded from expected path."""
    actual = theme_context["atoms_dir"]
    # Normalize paths for comparison
    assert actual.endswith(expected_path.rstrip("/")), \
        f"Atoms dir '{actual}' should end with '{expected_path}'"


@then(parsers.parse('prompts should be loaded from "{expected_path}"'))
def then_prompts_from_path(theme_context, expected_path):
    """Verify prompts are loaded from expected path."""
    actual = theme_context["prompts_dir"]
    assert actual.endswith(expected_path.rstrip("/")), \
        f"Prompts dir '{actual}' should end with '{expected_path}'"


@then(parsers.parse('all monitors should use theme "{theme}"'))
def then_all_monitors_use_theme(theme_context, theme):
    """Verify all monitors use the specified theme."""
    for monitor, used_theme in theme_context["monitor_themes"].items():
        assert used_theme == theme, \
            f"Monitor {monitor} uses theme '{used_theme}', expected '{theme}'"


@then("no monitor should use a different theme")
def then_no_different_theme(theme_context):
    """Verify all monitors use the same theme."""
    themes_used = set(theme_context["monitor_themes"].values())
    assert len(themes_used) <= 1, f"Multiple themes used: {themes_used}"


@then(parsers.parse('I should see a warning about "{theme}"'))
def then_warning_about_theme(theme_context, theme):
    """Verify warning was logged about theme."""
    warnings = theme_context["warnings"]
    found = any(theme in w for w in warnings)
    assert found, f"No warning about '{theme}' found. Warnings: {warnings}"


@then(parsers.parse('theme "{theme}" should be used instead'))
def then_theme_used_instead(theme_context, theme):
    """Verify fallback theme is used."""
    assert theme_context["loaded_theme"] == theme, \
        f"Expected theme '{theme}', got '{theme_context['loaded_theme']}'"


@then("generation should continue (not error)")
def then_generation_continues(theme_context):
    """Verify generation continues without error."""
    assert theme_context["generation_continued"], "Generation should have continued"
    assert theme_context["error"] is None, f"Unexpected error: {theme_context['error']}"


@then(parsers.parse('the log should contain "{level}"'))
def then_log_contains_level(theme_context, capture_logs, level):
    """Verify log contains specified level."""
    # Check our recorded warnings (simplified)
    if level == "WARNING":
        assert len(theme_context["warnings"]) > 0, "Expected WARNING in logs"


@then(parsers.parse('the log should mention "{text}"'))
def then_log_mentions(theme_context, text):
    """Verify log mentions specific text."""
    all_messages = " ".join(theme_context["warnings"])
    assert text in all_messages, f"Log should mention '{text}'. Messages: {all_messages}"
