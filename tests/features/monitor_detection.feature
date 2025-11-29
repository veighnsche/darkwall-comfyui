@REQ-MONITOR-001 @REQ-MONITOR-002
Feature: Monitor Detection
    As a user with multiple monitors
    I want darkwall to auto-detect my monitors from the compositor
    So that I don't have to manually configure monitor count

    Background:
        Given the compositor is "niri"

    Scenario: Detect monitors from niri
        When I run monitor detection
        Then I should see monitors:
            | name     | resolution |
            | DP-1     | 2560x1440  |
            | HDMI-A-2 | 1920x1080  |
            | HDMI-A-1 | 2560x1440  |

    Scenario: Use compositor output names as identifiers
        When I run monitor detection
        Then monitor "DP-1" should be identified by name not index
        And monitor "HDMI-A-1" should be identified by name not index

    @planned
    Scenario: Detect monitors from sway
        Given the compositor is "sway"
        When I run monitor detection
        Then I should see the connected monitors

    @planned
    Scenario: Detect monitors from hyprland
        Given the compositor is "hyprland"
        When I run monitor detection
        Then I should see the connected monitors

    # REQ-MONITOR-010: Compositor not running → Error with clear message
    # REQ-MONITOR-010: Detection command fails → Error with actual message
    # REQ-MONITOR-011: Cache until monitor change detected
