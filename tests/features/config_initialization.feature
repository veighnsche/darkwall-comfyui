@REQ-CONFIG-001 @REQ-CONFIG-002
Feature: Configuration Initialization
    As a new user
    I want my config directory to be initialized with defaults
    So that I can start using darkwall immediately

    Background:
        Given a clean user config directory

    @REQ-CONFIG-001
    Scenario: Initialize config directory on first run
        Given DARKWALL_CONFIG_TEMPLATES points to valid templates
        When I run "darkwall init"
        Then config.toml should exist in user config directory
        And themes/light/ directory should exist
        And themes/dark/ directory should exist
        And workflows/ directory should exist

    @REQ-CONFIG-002
    Scenario: Preserve existing user config
        Given user has existing config.toml with custom settings
        When I run "darkwall init"
        Then the existing config.toml should not be overwritten
        And user customizations should be preserved

    Scenario: Copy theme atoms and prompts
        Given DARKWALL_CONFIG_TEMPLATES points to valid templates
        When I run "darkwall init"
        Then themes/light/atoms/ should contain atom files
        And themes/light/prompts/ should contain prompt files
        And themes/dark/atoms/ should contain atom files
        And themes/dark/prompts/ should contain prompt files

    Scenario: Copy workflow files
        Given DARKWALL_CONFIG_TEMPLATES points to valid templates
        When I run "darkwall init"
        Then workflows/ should contain JSON workflow files

    Scenario: Files are writable after copy
        Given DARKWALL_CONFIG_TEMPLATES points to read-only Nix store
        When I run "darkwall init"
        Then all copied files should be writable
        And user can edit config.toml

    Scenario: Warning when templates not found
        Given DARKWALL_CONFIG_TEMPLATES is not set
        And no config.toml exists
        When I run "darkwall init"
        Then I should see a warning about missing templates
        And the command should not fail

    @REQ-CONFIG-003
    Scenario: Config directory location
        Given XDG_CONFIG_HOME is set to "/tmp/test-config"
        When I determine the config directory
        Then it should be "/tmp/test-config/darkwall-comfyui"

    Scenario: Default config directory
        Given XDG_CONFIG_HOME is not set
        When I determine the config directory
        Then it should be "~/.config/darkwall-comfyui"
