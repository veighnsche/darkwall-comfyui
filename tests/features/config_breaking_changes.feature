@REQ-CONFIG-005
Feature: Breaking Changes - Fail Hard
    As a developer
    I want deprecated config keys to cause hard errors
    So that we don't accumulate backwards compatibility tech debt

    Scenario: Error on deprecated key
        Given a config file with deprecated key "monitors.count":
            """
            [monitors]
            count = 3
            command = "swaybg"
            """
        When I load the configuration
        Then I should see an error mentioning "monitors.count"
        And the error should include migration instructions
        And the exit code should be 1

    Scenario: Error on old array-style monitors
        Given a config file with old format:
            """
            [monitors]
            workflows = ["a.json", "b.json"]
            templates = ["a.prompt", "b.prompt"]
            """
        When I load the configuration
        Then I should see an error about deprecated format
        And the error should explain the new format

    Scenario: No silent fallback for deprecated keys
        Given a config file with both old and new formats
        When I load the configuration
        Then the old format should NOT be silently ignored
        And an error should be raised immediately

    Scenario: Migration guide in error message
        Given a config file with deprecated key "monitors.pattern"
        When I load the configuration
        Then the error message should include:
            | content                              |
            | "monitors.pattern" is deprecated     |
            | Use [monitors.{name}] sections       |
            | See docs/requirements/REQUIREMENTS.md |

    # UNCLEAR: What is the full list of deprecated keys?
    # UNCLEAR: Should we provide a migration command?
