@REQ-PROMPT-001 @REQ-PROMPT-002 @REQ-PROMPT-003
Feature: Prompt Generation CLI
    As a user
    I want to generate prompts via CLI
    So that I can copy them into ComfyUI manually

    Background:
        Given a config directory with themes "light" and "dark"
        And theme "dark" has prompts "default", "cyberpunk", "noir"
        And theme "light" has prompts "default", "landscape", "nature"

    @REQ-PROMPT-001
    Scenario: Generate prompt with specific theme
        When I run "prompt generate -T dark"
        Then the exit code should be 0
        And the output should contain "POSITIVE PROMPT"
        And the output should contain "NEGATIVE PROMPT"

    @REQ-PROMPT-001
    Scenario: Generate prompt with specific template
        When I run "prompt generate -T dark -t cyberpunk.prompt"
        Then the exit code should be 0
        And the output should contain "POSITIVE PROMPT"
        And the output should contain "cyberpunk"

    @REQ-PROMPT-002
    Scenario: Generate raw output for scripting
        When I run "prompt generate -T dark --raw"
        Then the exit code should be 0
        And the output should not contain "POSITIVE PROMPT"
        And the output should contain "---"

    @REQ-PROMPT-002
    Scenario: Generate positive prompt only
        When I run "prompt generate -T light --positive-only"
        Then the exit code should be 0
        And the output should not contain "NEGATIVE PROMPT"
        And the output should not contain "---"

    @REQ-PROMPT-002
    Scenario: Generate negative prompt only
        When I run "prompt generate -T light --negative-only"
        Then the exit code should be 0
        And the output should not contain "POSITIVE PROMPT"

    @REQ-PROMPT-003
    Scenario: Generate with specific seed
        When I run "prompt generate -T dark -s 12345"
        And I run "prompt generate -T dark -s 12345" again
        Then both outputs should be identical

    @REQ-PROMPT-003
    Scenario: Different seeds produce different prompts
        When I run "prompt generate -T dark -s 12345"
        And I run "prompt generate -T dark -s 67890"
        Then the outputs should be different

    Scenario: Default theme when not specified
        When I run "prompt generate" without theme flag
        Then the exit code should be 0
        And a prompt should be generated

    Scenario: Invalid theme shows error
        When I run "prompt generate -T nonexistent"
        Then the exit code should be non-zero
        Or a warning should be shown

    Scenario: Show metadata with formatted output
        When I run "prompt generate -T dark -t noir.prompt"
        Then the output should contain "Theme: dark"
        And the output should contain "Template: noir.prompt"
        And the output should contain "Seed:"

    Scenario: Interactive command exists
        When I request help for "prompt interactive"
        Then the help should mention "interactive"
        And the help should mention "clipboard"
