# TEAM_002: Workflow System Refactor

## Phase 4 Implementation

### Goal
- Workflow ID = filename (already partially implemented in `PerMonitorConfig.get_workflow_path()`)
- Optional prompt filtering per workflow via `[workflows.{name}]` sections

### Tasks
1. [x] Review existing implementation
2. [x] Add `WorkflowConfig` dataclass for optional prompt filtering
3. [x] Add `[workflows.{name}]` section parsing to config.py
4. [x] Validate workflow file exists on config load
5. [x] Update generate_v2.py to use workflow prompts filtering
6. [x] Verify all BDD tests pass (36 passed, 2 skipped)

### Changes Made
- Added `WorkflowConfig` dataclass with `filter_prompts()` method
- Added `workflows` section to `validate_toml_structure()`
- Added `workflows` field to `ConfigV2` dataclass
- Added `get_workflow_config()` and `get_eligible_prompts_for_workflow()` methods to `ConfigV2`
- Added workflow file validation in `load_v2()` (raises ConfigError if missing)
- Added `_get_available_prompts()` and `_select_template_for_workflow()` helpers to generate_v2.py
- Updated `generate_for_monitor()` to use workflow-based template selection
- Exported `WorkflowConfig` from `__init__.py`

### Files Modified
- `src/darkwall_comfyui/config.py` - WorkflowConfig, ConfigV2 updates, validation
- `src/darkwall_comfyui/commands/generate_v2.py` - Workflow-based template selection
- `src/darkwall_comfyui/__init__.py` - Export WorkflowConfig
- `TODO.md` - Marked Phase 4 complete

### Config Example
```toml
# Optional: restrict prompts for specific workflows
[workflows.2327x1309]
prompts = ["cinematic.prompt", "nature.prompt"]

# Workflows without explicit config use all available prompts
```

## Handoff
- [x] Code compiles (`nix build`)
- [x] Tests pass (`pytest tests/step_definitions/`) - 36 passed, 2 skipped
- [x] Team file complete
