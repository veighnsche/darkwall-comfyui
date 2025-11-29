@REQ-COMFY-005 @REQ-SCHED-004 @REQ-MISC-003
Feature: CLI Status Command
    As a user
    I want to see the current system status
    So that I can debug issues and monitor the schedule

    @REQ-COMFY-005
    Scenario: Status shows ComfyUI health
        Given ComfyUI is running
        When I run "darkwall status"
        Then the output should contain "ComfyUI URL"
        And the output should contain "Connected"
        And the output should contain response time

    Scenario: Status shows current theme
        Given the schedule is configured
        And it is currently daytime
        When I run "darkwall status"
        Then I should see "Current theme: default"

    @REQ-SCHED-004 @planned
    Scenario: Status shows 24h schedule table
        Given the schedule is configured with solar times
        When I run "darkwall status"
        Then the output should contain "Theme Schedule"
        And the output should contain "TIME"
        And the output should contain "THEME"
        And the output should contain "PROBABILITY"

    @REQ-MISC-003 @planned
    Scenario: JSON output for waybar integration
        When I run "darkwall status --json"
        Then the output should be valid JSON
        And the JSON should contain key "comfyui_status"
        And the JSON should contain key "current_theme"
        And the JSON should contain key "next_transition"
        And the JSON should contain key "monitors"

    @REQ-MISC-003 @planned
    Scenario: JSON format for external tools
        When I run "darkwall status --json"
        Then the output should be parseable by jq
        And should work with waybar custom modules

    Scenario: Status when ComfyUI is unreachable
        Given ComfyUI is not running
        When I run "darkwall status"
        Then I should see "ComfyUI: Unreachable"
        And the exit code should still be 0
        # Status command should not fail, just report state

    # REQ-COMFY-005: Status shows current rotation position
