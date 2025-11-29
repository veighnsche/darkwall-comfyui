@REQ-CORE-002 @REQ-MONITOR-008
Feature: Wallpaper Generation
    As a user
    I want to generate wallpapers for my monitors
    So that I have unique AI-generated dark-mode wallpapers

    @REQ-CORE-002
    Scenario: Basic generation flow
        Given a valid configuration
        And ComfyUI is running at "http://localhost:8188"
        When I run "darkwall generate"
        Then generation should complete the full pipeline
        And the pipeline should include loading configuration
        And the pipeline should include submitting to ComfyUI
        And the pipeline should include executing wallpaper setter

    @REQ-MONITOR-008
    Scenario: Independent template selection per monitor
        Given monitors "DP-1" and "HDMI-A-1" both use workflow "2327x1309"
        And the time slot is the same
        When I generate for "DP-1"
        And I generate for "HDMI-A-1"
        Then "DP-1" and "HDMI-A-1" may have different templates
        # Due to monitor name hash offset in seed

    Scenario: Generate for specific monitor
        Given 3 configured monitors
        When I run "darkwall generate --monitor HDMI-A-2"
        Then generation should happen for "HDMI-A-2" only
        And rotation state should not advance

    Scenario: Generate for all monitors
        Given 3 configured monitors
        When I run "darkwall generate-all"
        Then generation should happen for all 3 monitors
        And each monitor gets its own wallpaper

    Scenario: Dry run shows plan without executing
        Given a valid configuration
        When I run "darkwall generate --dry-run"
        Then the dry run output should show the selected monitor
        And the dry run output should show the generated prompt
        And the dry run output should show the workflow
        And no files should be created
        And no network requests should be made

    # REQ-COMFY-006: Queue full → Report queue position, continue polling
    # REQ-COMFY-004: ComfyUI errors → Retry with exponential backoff
    # REQ-WALL-005: Setter fails after save → Keep image, log error
