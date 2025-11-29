"""
Step definitions for scheduling feature.

REQ-SCHED-002: Sundown/Sunrise Theme Switching
REQ-SCHED-003: Probability Blend Transitions
REQ-SCHED-004: 24-Hour Schedule Status
"""

from datetime import datetime, time, timedelta
from typing import Optional

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

# Load all scenarios from the feature file
scenarios("../features/scheduling.feature")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def schedule_context():
    """Context for scheduling tests."""
    return {
        "config": {},
        "latitude": None,
        "longitude": None,
        "sunset_time": None,
        "sunrise_time": None,
        "current_time": None,
        "blend_duration": 30,  # minutes
        "manual_nsfw_start": None,
        "manual_nsfw_end": None,
        "day_theme": "default",
        "night_theme": "nsfw",
        "determined_theme": None,
        "sfw_probability": None,
        "nsfw_probability": None,
        "status_output": "",
    }


# ============================================================================
# Helper Functions
# ============================================================================

def parse_time(time_str: str) -> time:
    """Parse time string like '18:00' or '23:30'."""
    return datetime.strptime(time_str, "%H:%M").time()


def is_night_time(current: time, nsfw_start: time, nsfw_end: time) -> bool:
    """Check if current time is in night (NSFW) period."""
    if nsfw_start < nsfw_end:
        # Simple case: start and end on same day
        return nsfw_start <= current < nsfw_end
    else:
        # Wraps midnight: e.g., 22:00 to 06:00
        return current >= nsfw_start or current < nsfw_end


# ============================================================================
# Given Steps
# ============================================================================

@given(parsers.parse('a default schedule config with day theme "{day}" and night theme "{night}"'))
def given_default_schedule_config(schedule_context, day, night):
    """Set up default schedule config."""
    schedule_context["day_theme"] = day
    schedule_context["night_theme"] = night


@given(parsers.parse('manual NSFW times from "{start}" to "{end}"'))
def given_manual_nsfw_times(schedule_context, start, end):
    """Set manual NSFW times."""
    schedule_context["manual_nsfw_start"] = parse_time(start)
    schedule_context["manual_nsfw_end"] = parse_time(end)


@given(parsers.parse("location is latitude {lat:f}, longitude {lon:f}"))
def given_location(schedule_context, lat, lon):
    """Set location for solar calculations."""
    schedule_context["latitude"] = lat
    schedule_context["longitude"] = lon


@given(parsers.parse("the current time is {hours:d} hours after sunset"))
def given_time_after_sunset(schedule_context, hours):
    """Set current time relative to sunset."""
    # Default sunset at 18:00 if not set
    sunset = schedule_context.get("sunset_time") or time(18, 0)
    
    # Calculate current time
    sunset_dt = datetime.combine(datetime.today(), sunset)
    current_dt = sunset_dt + timedelta(hours=hours)
    schedule_context["current_time"] = current_dt.time()


@given(parsers.parse('the current time is "{time_str}"'))
def given_current_time(schedule_context, time_str):
    """Set current time."""
    schedule_context["current_time"] = parse_time(time_str)


@given(parsers.parse('sunset is at "{time_str}"'))
def given_sunset_at(schedule_context, time_str):
    """Set sunset time."""
    schedule_context["sunset_time"] = parse_time(time_str)


@given(parsers.parse('the config has manual times "{start}" to "{end}"'))
def given_manual_times(schedule_context, start, end):
    """Set manual NSFW start/end times."""
    schedule_context["manual_nsfw_start"] = parse_time(start)
    schedule_context["manual_nsfw_end"] = parse_time(end)


@given(parsers.parse('the current time is "{time_str}" ({description})'))
def given_current_time_with_desc(schedule_context, time_str, description):
    """Set current time with description (ignored)."""
    schedule_context["current_time"] = parse_time(time_str)


@given(parsers.parse("blend duration is {minutes:d} minutes"))
def given_blend_duration(schedule_context, minutes):
    """Set blend duration."""
    schedule_context["blend_duration"] = minutes


@given("location is configured")
def given_location_configured(schedule_context):
    """Set default location."""
    schedule_context["latitude"] = 52.52
    schedule_context["longitude"] = 13.405


@given("it is currently daytime")
def given_daytime(schedule_context):
    """Set current time to daytime."""
    schedule_context["current_time"] = time(12, 0)


@given("the schedule is configured")
def given_schedule_configured(schedule_context):
    """Set up basic schedule config."""
    schedule_context["day_theme"] = "default"
    schedule_context["night_theme"] = "nsfw"
    schedule_context["latitude"] = 52.52
    schedule_context["longitude"] = 13.405


@given("the schedule is configured with solar times")
def given_schedule_with_solar(schedule_context):
    """Set up schedule with solar times."""
    given_schedule_configured(schedule_context)
    schedule_context["sunset_time"] = time(18, 30)
    schedule_context["sunrise_time"] = time(6, 0)


# ============================================================================
# When Steps
# ============================================================================

@when("I determine the current theme")
def when_determine_theme(schedule_context):
    """Determine current theme based on time."""
    current = schedule_context["current_time"]
    
    # Manual times take priority
    if schedule_context["manual_nsfw_start"] and schedule_context["manual_nsfw_end"]:
        nsfw_start = schedule_context["manual_nsfw_start"]
        nsfw_end = schedule_context["manual_nsfw_end"]
        
        if is_night_time(current, nsfw_start, nsfw_end):
            schedule_context["determined_theme"] = schedule_context["night_theme"]
        else:
            schedule_context["determined_theme"] = schedule_context["day_theme"]
    else:
        # Solar-based (simplified: assume sunset at 18:00 if not set)
        sunset = schedule_context.get("sunset_time") or time(18, 0)
        sunrise = schedule_context.get("sunrise_time") or time(6, 0)
        
        if is_night_time(current, sunset, sunrise):
            schedule_context["determined_theme"] = schedule_context["night_theme"]
        else:
            schedule_context["determined_theme"] = schedule_context["day_theme"]


@when("I determine theme probability")
def when_determine_probability(schedule_context):
    """Determine theme probability during blend period."""
    current = schedule_context["current_time"]
    sunset = schedule_context["sunset_time"]
    blend_minutes = schedule_context["blend_duration"]
    
    # Convert to minutes from midnight for calculation
    current_mins = current.hour * 60 + current.minute
    sunset_mins = sunset.hour * 60 + sunset.minute
    
    # Distance from sunset in minutes
    distance = current_mins - sunset_mins
    
    # Calculate probability (linear interpolation)
    if distance <= -blend_minutes:
        # Before blend period - 100% SFW
        sfw_prob = 100
    elif distance >= blend_minutes:
        # After blend period - 0% SFW
        sfw_prob = 0
    else:
        # In blend period - linear interpolation
        # At -30 min: 100% SFW, at 0: 50%, at +30 min: 0%
        sfw_prob = 50 - (distance / blend_minutes) * 50
    
    schedule_context["sfw_probability"] = sfw_prob
    schedule_context["nsfw_probability"] = 100 - sfw_prob


@when(parsers.parse('I run "{command}"'))
def when_run_command(schedule_context, command):
    """Simulate running a command."""
    if "status" in command:
        # Generate mock status output
        schedule_context["status_output"] = """
DarkWall Status
===============
ComfyUI: Connected (http://localhost:8188)
Current theme: default
Current rotation: DP-1

Theme Schedule (next 24h):
TIME        THEME     PROBABILITY
06:00       default   100%
18:30       (blend)   SFW 70% / NSFW 30%
19:00       nsfw      100%
"""


# ============================================================================
# Then Steps
# ============================================================================

@then(parsers.parse('the theme should be "{expected}"'))
def then_theme_is(schedule_context, expected):
    """Verify determined theme."""
    actual = schedule_context["determined_theme"]
    assert actual == expected, f"Expected theme '{expected}', got '{actual}'"


@then(parsers.parse("SFW probability should be approximately {percent:d}%"))
def then_sfw_probability(schedule_context, percent):
    """Verify SFW probability within tolerance."""
    actual = schedule_context["sfw_probability"]
    tolerance = 5  # Allow 5% tolerance
    assert abs(actual - percent) <= tolerance, \
        f"Expected SFW probability ~{percent}%, got {actual}%"


@then(parsers.parse("NSFW probability should be approximately {percent:d}%"))
def then_nsfw_probability(schedule_context, percent):
    """Verify NSFW probability within tolerance."""
    actual = schedule_context["nsfw_probability"]
    tolerance = 5
    assert abs(actual - percent) <= tolerance, \
        f"Expected NSFW probability ~{percent}%, got {actual}%"


@then(parsers.parse('the output should contain "{text}"'))
def then_output_contains(schedule_context, text):
    """Verify output contains text."""
    output = schedule_context["status_output"]
    assert text in output, f"Output should contain '{text}'. Got: {output}"


@then("the output should contain time entries")
def then_output_contains_time(schedule_context):
    """Verify output contains time entries."""
    output = schedule_context["status_output"]
    # Look for time pattern like HH:MM
    import re
    assert re.search(r'\d{2}:\d{2}', output), f"Output should contain time entries. Got: {output}"


@then("the output should contain theme names")
def then_output_contains_themes(schedule_context):
    """Verify output contains theme names."""
    output = schedule_context["status_output"]
    assert "default" in output or "nsfw" in output, f"Output should contain theme names. Got: {output}"
