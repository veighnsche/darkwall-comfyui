@REQ-SCHED-002 @REQ-SCHED-003 @REQ-SCHED-004
Feature: Time-Based Theme Scheduling
    As a user
    I want themes to automatically switch based on time of day
    So that NSFW content only appears after sunset

    Background:
        Given the config has:
            """
            [schedule]
            day_theme = "default"
            night_theme = "nsfw"
            """

    @REQ-SCHED-002
    Scenario: Solar-based scheduling
        Given location is latitude 52.52, longitude 13.405
        And the current time is 2 hours after sunset
        When I determine the current theme
        Then the theme should be "nsfw"

    @REQ-SCHED-002
    Scenario: Manual time override
        Given the config has:
            """
            [schedule]
            nsfw_start = "22:00"
            nsfw_end = "06:00"
            day_theme = "default"
            night_theme = "nsfw"
            """
        And the current time is "23:30"
        When I determine the current theme
        Then the theme should be "nsfw"

    @REQ-SCHED-002
    Scenario: Manual times override solar calculation
        Given location is latitude 52.52, longitude 13.405
        And sunset is at "18:00"
        And the config has manual times "22:00" to "06:00"
        And the current time is "19:00"
        When I determine the current theme
        Then the theme should be "default"
        # Because 19:00 is after sunset but before manual nsfw_start

    @REQ-SCHED-003 @planned
    Scenario: Probability blend before sunset
        Given sunset is at "18:00"
        And blend duration is 30 minutes
        And the current time is "17:45" (15 min before sunset)
        When I determine theme probability
        Then SFW probability should be approximately 75%
        And NSFW probability should be approximately 25%

    @REQ-SCHED-003 @planned
    Scenario: Probability blend at sunset
        Given sunset is at "18:00"
        And blend duration is 30 minutes
        And the current time is "18:00" (at sunset)
        When I determine theme probability
        Then SFW probability should be approximately 50%
        And NSFW probability should be approximately 50%

    @REQ-SCHED-003 @planned
    Scenario: Probability blend after sunset
        Given sunset is at "18:00"
        And blend duration is 30 minutes
        And the current time is "18:15" (15 min after sunset)
        When I determine theme probability
        Then SFW probability should be approximately 25%
        And NSFW probability should be approximately 75%

    @REQ-SCHED-004 @planned
    Scenario: Status shows 24-hour schedule
        Given location is configured
        And it is currently daytime
        When I run "darkwall status"
        Then I should see a schedule table with columns:
            | TIME | THEME | PROBABILITY |
        And the table should show transitions for the next 24 hours

    # REQ-SCHED-002: Timezone → System local timezone
    # REQ-SCHED-003: Blend duration → Configurable with 30 min default
    # REQ-SCHED-002: DST → Astral handles automatically
    # REQ-SCHED-002: Astral fails → Error with message (no fallback)
