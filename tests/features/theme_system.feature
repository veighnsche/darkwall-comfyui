@REQ-THEME-001 @REQ-THEME-004 @REQ-THEME-005
Feature: Theme System
    As a user
    I want to organize my prompts and atoms into themes
    So that I can have separate content for SFW and NSFW

    @REQ-THEME-001
    Scenario: Theme directory structure
        Given a config directory with themes:
            """
            themes/
            ├── default/
            │   ├── atoms/
            │   │   └── subjects.txt
            │   └── prompts/
            │       └── default.prompt
            └── nsfw/
                ├── atoms/
                │   └── subjects.txt
                └── prompts/
                    └── default.prompt
            """
        When I load theme "default"
        Then atoms should be loaded from "themes/default/atoms/"
        And prompts should be loaded from "themes/default/prompts/"

    @REQ-THEME-004
    Scenario: Global theme for all monitors
        Given theme is set to "nsfw" globally
        And I have 3 monitors configured
        When I generate wallpapers for all monitors
        Then all monitors should use theme "nsfw"
        And no monitor should use a different theme

    @REQ-THEME-005
    Scenario: Fallback to default when theme missing
        Given theme is set to "nonexistent"
        And theme "default" exists
        When I load the configuration
        Then I should see a warning about "nonexistent"
        And theme "default" should be used instead
        And generation should continue (not error)

    @REQ-THEME-005
    Scenario: Warning logged for missing theme
        Given theme is set to "fantasy"
        And theme "fantasy" does not exist
        When I load the configuration
        Then the log should contain "WARNING"
        And the log should mention "fantasy"

    # UNCLEAR: What if "default" theme also doesn't exist?
    # UNCLEAR: Should we create theme directories on init?
    # UNCLEAR: Can themes inherit from other themes?
