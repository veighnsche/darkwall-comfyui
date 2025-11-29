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
| `REQ-THEME-xxx` | Theme system |
| `REQ-MONITOR-xxx` | Multi-monitor support |
| `REQ-SCHED-xxx` | Scheduling & time-based features |
| `REQ-WALL-xxx` | Wallpaper setter integration |
| `REQ-HIST-xxx` | History & gallery |
| `REQ-CLI-xxx` | CLI interface |
| `REQ-CONFIG-xxx` | Configuration system |
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

**Test**: `tests/test_commands.py::test_status`

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

# 4. Theme System

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

## REQ-THEME-002: Theme Config Section 🔧 IMPLEMENTED

**Behavior**: Themes defined in `config.toml`:

```toml
[themes.default]
atoms_dir = "themes/default/atoms"
prompts_dir = "themes/default/prompts"
default_template = "default.prompt"

[themes.nsfw]
atoms_dir = "themes/nsfw/atoms"
prompts_dir = "themes/nsfw/prompts"
default_template = "default.prompt"
```

**Test**: `tests/test_config.py`

---

## REQ-THEME-003: Legacy Fallback ✅ FROZEN

**Behavior**: If no `[themes]` section exists, fall back to flat `atoms/` and `prompts/` directories for backwards compatibility.

**Test**: `tests/test_config.py::test_legacy_fallback`

---

## REQ-THEME-004: Per-Monitor Theme Selection ❓ OPEN

**Status**: See QUESTIONNAIRE.md Q-THEME-001

---

# 5. Multi-Monitor Support

## REQ-MONITOR-001: Monitor Count Config ✅ FROZEN

**Behavior**: `monitors.count` defines number of monitors (1-10).

**Test**: `tests/test_config.py`

---

## REQ-MONITOR-002: Rotation State Persistence ✅ FROZEN

**Behavior**: State file (`~/.local/state/darkwall-comfyui/state.json`) tracks:
- Current monitor index
- Last generation timestamps per monitor

**Commands**:
- `generate` — generates for next monitor in rotation
- `generate-all` — generates for all monitors
- `reset` — resets rotation to monitor 0

**Test**: `tests/test_state.py`

---

## REQ-MONITOR-003: Per-Monitor Output Paths ✅ FROZEN

**Behavior**: Two modes:
1. **Pattern mode**: `monitors.pattern = "monitor_{index}.png"` → auto-generates paths
2. **Explicit mode**: `monitors.paths = ["path1.png", "path2.png"]` → exact paths per monitor

**Test**: `tests/test_config.py`

---

## REQ-MONITOR-004: Per-Monitor Workflows ✅ FROZEN

**Behavior**: `monitors.workflows = ["workflow1.json", "workflow2.json"]` assigns different workflows per monitor.

**Use case**: Different resolutions/aspect ratios per monitor.

**Test**: `tests/test_config.py`

---

## REQ-MONITOR-005: Per-Monitor Templates ✅ FROZEN

**Behavior**: `monitors.templates = ["cinematic.prompt", "minimal.prompt"]` assigns different prompt templates per monitor.

**Test**: `tests/test_config.py`

---

## REQ-MONITOR-006: CLI Override ✅ FROZEN

**Behavior**:
- `--workflow FILE` — override workflow for single generation
- `--template FILE` — override template for single generation
- `--monitor N` — generate for specific monitor (skip rotation)

**Test**: `tests/test_commands.py`

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

**Config**:
```toml
[schedule]
latitude = 52.52
longitude = 13.405
day_theme = "default"
night_theme = "nsfw"
```

**Alternative**: Manual time ranges:
```toml
[schedule]
nsfw_start = "22:00"
nsfw_end = "06:00"
```

**Dependency**: `astral` Python library

**Status**: Not yet implemented; see TODO.md

---

## REQ-SCHED-003: Status Shows Next Transition 📋 PLANNED

**Behavior**: `darkwall status` shows current theme and next scheduled transition time.

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

**Status**: See QUESTIONNAIRE.md Q-WALL-001 for priority.

Candidates:
- `hyprpaper` (Hyprland)
- `wpaperd` (Wayland daemon)
- `wallutils` (cross-platform)

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

# 11. NixOS Integration

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
| ComfyUI | 5 | 0 | 0 | 0 |
| Prompt | 7 | 0 | 0 | 0 |
| Theme | 3 | 1 | 0 | 1 |
| Monitor | 6 | 0 | 0 | 0 |
| Scheduling | 1 | 0 | 2 | 0 |
| Wallpaper | 3 | 0 | 1 | 0 |
| History | 4 | 0 | 0 | 0 |
| CLI | 3 | 0 | 0 | 0 |
| Config | 4 | 0 | 0 | 0 |
| NixOS | 5 | 0 | 0 | 0 |
| **Total** | **44** | **1** | **3** | **1** |

---

*Last Updated: 2025-11-29*
