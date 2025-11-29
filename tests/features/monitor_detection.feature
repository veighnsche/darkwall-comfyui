@REQ-MONITOR-001 @REQ-MONITOR-002
Feature: Monitor Detection
    As a user with multiple monitors
    I want darkwall to auto-detect my monitors from the compositor
    So that I don't have to manually configure monitor count

    Background:
        Given the compositor is "niri"

    Scenario: Detect monitors from niri
        When I run monitor detection
        Then I should detect 3 monitors
        And monitor "DP-1" should be detected with resolution "2560x1440"
        And monitor "HDMI-A-2" should be detected with resolution "1920x1080"
        And monitor "HDMI-A-1" should be detected with resolution "2560x1440"

    Scenario: Use compositor output names as identifiers
        When I run monitor detection
        Then monitor "DP-1" should be identified by name not index
        And monitor "HDMI-A-1" should be identified by name not index

    Scenario: Detect monitors from sway
        Given the compositor is "sway"
        When I run monitor detection
        Then I should see the connected monitors

    Scenario: Detect monitors from hyprland
        Given the compositor is "hyprland"
        When I run monitor detection
        Then I should see the connected monitors

    # =========================================================================
    # Error Handling (REQ-MONITOR-010)
    # =========================================================================

    @REQ-MONITOR-010
    Scenario: Error when no compositor is running
        Given no compositor is running
        When I attempt monitor detection
        Then I should get an error containing "No supported compositor running"
        And the error should list supported compositors

    @REQ-MONITOR-010
    Scenario: Error when compositor command fails
        Given the compositor is "niri"
        And the compositor command will fail with "Connection refused"
        When I attempt monitor detection
        Then I should get an error containing "Connection refused"

    @REQ-MONITOR-010
    Scenario: Error when compositor command times out
        Given the compositor is "niri"
        And the compositor command will timeout
        When I attempt monitor detection
        Then I should get an error containing "Timeout"

    @REQ-MONITOR-010
    Scenario: Error when no monitors detected
        Given the compositor is "niri"
        And the compositor returns empty output
        When I attempt monitor detection
        Then I should get an error containing "No monitors detected"

    # =========================================================================
    # Caching (REQ-MONITOR-011)
    # =========================================================================

    @REQ-MONITOR-011
    Scenario: Detection results are cached
        Given the compositor is "niri"
        When I run monitor detection
        And I run monitor detection again
        Then the second detection should use cached results

    @REQ-MONITOR-011
    Scenario: Cache can be invalidated
        Given the compositor is "niri"
        When I run monitor detection
        And I invalidate the cache
        And I run monitor detection again
        Then the second detection should re-query the compositor
