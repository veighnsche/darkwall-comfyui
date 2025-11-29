@REQ-MONITOR-003 @REQ-MONITOR-004 @REQ-MONITOR-007
Feature: Monitor Configuration
    As a user
    I want to configure each monitor by its compositor name
    So that my config is tied to actual outputs, not arbitrary indices

    Scenario: Configure monitor with inline section
        Given monitor "DP-1" is configured with workflow "2327x1309"
        And monitor "HDMI-A-1" is configured with workflow "2327x1309"
        And monitor "HDMI-A-2" is configured with workflow "1920x1080"
        When I load the configuration
        Then monitor "DP-1" should use workflow "2327x1309"
        And monitor "HDMI-A-2" should use workflow "1920x1080"

    @REQ-MONITOR-004
    Scenario: Error on unconfigured monitor
        Given monitor "DP-1" is configured with workflow "2327x1309"
        And the compositor reports monitor "DP-1"
        And the compositor reports monitor "HDMI-A-1"
        When I validate the configuration
        Then I should see an error mentioning "HDMI-A-1"
        And the exit code should be 1

    Scenario: All monitors must be configured
        Given the compositor reports monitor "DP-1"
        And the compositor reports monitor "HDMI-A-2"
        And the compositor reports monitor "HDMI-A-1"
        And all reported monitors are configured
        When I validate the configuration
        Then validation should succeed

    # REQ-MONITOR-012: Unconfigured monitors → Skip with warning (default)
    # REQ-MONITOR-013: Disconnected configured monitor → Warn and skip
