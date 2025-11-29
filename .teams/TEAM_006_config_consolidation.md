# TEAM_006: Config Consolidation

**Date**: 2024-11-29
**Goal**: Eliminate backwards compatibility debt by merging ConfigV2 into Config

## Problem

Previous teams created parallel config systems:
- `Config` with `MonitorConfig` (old flat format)
- `ConfigV2` with `MonitorsConfig`/`PerMonitorConfig` (new per-monitor format)
- `Config.load()` vs `Config.load_v2()`

This violated the "Breaking Changes > Backwards Compatibility" rule.

## Solution

Merged everything into a single canonical `Config` class:

### Deleted
- `ConfigV2` class
- `MonitorConfig` class (legacy)
- `Config.load_v2()` method

### Updated
- `Config` now has all fields from `ConfigV2`:
  - `monitors: MonitorsConfig` (was `MonitorConfig`)
  - `active_monitors: List[str]`
  - `workflows: Dict[str, WorkflowConfig]`
  - `schedule: Optional[ScheduleConfig]`
  - `notifications: Optional[NotificationConfig]`
- `Config.load()` now parses per-monitor format with auto-detection
- All imports and type hints updated across codebase

### Files Modified
- `src/darkwall_comfyui/config.py` - Merged ConfigV2 into Config, deleted MonitorConfig
- `src/darkwall_comfyui/__init__.py` - Removed ConfigV2 export
- `src/darkwall_comfyui/commands/generate.py` - Use Config instead of ConfigV2
- `src/darkwall_comfyui/commands/status.py` - Use Config instead of ConfigV2
- `src/darkwall_comfyui/wallpaper/target.py` - Use MonitorsConfig instead of MonitorConfig
- `tests/conftest.py` - Use Config.load() instead of load_v2()
- `tests/test_dependency_injection.py` - Use MonitorsConfig
- `tests/test_consolidated_logic.py` - Use MonitorsConfig
- `docs/api/config.md` - Updated documentation
- `docs/requirements/TRACEABILITY.md` - Updated references
- `docs/contributing.md` - Updated example code
- `TODO.md` - Updated references

## Handoff

- [x] Code compiles
- [x] `generate-wallpaper-once status` works
- [x] All ConfigV2/MonitorConfig references updated to comments or removed
- [x] Documentation updated

## Notes

The team files (TEAM_002, TEAM_003, TEAM_004) contain historical references to ConfigV2.
These are kept as historical records of what was done at the time.
