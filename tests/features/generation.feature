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
        Then the following steps should occur in order:
            | step                                    |
            | Load configuration                      |
            | Select next monitor in rotation         |
            | Determine current theme from schedule   |
            | Select random prompt template           |
            | Generate prompt from template           |
            | Load workflow JSON                      |
            | Inject prompt via placeholders          |
            | Submit to ComfyUI                       |
            | Poll until completion                   |
            | Download generated image                |
            | Save to output path                     |
            | Execute wallpaper setter                |

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
        Then I should see:
            | info                        |
            | Selected monitor            |
            | Selected template           |
            | Generated prompt (positive) |
            | Generated prompt (negative) |
            | Workflow to be used         |
            | Output path                 |
            | Wallpaper command           |
        And no files should be created
        And no network requests should be made

    # UNCLEAR: What if ComfyUI queue is full?
    # UNCLEAR: Should we retry on ComfyUI errors?
    # UNCLEAR: What if wallpaper setter fails but image is saved?
