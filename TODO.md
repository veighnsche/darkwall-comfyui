# DarkWall ComfyUI - Development Roadmap

> **Development Mode**: BDD (Behavior-Driven Development) with `pytest-bdd`
> **Requirements**: See `docs/requirements/REQUIREMENTS.md` (66 frozen requirements)
> **Questions**: See `docs/requirements/QUESTIONNAIRE.md` (all answered)

---

## 🎯 PHASE 1: BDD Foundation (CURRENT)

### 1.1 ✅ All Behavior Questions Answered
See `docs/requirements/QUESTIONNAIRE.md` — all 18 BDD questions now have decisions.

### 1.2 ✅ Step Definitions Complete
All step definitions written and passing (36 tests, 2 skipped for planned features):

| Feature File | Status | Requirements |
|--------------|--------|--------------|
| `monitor_detection.feature` | ✅ Done | REQ-MONITOR-001, 002 |
| `monitor_config.feature` | ✅ Done | REQ-MONITOR-003, 004, 007 |
| `workflow_system.feature` | ✅ Done | REQ-WORKFLOW-001, 002, 003 |
| `theme_system.feature` | ✅ Done | REQ-THEME-001, 004, 005 |
| `scheduling.feature` | ✅ Done | REQ-SCHED-002, 003, 004 |
| `config_breaking_changes.feature` | ✅ Done | REQ-CONFIG-005 |
| `generation.feature` | ✅ Done | REQ-CORE-002, REQ-MONITOR-008 |
| `cli_status.feature` | ✅ Done | REQ-COMFY-005, SCHED-004, MISC-003 |

### 1.3 Run BDD Tests
```bash
nix develop
pytest tests/step_definitions/ -v
pytest -m "REQ-MONITOR-001"  # Run specific requirement
```

---

## ✅ PHASE 2: Config Breaking Changes (COMPLETE)

**Goal**: Migrate from old index-based config to new compositor-name-based config.

### 2.1 ✅ Deprecate Old Config Keys (REQ-CONFIG-005)
All deprecated keys now error with clear migration instructions:
- [x] `monitors.count` → auto-detect from compositor
- [x] `monitors.pattern` → use `[monitors.{name}]` sections
- [x] `monitors.workflows` (array) → per-monitor config
- [x] `monitors.templates` (array) → per-monitor config
- [x] `monitors.paths` (array) → per-monitor config
- [x] `monitors.backup_pattern` → per-monitor config
- [x] `monitors.names` → use section names directly

### 2.2 New Config Format
```toml
# OLD (deprecated - will ERROR)
[monitors]
count = 3
workflows = ["a.json", "b.json", "c.json"]

# NEW (required)
[monitors.DP-1]
workflow = "2327x1309"

[monitors.HDMI-A-2]
workflow = "1920x1080"

[monitors.HDMI-A-1]
workflow = "2327x1309"
```

### 2.3 ✅ Implementation Complete
- [x] Added `check_deprecated_keys()` to config.py
- [x] Added `DEPRECATED_KEYS` dict with migration messages
- [x] Errors include full migration instructions
- [x] BDD: `config_breaking_changes.feature` passes (4/4)

---

## 🎯 PHASE 3: Monitor Auto-Detection (IN PROGRESS)

**Goal**: Auto-detect monitors from compositor instead of manual count.

### 3.1 ✅ Monitor Detection (REQ-MONITOR-001)
- [x] Created `monitor_detection.py` module
- [x] Implemented niri detection (`niri msg outputs`)
- [x] Parse output to get monitor names + resolutions
- [x] Added error handling (REQ-MONITOR-010)
- [x] Added caching (REQ-MONITOR-011)
- [ ] TODO: Add sway support (`swaymsg -t get_outputs`)
- [ ] TODO: Add hyprland support (`hyprctl monitors`)

### 3.2 ✅ Compositor Names (REQ-MONITOR-002)
- [x] Use `DP-1`, `HDMI-A-1` instead of indices
- [x] Added `NamedStateManager` for name-based rotation
- [x] Added `MonitorsConfig` and `PerMonitorConfig` dataclasses
- [x] Exported new classes from `__init__.py`

### 3.3 User's Monitors (Reference)
| Output | Resolution | Workflow |
|--------|------------|----------|
| `DP-1` | 2327x1309 | `2327x1309.json` |
| `HDMI-A-2` | 1920x1080 | `1920x1080.json` |
| `HDMI-A-1` | 2327x1309 | `2327x1309.json` |

### 3.4 Implementation Tasks
- [ ] BDD: `monitor_detection.feature` passes
- [ ] BDD: `monitor_config.feature` passes
- [ ] Create default workflows for user's resolutions

---

## 🎯 PHASE 4: Workflow System Refactor

**Goal**: Workflow ID = filename, optional prompt filtering.

### 4.1 Workflow ID = Filename (REQ-WORKFLOW-001)
- [ ] Remove any workflow ID mapping tables
- [ ] `workflow = "2327x1309"` → loads `workflows/2327x1309.json`
- [ ] Validate workflow exists on config load

### 4.2 Workflow → Prompts (REQ-WORKFLOW-002)
- [ ] Default: all prompts available to all workflows
- [ ] Optional explicit config:
  ```toml
  [workflows.2327x1309]
  prompts = ["cinematic.prompt", "nature.prompt"]
  ```
- [ ] Add `WorkflowConfig` dataclass

### 4.3 Implementation Tasks
- [ ] BDD: `workflow_system.feature` passes
- [ ] Update config.py with WorkflowConfig
- [ ] Update generate.py flow

---

## 🎯 PHASE 5: Theme Scheduling

**Goal**: Automatic SFW/NSFW switching based on solar position.

### 5.1 Dependencies
- [ ] Add `astral` to dependencies (flake.nix, pyproject.toml)

### 5.2 Solar Scheduling (REQ-SCHED-002)
- [ ] Create `schedule.py` module
- [ ] Calculate sunrise/sunset with astral
- [ ] Support manual time override
- [ ] Manual times take priority over solar

### 5.3 Probability Blend (REQ-SCHED-003)
- [ ] Implement blend during transitions
- [ ] 30-minute blend window (configurable)
- [ ] Linear probability interpolation

### 5.4 Status Display (REQ-SCHED-004)
- [ ] 24-hour schedule table in `darkwall status`
- [ ] JSON output for waybar (`--json`)

### 5.5 Config Example
```toml
[schedule]
latitude = 52.52
longitude = 13.405
day_theme = "default"
night_theme = "nsfw"
blend_duration_minutes = 30
```

### 5.6 Implementation Tasks
- [ ] BDD: `scheduling.feature` passes
- [ ] BDD: `cli_status.feature` passes
- [ ] Create nsfw theme directory with example content

---

## 🎯 PHASE 6: Polish & Integration

### 6.1 Notifications (REQ-MISC-001)
- [ ] Optional desktop notifications on wallpaper change
- [ ] Config: `notifications.enabled = false`

### 6.2 JSON Status (REQ-MISC-003)
- [ ] `darkwall status --json` for waybar/polybar
- [ ] Include: theme, schedule, monitors, comfyui status

### 6.3 Additional Wallpaper Setters (TODO)
Low priority - current setters are sufficient:
- [ ] hyprpaper (Hyprland)
- [ ] wpaperd (Wayland daemon)
- [ ] wallutils (cross-platform)

---

## ✅ Completed (Archive)

<details>
<summary>Click to expand completed items</summary>

### Core Infrastructure ✅
- Project structure, Nix flake, CLI, logging

### ComfyUI Integration ✅
- Workflow loading, API client, prompt injection, polling, health checks

### Multi-Monitor Support ✅ (old index-based)
- MonitorConfig, rotation state, wallpaper commands, swaybg management

### Configuration System ✅
- TOML config, dataclasses, env overrides, auto-init

### Prompt Generation ✅
- Template system, wildcards, variants, negative prompts

### Theme System ✅ (basic)
- Theme directories, theme-aware loading, legacy fallback

### Testing ✅
- Unit tests, integration tests, mocked ComfyUI

### Documentation ✅
- Man page, troubleshooting, API docs, config reference

### NixOS Integration ✅
- Flake package, NixOS module, Home Manager module

</details>

---

## Quick Reference

### Run Tests
```bash
nix develop
pytest                              # All tests
pytest tests/step_definitions/      # BDD only
pytest -m "REQ-MONITOR-001"         # Specific requirement
pytest --collect-only               # List scenarios
```

### Key Files
| File | Purpose |
|------|---------|
| `docs/requirements/REQUIREMENTS.md` | 56 frozen requirements |
| `docs/requirements/QUESTIONNAIRE.md` | Answered design questions |
| `docs/requirements/TRACEABILITY.md` | Requirement → code mapping |
| `tests/features/*.feature` | BDD scenarios |
| `tests/step_definitions/*.py` | Step implementations |

---

*Last Updated: 2025-11-29*
