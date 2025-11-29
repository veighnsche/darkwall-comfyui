# TEAM_004: Polish & Integration

## Phase 6 Implementation

### Goal
- Desktop notifications on wallpaper change
- JSON status output for waybar/polybar
- Additional wallpaper setters (hyprpaper)

### Tasks
1. [x] Add notifications module with desktop notification support
2. [x] Add `[notifications]` section to config.py
3. [x] Integrate notifications into generate.py
4. [x] Implement `darkwall status --json` command
5. [x] Add hyprpaper setter
6. [x] Run all tests and verify (96 passed, 2 skipped)

### Changes Made
- Created `notifications.py` module with:
  - `NotificationConfig` dataclass for notification settings
  - `NotificationSender` class using `notify-send` (libnotify)
  - Methods: `notify_wallpaper_changed()`, `notify_generation_started()`, `notify_error()`
- Added `[notifications]` section to `validate_toml_structure()` in config.py
- Added `notifications` field to `ConfigV2` dataclass
- Added notifications parsing to `Config.load_v2()`
- Integrated notifications into `generate_for_monitor()` in generate.py
- Updated `status.py` to:
  - Use `ConfigV2` instead of old `Config`
  - Support `json_output` parameter for JSON output
  - Added `get_status_json()` function for waybar/polybar
  - Include schedule, monitors, comfyui status in output
- Added `HyprpaperSetter` to wallpaper/setters.py
- Exported `NotificationConfig`, `NotificationSender` from `__init__.py`

### Files Modified
- `src/darkwall_comfyui/notifications.py` - NEW: Desktop notifications module
- `src/darkwall_comfyui/config.py` - Added notifications section parsing
- `src/darkwall_comfyui/commands/generate.py` - Integrated notifications
- `src/darkwall_comfyui/commands/status.py` - Updated for ConfigV2 + JSON output
- `src/darkwall_comfyui/wallpaper/setters.py` - Added HyprpaperSetter
- `src/darkwall_comfyui/__init__.py` - Export notification classes
- `TODO.md` - Marked Phase 6 complete

### Config Example
```toml
[notifications]
enabled = true
show_preview = true
timeout_ms = 5000
urgency = "normal"
```

## Handoff
- [x] Code compiles (`nix build`)
- [x] Tests pass (`pytest tests/`) - 96 passed, 2 skipped
- [x] Team file complete
