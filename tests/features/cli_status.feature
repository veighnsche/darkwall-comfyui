@REQ-COMFY-005 @REQ-SCHED-004 @REQ-MISC-003
Feature: CLI Status Command
    As a user
    I want to see the current system status
    So that I can debug issues and monitor the schedule

    @REQ-COMFY-005
    Scenario: Status shows ComfyUI health
        Given ComfyUI is running
        When I run "darkwall status"
        Then I should see:
            | field         | example value    |
            | ComfyUI URL   | http://localhost:8188 |
            | Status        | Connected        |
            | Response time | 45ms             |

    Scenario: Status shows current theme
        Given the schedule is configured
        And it is currently daytime
        When I run "darkwall status"
        Then I should see "Current theme: default"

    @REQ-SCHED-004 @planned
    Scenario: Status shows 24h schedule table
        Given the schedule is configured with solar times
        When I run "darkwall status"
        Then I should see a table:
            """
            Theme Schedule (next 24h):
            TIME        THEME     PROBABILITY
            06:00       default   100%
            18:30       (blend)   SFW 70% / NSFW 30%
            19:00       nsfw      100%
            """

    @REQ-MISC-003 @planned
    Scenario: JSON output for waybar integration
        When I run "darkwall status --json"
        Then the output should be valid JSON
        And the JSON should contain:
            | key              |
            | comfyui_status   |
            | current_theme    |
            | next_transition  |
            | monitors         |

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
