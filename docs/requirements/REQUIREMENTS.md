# DarkWall ComfyUI — Behavior Requirements Specification

> **Purpose**: Single source of truth for all frozen, planned, and deferred behaviors.
> **TDD**: Each requirement maps to test file(s) for verification.
> **Traceability**: See `TRACEABILITY.md` for code location mapping.

---

## Requirement ID Convention

| Prefix | Category |
|--------|----------|
| `REQ-CORE-xxx` | Core generation pipeline |
| `REQ-COMFY-xxx` | ComfyUI integration |
| `REQ-PROMPT-xxx` | Prompt generation & templates |
| `REQ-WORKFLOW-xxx` | Workflow system |
| `REQ-THEME-xxx` | Theme system |
| `REQ-MONITOR-xxx` | Multi-monitor support |
| `REQ-SCHED-xxx` | Scheduling & time-based features |
| `REQ-WALL-xxx` | Wallpaper setter integration |
| `REQ-HIST-xxx` | History & gallery |
| `REQ-CLI-xxx` | CLI interface |
| `REQ-CONFIG-xxx` | Configuration system |
| `REQ-MISC-xxx` | Miscellaneous features |
| `REQ-NIX-xxx` | NixOS/Nix integration |

## Status Legend

- ✅ **FROZEN** — Implemented and tested; behavior locked
- 🔧 **IMPLEMENTED** — Works but needs more tests
- 📋 **PLANNED** — Designed but not yet implemented
- ❓ **OPEN** — Requires user decision (see QUESTIONNAIRE.md)

---

# 1. Core Generation Pipeline

## REQ-CORE-001: Single-Shot Execution ✅ FROZEN

**Behavior**: The tool executes as a single-shot command that generates one wallpaper and exits. No internal scheduling or loops.

**Rationale**: External schedulers (systemd timers) handle periodicity.

**Test**: `tests/test_commands.py`

---

## REQ-CORE-002: Generation Flow ✅ FROZEN

**Behavior**: Generation follows this exact sequence:
1. Load configuration
2. Select monitor (rotation or explicit)
3. Generate deterministic prompt from template
4. Load workflow JSON
5. Inject prompt into workflow via placeholders
6. Submit to ComfyUI `/prompt` endpoint
7. Poll `/history/{prompt_id}` until completion or timeout
8. Download image via `/view` endpoint
9. Save to output path
10. Optionally save to history
11. Execute wallpaper setter command

**Test**: `tests/test_integration.py`

---

## REQ-CORE-003: Exit Codes ✅ FROZEN

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Configuration error |
| 2 | Network error (ComfyUI unreachable) |
| 3 | Generation error (ComfyUI failed) |
| 4 | Timeout error |
| 5 | Filesystem error |

**Test**: `tests/test_commands.py`

---

# 2. ComfyUI Integration

## REQ-COMFY-001: Workflow Loading ✅ FROZEN

**Behavior**: Workflow JSON files are loaded from paths relative to the config directory (`~/.config/darkwall-comfyui/workflows/`).

**Test**: `tests/test_comfy_client.py`

---

## REQ-COMFY-002: Placeholder-Based Prompt Injection ✅ FROZEN

**Behavior**: Prompts are injected via exact placeholder matching:
- `__POSITIVE_PROMPT__` — replaced with generated positive prompt
- `__NEGATIVE_PROMPT__` — replaced with generated negative prompt

**Breaking Change**: Workflows MUST contain these placeholders. No heuristic detection.

**Error**: Clear error message with migration instructions when placeholders missing.

**Test**: `tests/test_comfy_client.py::test_prompt_injection`

---

## REQ-COMFY-003: Polling with Timeout ✅ FROZEN

**Behavior**: Poll `/history/{prompt_id}` every `poll_interval` seconds (default: 5) until:
- Generation completes, OR
- `timeout` seconds elapsed (default: 300)

**Error**: Timeout error (exit code 4) with elapsed time in message.

**Test**: `tests/test_comfy_client.py`

---

## REQ-COMFY-004: Retry with Exponential Backoff ✅ FROZEN

**Behavior**: Network failures retry with exponential backoff (2s, 4s, 8s).
- Retries on: connection errors, timeouts, 5xx responses
- Uses connection pooling (10 connections, 20 max per host)

**Test**: `tests/test_comfy_client.py`

---

## REQ-COMFY-005: Health Check ✅ FROZEN

**Behavior**: `status` command checks ComfyUI connectivity and reports:
- Response time
- Device info (GPU, VRAM)
- Queue status
- Current rotation position

**Test**: `tests/test_commands.py::test_status`

---

## REQ-COMFY-006: Queue Position Reporting ✅ FROZEN

**Behavior**: When ComfyUI queue is not empty, report queue position:
1. Log INFO: "Queued at position N"
2. Continue polling until generation starts
3. DO NOT error on queue full

**Rationale**: ComfyUI handles queueing internally; just report position.

**Test**: `tests/test_comfy_client.py::test_queue_position`

---

# 3. Prompt Generation

## REQ-PROMPT-001: Template-Based Prompts ✅ FROZEN

**Behavior**: Prompts are generated from `.prompt` template files, NOT hard-coded pillar format.

**Template location**: `~/.config/darkwall-comfyui/themes/{theme}/prompts/`

**Test**: `tests/test_prompt_generator.py`

---

## REQ-PROMPT-002: Wildcard Syntax ✅ FROZEN

**Behavior**: `__path/to/atom__` is replaced with a random line from `atoms/path/to/atom.txt`.

**Example**: `__subjects/nature__` → random line from `atoms/subjects/nature.txt`

**Test**: `tests/test_prompt_generator.py::test_wildcard_resolution`

---

## REQ-PROMPT-003: Variant Syntax ✅ FROZEN

**Behavior**: `{a|b|c}` is replaced with random choice from options.

**Weighted**: `{0.8::a|0.2::b}` — weighted random selection.

**Test**: `tests/test_prompt_generator.py::test_variant_resolution`

---

## REQ-PROMPT-004: Negative Prompt Section ✅ FROZEN

**Behavior**: Templates support `---negative---` separator.
- Content before separator = positive prompt
- Content after separator = negative prompt

**Test**: `tests/test_prompt_generator.py::test_negative_prompts`

---

## REQ-PROMPT-005: Deterministic Seeding ✅ FROZEN

**Behavior**: Same time slot + monitor index = same prompt.

**Algorithm**:
1. Calculate time slot: `floor(current_minutes / slot_minutes)`
2. Create slot ID: `YYYY-MM-DD-HH-slot_number-monitor_index`
3. MD5 hash → first 8 hex chars → integer seed
4. Use seed for all random selections in that generation

**Config**: `time_slot_minutes` (default: 30), `use_monitor_seed` (default: true)

**Test**: `tests/test_prompt_generator.py::test_determinism`

---

## REQ-PROMPT-006: Prompt Preview CLI ✅ FROZEN

**Behavior**: `darkwall prompt preview [--seed N] [--template FILE]` shows generated prompt without running ComfyUI.

**Test**: `tests/test_commands.py::test_prompt_preview`

---

## REQ-PROMPT-007: Prompt List CLI ✅ FROZEN

**Behavior**: `darkwall prompt list [--atoms]` lists available templates (and optionally atom files).

**Test**: `tests/test_commands.py::test_prompt_list`

---

# 4. Workflow System

## REQ-WORKFLOW-001: Workflow ID = Filename ✅ FROZEN

**Behavior**: Workflow identifiers are the filename without `.json` extension.

**Example**: `workflows/2327x1309.json` → workflow ID is `"2327x1309"`

**No custom IDs**: No separate mapping table; filename IS the ID.

**Test**: `tests/test_config.py`

---

## REQ-WORKFLOW-002: Workflow → Prompts Relationship ✅ FROZEN

**Behavior**: Two modes for associating prompts with workflows:

**Default (C)**: All prompts in theme available to all workflows
```toml
# No explicit prompts config needed
# Any .prompt file in themes/{theme}/prompts/ can be used
```

**Explicit (B)**: Workflow declares specific prompts
```toml
[workflows.2327x1309]
prompts = ["cinematic.prompt", "nature.prompt"]
# Only these templates will be used for this workflow
```

**Priority**: If `[workflows.{name}]` section exists with `prompts`, use it. Otherwise, all prompts available.

**Test**: `tests/test_config.py::test_workflow_prompts`

---

## REQ-WORKFLOW-003: Random Template Selection ✅ FROZEN

**Behavior**: When multiple prompts are available for a workflow, selection is random (seeded).

**Seed**: Based on time slot + monitor name (deterministic per generation).

**Test**: `tests/test_prompt_generator.py::test_template_selection`

---

## REQ-WORKFLOW-004: Missing Workflow Error ✅ FROZEN

**Behavior**: When a workflow file doesn't exist:
1. Error with full path that was tried (e.g., "Workflow not found: /home/user/.config/darkwall-comfyui/workflows/2327x1309.json")
2. Exit with code 1

**NO listing available workflows.** Keep error message simple and direct.

**Test**: `tests/test_comfy_client.py::test_missing_workflow`

---

## REQ-WORKFLOW-005: Workflow JSON Validation ✅ FROZEN

**Behavior**: Workflow JSON validation is minimal:
1. Check it's valid JSON (parse succeeds)
2. Let ComfyUI validate the workflow structure
3. Show ComfyUI's error message if workflow is invalid

**Rationale**: ComfyUI knows its own schema best; don't duplicate validation logic.

**Test**: `tests/test_comfy_client.py::test_invalid_workflow_json`

---

# 5. Theme System

## REQ-THEME-001: Theme Directory Structure ✅ FROZEN

**Behavior**: Themes are self-contained directories under `~/.config/darkwall-comfyui/themes/`:

```
themes/
├── default/
│   ├── atoms/
│   │   ├── subjects.txt
│   │   ├── environments.txt
│   │   └── ...
│   └── prompts/
│       ├── default.prompt
│       └── cinematic.prompt
└── nsfw/
    ├── atoms/
    └── prompts/
```

**Test**: `tests/test_config.py::test_theme_loading`

---

## REQ-THEME-002: Theme Config Section ✅ FROZEN

**Behavior**: Themes defined in `config.toml` with workflow_prefix for model selection:

```toml
[themes.light]
workflow_prefix = "wan2_5"  # Uses wan2_5-{resolution} workflows
default_template = "default.prompt"

[themes.dark]
workflow_prefix = "z-image-turbo"  # Uses z-image-turbo-{resolution} workflows
default_template = "default.prompt"

[themes.uncannyvalley]
workflow_prefix = "uncannyvalley"  # Uses uncannyvalley-{resolution} workflows
default_template = "default.prompt"
```

**TEAM_006**: `workflow_prefix` determines which ComfyUI model/workflow to use.
The full workflow is computed as: `{workflow_prefix}-{monitor.resolution}`

**Test**: `tests/test_config.py`

---

## REQ-THEME-003: Legacy Fallback ✅ FROZEN

**Behavior**: If no `[themes]` section exists, fall back to flat `atoms/` and `prompts/` directories for backwards compatibility.

**Test**: `tests/test_config.py::test_legacy_fallback`

---

## REQ-THEME-004: Global Theme Only ✅ FROZEN

**Behavior**: All monitors use the same theme. No per-monitor theme overrides.

**Rationale**: Simplicity. Theme switching is time-based via scheduling, not per-monitor.

**Test**: `tests/test_config.py`

---

## REQ-THEME-005: Theme Fallback on Missing ✅ FROZEN

**Behavior**: When a configured theme doesn't exist:
1. Log a WARNING with the missing theme name
2. Fall back to "default" theme
3. Continue operation (do not error)

**Test**: `tests/test_config.py::test_theme_fallback`

---

## REQ-THEME-006: Default Theme Auto-Creation ✅ FROZEN

**Behavior**: When "default" fallback theme also doesn't exist:
1. Create empty default theme directory structure
2. Log INFO: "Created default theme directory, see config folder for defaults"
3. Continue operation with empty prompts (may error later if no prompts available)

**Rationale**: Self-healing; point user to packaged defaults.

**Test**: `tests/test_config.py::test_default_theme_creation`

---

## REQ-THEME-007: Init Creates Theme Structure ✅ FROZEN

**Behavior**: `darkwall init` creates full theme directory structure with examples:

```
themes/
└── default/
    ├── atoms/
    │   ├── subjects.txt (with examples)
    │   ├── environments.txt
    │   └── ...
    └── prompts/
        ├── default.prompt
        └── cinematic.prompt
```

**Content**: Actual example atoms and prompts, not empty files.

**Test**: `tests/test_config.py::test_init_theme_structure`

---

# 5. Multi-Monitor Support

## REQ-MONITOR-001: Auto-Detection via Compositor ✅ FROZEN

**Behavior**: Monitors are auto-detected from the compositor, not manually configured.

**Primary support**: niri (`niri msg outputs`)

**TODO**: Add support for sway (`swaymsg -t get_outputs`), hyprland (`hyprctl monitors`)

**Test**: `tests/test_monitor_detection.py`

---

## REQ-MONITOR-002: Compositor Names as Identifiers ✅ FROZEN

**Behavior**: Monitors are identified by compositor output names (e.g., `DP-1`, `HDMI-A-1`), NOT by index.

**User's Setup** (reference):
| Output | Model | Resolution | Logical Size |
|--------|-------|------------|--------------|
| `DP-1` | HP OMEN 27 | 2560x1440 | 2327x1309 |
| `HDMI-A-2` | LG IPS FULLHD | 1920x1080 | 1920x1080 |
| `HDMI-A-1` | LG Ultra HD | 2560x1440 | 2327x1309 |

**Test**: `tests/test_config.py`

---

## REQ-MONITOR-003: Inline Monitor Config Sections ✅ FROZEN

**Behavior**: Each monitor is configured via `[monitors.{output_name}]` sections:

```toml
[monitors.DP-1]
resolution = "2327x1309"  # Used with theme.workflow_prefix
output = "~/Pictures/wallpapers/monitor_DP-1.png"
command = "swaybg"

[monitors.HDMI-A-2]
resolution = "1920x1080"
output = "~/Pictures/wallpapers/monitor_HDMI-A-2.png"

[monitors.HDMI-A-1]
resolution = "2327x1309"
output = "~/Pictures/wallpapers/monitor_HDMI-A-1.png"
```

**TEAM_006**: `resolution` is combined with `theme.workflow_prefix` to select workflow:
- Theme `dark` with `workflow_prefix = "z-image-turbo"` + monitor `resolution = "2327x1309"`
- → Uses workflow `z-image-turbo-2327x1309.json`

**Test**: `tests/test_config.py`

---

## REQ-MONITOR-004: Error on Unconfigured Monitor ✅ FROZEN

**Behavior**: If a connected monitor has no `[monitors.{name}]` section:
1. Log ERROR with monitor name
2. Exit with code 1 (configuration error)

**Rationale**: Explicit config prevents accidental wallpaper mismatches.

**Test**: `tests/test_config.py::test_unconfigured_monitor_error`

---

## REQ-MONITOR-005: Rotation State Persistence ✅ FROZEN

**Behavior**: State file (`~/.local/state/darkwall-comfyui/state.json`) tracks:
- Current monitor name (not index)
- Last generation timestamps per monitor

**Commands**:
- `generate` — generates for next monitor in rotation
- `generate-all` — generates for all monitors
- `reset` — resets rotation

**Test**: `tests/test_state.py`

---

## REQ-MONITOR-006: Per-Monitor Output Paths ✅ FROZEN

**Behavior**: Output paths derived from monitor name:

```toml
[monitors.DP-1]
output = "~/Pictures/wallpapers/DP-1.png"
```

**Default pattern**: `~/Pictures/wallpapers/{monitor_name}.png`

**Test**: `tests/test_config.py`

---

## REQ-MONITOR-007: Per-Monitor Workflows ✅ FROZEN

**Behavior**: Each monitor specifies its workflow (by filename without .json):

```toml
[monitors.DP-1]
workflow = "2327x1309"  # Uses workflows/2327x1309.json
```

**Test**: `tests/test_config.py`

---

## REQ-MONITOR-008: Independent Template Selection ✅ FROZEN

**Behavior**: When two monitors share a workflow, each selects templates independently.

**Implementation**: Seed offset based on monitor name hash.

**Rationale**: Same time slot should NOT produce identical wallpapers on all monitors.

**Test**: `tests/test_prompt_generator.py::test_monitor_independence`

---

## REQ-MONITOR-009: CLI Override ✅ FROZEN

**Behavior**:
- `--workflow FILE` — override workflow for single generation
- `--template FILE` — override template for single generation
- `--monitor NAME` — generate for specific monitor (skip rotation)

**Test**: `tests/test_commands.py`

---

## REQ-MONITOR-010: Compositor Error Handling ✅ FROZEN

**Behavior**: When compositor is not running or detection fails:
1. Error with clear message (e.g., "Could not detect monitors: niri not running")
2. Show actual error from detection command (permission denied, command not found, etc.)
3. Exit with code 1

**NO fallback to manual config.** User must fix the issue.

**Test**: `tests/test_monitor_detection.py`

---

## REQ-MONITOR-011: Monitor Detection Caching ✅ FROZEN

**Behavior**: Cache detected monitors until monitor change detected.

**Cache invalidation**: When monitor connects/disconnects (detected via compositor).

**Rationale**: Avoid unnecessary compositor calls on every generation.

**Test**: `tests/test_monitor_detection.py`

---

## REQ-MONITOR-012: Unconfigured Monitor Handling ✅ FROZEN

**Behavior**: When a connected monitor has no config section:
1. Log WARNING: "Monitor {name} has no configuration, skipping"
2. Continue with configured monitors only

**Default behavior**: Skip unconfigured monitors with warning (not error).

**Test**: `tests/test_monitor_detection.py`

---

## REQ-MONITOR-013: Disconnected Monitor Handling ✅ FROZEN

**Behavior**: When a configured monitor is disconnected:
1. Log WARNING: "Configured monitor {name} is not connected, skipping"
2. Continue with connected monitors only

**Test**: `tests/test_monitor_detection.py`

---

# 6. Scheduling & Time-Based Features

## REQ-SCHED-001: Time Slot Determinism ✅ FROZEN

**Behavior**: `prompt.time_slot_minutes` (1-1440) defines how often prompts change.

**Default**: 30 minutes → 48 unique prompts per day per monitor.

**Test**: `tests/test_prompt_generator.py`

---

## REQ-SCHED-002: Sundown/Sunrise Theme Switching 📋 PLANNED

**Behavior**: Automatically switch themes based on solar position:
- Day: use `day_theme` (default: "default")
- Night: use `night_theme` (default: "nsfw")

**Config** (solar-based):
```toml
[schedule]
latitude = 52.52
longitude = 13.405
day_theme = "default"
night_theme = "nsfw"
```

**Config** (manual override):
```toml
[schedule]
nsfw_start = "22:00"
nsfw_end = "06:00"
day_theme = "default"
night_theme = "nsfw"
```

**Priority**: Manual times override solar calculation if both specified.

**Timezone**: Manual times use system local timezone.

**Error handling**: If `astral` fails to calculate sunset, error with message (no fallback).

**DST handling**: Astral library handles daylight saving time automatically.

**Dependency**: `astral` Python library (confirmed)

**Test**: `tests/test_schedule.py`

---

## REQ-SCHED-003: Probability Blend Transitions 📋 PLANNED

**Behavior**: During transition periods (around sunset/sunrise), themes blend via probability:

| Time relative to sunset | SFW probability | NSFW probability |
|-------------------------|-----------------|------------------|
| -30 min (before) | 80% | 20% |
| 0 (at sunset) | 50% | 50% |
| +30 min (after) | 20% | 80% |

**Config**:
```toml
[schedule]
blend_duration_minutes = 30  # default, configurable
```

**Configurable**: Yes, with sensible default of 30 minutes.

**Test**: `tests/test_schedule.py::test_blend_probability`

---

## REQ-SCHED-004: 24-Hour Schedule Status 📋 PLANNED

**Behavior**: `darkwall status` shows full 24-hour schedule as table:

```
Theme Schedule (next 24h):
TIME        THEME     PROBABILITY
06:00       default   100%
18:30       (blend)   SFW 70% / NSFW 30%
19:00       nsfw      100%
```

**Flag**: `--json` outputs machine-readable format for waybar/polybar integration.

**Test**: `tests/test_commands.py::test_status_schedule`

---

# 7. Wallpaper Setter Integration

## REQ-WALL-001: Built-in Setters ✅ FROZEN

**Behavior**: Supported wallpaper setters:
- `swaybg` (default) — Wayland
- `swww` — Wayland with animations
- `feh` — X11
- `nitrogen` — X11

**Config**: `monitors.command = "swaybg"`

**Test**: `tests/test_wallpaper.py`

---

## REQ-WALL-002: Custom Commands ✅ FROZEN

**Behavior**: `command = "custom:<command>"` supports placeholders:
- `{path}` — full path to wallpaper image
- `{index}` — monitor index (0-based)
- `{monitor}` — monitor name (if available)

**Example**: `custom:swww img {path} --outputs {monitor}`

**Test**: `tests/test_wallpaper.py`

---

## REQ-WALL-003: Swaybg Process Management ✅ FROZEN

**Behavior**: Before setting wallpaper with swaybg:
1. Kill existing swaybg process for that monitor
2. Start swaybg as background daemon

**Rationale**: Avoid process conflicts with NixOS systemd services.

**Test**: `tests/test_wallpaper.py`

---

## REQ-WALL-004: Additional Setters 📋 PLANNED

**Status**: Low priority — current setters are sufficient.

Candidates:
- `hyprpaper` (Hyprland)
- `wpaperd` (Wayland daemon)
- `wallutils` (cross-platform)

---

## REQ-WALL-005: Setter Failure After Save ✅ FROZEN

**Behavior**: When wallpaper image is saved but setter command fails:
1. Keep the saved image (do not rollback)
2. Log ERROR with command output
3. Exit with code 5 (filesystem error)

**Rationale**: Image is valuable; don't delete it just because setter failed.

**Test**: `tests/test_wallpaper.py::test_setter_failure`

---

# 8. History & Gallery

## REQ-HIST-001: History Saving ✅ FROZEN

**Behavior**: When `history.enabled = true`, copy generated wallpaper to history directory with YYYY/MM structure.

**Path**: `~/Pictures/wallpapers/history/2025/01/20250128_120000_monitor_0.png`

**Test**: `tests/test_history.py`

---

## REQ-HIST-002: Gallery CLI ✅ FROZEN

**Behavior**: `darkwall gallery` subcommand:
- `list` — show recent wallpapers
- `info <path>` — show metadata
- `favorite <path>` — mark as favorite
- `delete <path>` — remove (respects favorites)
- `stats` — show history statistics
- `cleanup` — apply cleanup policy

**Test**: `tests/test_history.py`

---

## REQ-HIST-003: Cleanup Policy ✅ FROZEN

**Behavior**: Configurable retention via `[history.cleanup_policy]`:
- `max_count` — maximum wallpapers to keep
- `max_days` — delete older than N days
- `min_favorites` — always keep N favorites
- `max_size_mb` — keep history under size limit

**Test**: `tests/test_history.py`

---

## REQ-HIST-004: Favorites Protection ✅ FROZEN

**Behavior**: Favorited wallpapers (marked with `★`) are protected from:
- `delete` command (unless `--force`)
- `cleanup` automatic deletion

**Test**: `tests/test_history.py`

---

# 9. CLI Interface

## REQ-CLI-001: Command Structure ✅ FROZEN

**Commands**:
- `init` — initialize config directory
- `status` — show config and ComfyUI health
- `validate` — validate config files
- `generate` — generate for next monitor
- `generate-all` — generate for all monitors
- `reset` — reset rotation state
- `fix-permissions` — fix file permissions
- `prompt preview|list` — prompt tools
- `gallery list|info|favorite|delete|stats|cleanup` — history tools

**Test**: `tests/test_cli.py`

---

## REQ-CLI-002: Global Flags ✅ FROZEN

**Flags**:
- `--dry-run` — show what would happen, don't execute
- `--verbose` / `-v` — enable debug logging
- `--no-init` — skip auto-initialization
- `--validate-config` — validate and exit

**Test**: `tests/test_cli.py`

---

## REQ-CLI-003: Dry Run Mode ✅ FROZEN

**Behavior**: `--dry-run` shows:
- Selected monitor and template
- Generated prompt (positive and negative)
- Workflow to be used
- Output path
- Wallpaper command to be executed

**Does NOT**: Submit to ComfyUI, save files, execute commands.

**Test**: `tests/test_commands.py::test_dry_run`

---

# 10. Configuration System

## REQ-CONFIG-001: TOML Format ✅ FROZEN

**Behavior**: Configuration in `~/.config/darkwall-comfyui/config.toml`.

**Test**: `tests/test_config.py`

---

## REQ-CONFIG-002: Environment Variable Overrides ✅ FROZEN

**Behavior**: Pattern `DARKWALL_[SECTION]_[KEY]=value` overrides config.

**Examples**:
- `DARKWALL_COMFYUI_BASE_URL="http://localhost:8188"`
- `DARKWALL_MONITORS_COUNT="2"`

**Test**: `tests/test_config.py`

---

## REQ-CONFIG-003: Auto-Initialization ✅ FROZEN

**Behavior**: On first run (or `init` command):
1. Create config directory structure
2. Copy default config.toml
3. Copy default workflows
4. Copy default themes (atoms + prompts)

**Test**: `tests/test_config.py::test_init`

---

## REQ-CONFIG-004: Validation on Load ✅ FROZEN

**Behavior**: Config validation on startup checks:
- URL format validity
- Integer ranges (count: 1-10, timeout: 1-3600, etc.)
- Required placeholders in patterns
- File extension requirements (.json for workflows)

**Error**: Clear error messages with field name and expected format.

**Test**: `tests/test_config.py::test_validation`

---

## REQ-CONFIG-005: Breaking Changes — Fail Hard ✅ FROZEN

**Behavior**: When config format changes:
1. Detect deprecated/removed keys
2. ERROR with specific key name and migration instructions
3. Exit with code 1

**NO backwards compatibility hacks. NO auto-migration. BREAK THE CODE.**

**Rationale**: Prevents forever tech debt from sad attempts at compatibility.

**Test**: `tests/test_config.py::test_deprecated_keys`

---

## REQ-CONFIG-006: No Profiles ✅ FROZEN

**Behavior**: Profiles feature is explicitly NOT implemented.

**Rationale**: Themes + scheduling cover all use cases. Profiles would add redundant complexity.

---

## REQ-CONFIG-007: No Multi-Host Support ✅ FROZEN

**Behavior**: Multi-host configuration is explicitly NOT implemented.

**Rationale**: Tool runs on one host. Different hosts use different config files via NixOS.

---

# 11. Miscellaneous Features

## REQ-MISC-001: Optional Desktop Notifications 📋 PLANNED

**Behavior**: When `notifications.enabled = true`, send desktop notification on wallpaper change.

**Config**:
```toml
[notifications]
enabled = false  # default
```

**Test**: `tests/test_notifications.py`

---

## REQ-MISC-002: No Lock Screen Integration ✅ FROZEN

**Behavior**: Lock screen wallpaper is explicitly NOT managed by this tool.

**Rationale**: Separate concern; user can configure swaylock independently.

---

## REQ-MISC-003: JSON Status Output 📋 PLANNED

**Behavior**: `darkwall status --json` outputs machine-readable JSON for integration with waybar/polybar.

**Test**: `tests/test_commands.py::test_status_json`

---

# 12. NixOS Integration

## REQ-NIX-001: Flake Package ✅ FROZEN

**Behavior**: `nix build` produces CLI binary with all runtime deps.

**Wrapper**: Wallpaper setters (swww, swaybg, feh, nitrogen) available in PATH.

**Test**: Manual

---

## REQ-NIX-002: NixOS Module ✅ FROZEN

**Behavior**: System-level module in flake for NixOS configuration.

**Test**: Manual

---

## REQ-NIX-003: Home Manager Module ✅ FROZEN

**Behavior**: User-level module for home-manager integration.

**Test**: Manual

---

## REQ-NIX-004: Non-Flake Compatibility ✅ FROZEN

**Behavior**: `pkgs/darkwall-comfyui.nix` works with classic NixOS (non-flake) configs.

**Test**: Manual

---

## REQ-NIX-005: DevShell ✅ FROZEN

**Behavior**: `nix develop` provides:
- Python 3 with all deps
- pytest, black, isort, mypy
- PYTHONPATH configured

**Test**: Manual

---

# Appendix: Requirement Summary

| Category | Frozen | Implemented | Planned | Open |
|----------|--------|-------------|---------|------|
| Core | 3 | 0 | 0 | 0 |
| ComfyUI | 6 | 0 | 0 | 0 |
| Prompt | 7 | 0 | 0 | 0 |
| Workflow | 5 | 0 | 0 | 0 |
| Theme | 7 | 0 | 0 | 0 |
| Monitor | 13 | 0 | 0 | 0 |
| Scheduling | 1 | 0 | 3 | 0 |
| Wallpaper | 4 | 0 | 1 | 0 |
| History | 4 | 0 | 0 | 0 |
| CLI | 3 | 0 | 0 | 0 |
| Config | 7 | 0 | 0 | 0 |
| Misc | 1 | 0 | 2 | 0 |
| NixOS | 5 | 0 | 0 | 0 |
| **Total** | **66** | **0** | **6** | **0** |

---

## User's Monitor Setup (Reference)

Auto-detected via `niri msg outputs`:

| Output | Model | Resolution | Logical Size |
|--------|-------|------------|--------------|
| `DP-1` | HP OMEN 27 | 2560x1440 | 2327x1309 |
| `HDMI-A-2` | LG IPS FULLHD | 1920x1080 | 1920x1080 |
| `HDMI-A-1` | LG Ultra HD | 2560x1440 | 2327x1309 |

---

*Last Updated: 2025-11-29*
