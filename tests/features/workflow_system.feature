@REQ-WORKFLOW-001 @REQ-WORKFLOW-002 @REQ-WORKFLOW-003
Feature: Workflow System
    As a user
    I want workflows to be identified by filename
    So that I don't need to maintain a separate mapping table

    @REQ-WORKFLOW-001
    Scenario: Workflow ID equals filename
        Given a workflow file "workflows/2327x1309.json"
        When I reference workflow "2327x1309" in config
        Then it should load "workflows/2327x1309.json"

    @REQ-WORKFLOW-001
    Scenario: Workflow ID without .json extension
        Given a workflow file "workflows/ultrawide.json"
        When I configure monitor with workflow = "ultrawide"
        Then it should resolve to "workflows/ultrawide.json"

    @REQ-WORKFLOW-002
    Scenario: Default - all prompts available to workflow
        Given a theme with prompts:
            | name             |
            | default.prompt   |
            | cinematic.prompt |
            | minimal.prompt   |
        And no explicit workflow prompts config
        When I generate for workflow "2327x1309"
        Then any of the 3 prompts may be selected

    @REQ-WORKFLOW-002
    Scenario: Explicit prompts restrict selection
        Given a config with:
            """
            [workflows.2327x1309]
            prompts = ["cinematic.prompt", "minimal.prompt"]
            """
        And a theme with prompts:
            | name             |
            | default.prompt   |
            | cinematic.prompt |
            | minimal.prompt   |
        When I generate for workflow "2327x1309"
        Then only "cinematic.prompt" or "minimal.prompt" may be selected
        And "default.prompt" should never be selected

    @REQ-WORKFLOW-003
    Scenario: Random template selection is seeded
        Given workflow "2327x1309" with 3 available prompts
        And time slot seed is 12345
        And monitor is "DP-1"
        When I generate a prompt
        Then the same prompt is selected on repeated runs
        And different time slots select different prompts

    # REQ-WORKFLOW-004: Missing workflow → Error with full path that was tried
    # REQ-WORKFLOW-005: JSON validation → Just check valid JSON, let ComfyUI validate
