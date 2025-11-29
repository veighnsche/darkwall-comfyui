# DarkWall ComfyUI — Requirements Traceability Matrix

> **Purpose**: Map each requirement to its implementation location(s) and test(s).
> **Usage**: When modifying code, check which requirements are affected.
> **Last Updated**: 2025-11-29 (after questionnaire completion)

---

## Legend

| Column | Description |
|--------|-------------|
| **Req ID** | Requirement identifier from REQUIREMENTS.md |
| **Source Files** | Primary implementation location(s) |
| **Test Files** | Test file(s) verifying the behavior |
| **Config Keys** | Related config.toml keys (if any) |

---

# Core Generation Pipeline

| Req ID | Source Files | Test Files | Config Keys |
|--------|--------------|------------|-------------|
| REQ-CORE-001 | `commands/generate.py` | `tests/test_commands.py` | — |
| REQ-CORE-002 | `commands/generate.py` | `tests/test_integration.py` | — |
| REQ-CORE-003 | `cli.py`, `exceptions.py` | `tests/test_commands.py` | — |

---

# ComfyUI Integration

| Req ID | Source Files | Test Files | Config Keys |
|--------|--------------|------------|-------------|
| REQ-COMFY-001 | `comfy/client.py` | `tests/test_comfy_client.py` | `comfyui.workflow_path` |
| REQ-COMFY-002 | `comfy/client.py:_inject_prompts()` | `tests/test_comfy_client.py` | — |
| REQ-COMFY-003 | `comfy/client.py:poll_result()` | `tests/test_comfy_client.py` | `comfyui.timeout`, `comfyui.poll_interval` |
| REQ-COMFY-004 | `comfy/client.py:_create_session()` | `tests/test_comfy_client.py` | — |
| REQ-COMFY-005 | `comfy/client.py:health_check()`, `commands/status.py` | `tests/test_commands.py` | `comfyui.base_url` |

---

# Prompt Generation

| Req ID | Source Files | Test Files | Config Keys |
|--------|--------------|------------|-------------|
| REQ-PROMPT-001 | `prompt_generator.py:_load_template()` | `tests/test_prompt_generator.py` | `prompt.default_template` |
| REQ-PROMPT-002 | `prompt_generator.py:_resolve_wildcards()` | `tests/test_prompt_generator.py` | `prompt.atoms_dir` |
| REQ-PROMPT-003 | `prompt_generator.py:_resolve_variants()` | `tests/test_prompt_generator.py` | — |
| REQ-PROMPT-004 | `prompt_generator.py:generate_prompt_pair()` | `tests/test_prompt_generator.py` | — |
| REQ-PROMPT-005 | `prompt_generator.py:get_time_slot_seed()` | `tests/test_prompt_generator.py` | `prompt.time_slot_minutes`, `prompt.use_monitor_seed` |
| REQ-PROMPT-006 | `commands/prompt.py:preview()` | `tests/test_commands.py` | — |
| REQ-PROMPT-007 | `commands/prompt.py:list_prompts()` | `tests/test_commands.py` | — |

---

# Workflow System

| Req ID | Source Files | Test Files | Config Keys |
|--------|--------------|------------|-------------|
| REQ-WORKFLOW-001 | `config.py:WorkflowConfig` | `tests/test_config.py` | `workflows.*` |
| REQ-WORKFLOW-002 | `config.py:get_workflow_prompts()` | `tests/test_config.py` | `workflows.*.prompts` |
| REQ-WORKFLOW-003 | `prompt_generator.py:select_template()` | `tests/test_prompt_generator.py` | — |

---

# Theme System

| Req ID | Source Files | Test Files | Config Keys |
|--------|--------------|------------|-------------|
| REQ-THEME-001 | `config.py:ThemeConfig` | `tests/test_config.py` | `themes.*` |
| REQ-THEME-002 | `config.py:Config.load()` | `tests/test_config.py` | `themes.*.atoms_dir`, `themes.*.prompts_dir` |
| REQ-THEME-003 | `config.py:Config.get_theme()` | `tests/test_config.py` | — |
| REQ-THEME-004 | `config.py` | `tests/test_config.py` | — (global theme only) |
| REQ-THEME-005 | `config.py:get_theme()` | `tests/test_config.py::test_theme_fallback` | `prompt.theme` |

---

# Multi-Monitor Support

| Req ID | Source Files | Test Files | Config Keys |
|--------|--------------|------------|-------------|
| REQ-MONITOR-001 | `monitor_detection.py` (NEW) | `tests/test_monitor_detection.py` | — |
| REQ-MONITOR-002 | `config.py` | `tests/test_config.py` | `monitors.*` |
| REQ-MONITOR-003 | `config.py:MonitorConfig` | `tests/test_config.py` | `monitors.{name}.*` |
| REQ-MONITOR-004 | `config.py:validate_monitors()` | `tests/test_config.py` | — |
| REQ-MONITOR-005 | `state.py:StateManager` | `tests/test_state.py` | — |
| REQ-MONITOR-006 | `config.py:MonitorConfig` | `tests/test_config.py` | `monitors.{name}.output` |
| REQ-MONITOR-007 | `config.py:MonitorConfig` | `tests/test_config.py` | `monitors.{name}.workflow` |
| REQ-MONITOR-008 | `prompt_generator.py` | `tests/test_prompt_generator.py` | — |
| REQ-MONITOR-009 | `cli.py`, `commands/generate.py` | `tests/test_commands.py` | — |

---

# Scheduling

| Req ID | Source Files | Test Files | Config Keys |
|--------|--------------|------------|-------------|
| REQ-SCHED-001 | `prompt_generator.py:get_time_slot_seed()` | `tests/test_prompt_generator.py` | `prompt.time_slot_minutes` |
| REQ-SCHED-002 | `schedule.py` (NEW) | `tests/test_schedule.py` | `schedule.latitude`, `schedule.longitude`, `schedule.day_theme`, `schedule.night_theme` |
| REQ-SCHED-003 | `schedule.py:get_blend_probability()` | `tests/test_schedule.py` | `schedule.blend_duration_minutes` |
| REQ-SCHED-004 | `commands/status.py` | `tests/test_commands.py` | — |

---

# Wallpaper Setters

| Req ID | Source Files | Test Files | Config Keys |
|--------|--------------|------------|-------------|
| REQ-WALL-001 | `wallpaper/setter.py` | `tests/test_wallpaper.py` | `monitors.command` |
| REQ-WALL-002 | `wallpaper/setter.py:_run_custom_command()` | `tests/test_wallpaper.py` | `monitors.command` |
| REQ-WALL-003 | `wallpaper/setter.py:_set_swaybg()` | `tests/test_wallpaper.py` | — |
| REQ-WALL-004 | — (not implemented) | — | — |

---

# History & Gallery

| Req ID | Source Files | Test Files | Config Keys |
|--------|--------------|------------|-------------|
| REQ-HIST-001 | `history/manager.py` | `tests/test_history.py` | `history.enabled`, `history.history_dir` |
| REQ-HIST-002 | `commands/gallery.py` | `tests/test_history.py` | — |
| REQ-HIST-003 | `history/manager.py:cleanup()` | `tests/test_history.py` | `history.cleanup_policy.*` |
| REQ-HIST-004 | `history/manager.py` | `tests/test_history.py` | — |

---

# CLI Interface

| Req ID | Source Files | Test Files | Config Keys |
|--------|--------------|------------|-------------|
| REQ-CLI-001 | `cli.py` | `tests/test_cli.py` | — |
| REQ-CLI-002 | `cli.py:parse_args()` | `tests/test_cli.py` | — |
| REQ-CLI-003 | `commands/generate.py:_dry_run()` | `tests/test_commands.py` | — |

---

# Configuration System

| Req ID | Source Files | Test Files | Config Keys |
|--------|--------------|------------|-------------|
| REQ-CONFIG-001 | `config.py:Config.load()` | `tests/test_config.py` | — |
| REQ-CONFIG-002 | `config.py:_apply_env_overrides()` | `tests/test_config.py` | — |
| REQ-CONFIG-003 | `config.py:Config.init_config_dir()` | `tests/test_config.py` | — |
| REQ-CONFIG-004 | `config.py:Config.__post_init__()` | `tests/test_config.py` | — |
| REQ-CONFIG-005 | `config.py:_check_deprecated_keys()` | `tests/test_config.py` | — |
| REQ-CONFIG-006 | — (explicitly not implemented) | — | — |
| REQ-CONFIG-007 | — (explicitly not implemented) | — | — |

---

# Miscellaneous Features

| Req ID | Source Files | Test Files | Config Keys |
|--------|--------------|------------|-------------|
| REQ-MISC-001 | `notifications.py` (NEW) | `tests/test_notifications.py` | `notifications.enabled` |
| REQ-MISC-002 | — (explicitly not implemented) | — | — |
| REQ-MISC-003 | `commands/status.py` | `tests/test_commands.py` | — |

---

# NixOS Integration

| Req ID | Source Files | Test Files | Config Keys |
|--------|--------------|------------|-------------|
| REQ-NIX-001 | `flake.nix:packages` | — (manual) | — |
| REQ-NIX-002 | `flake.nix:nixosModules` | — (manual) | — |
| REQ-NIX-003 | `flake.nix:homeManagerModules` | — (manual) | — |
| REQ-NIX-004 | `pkgs/darkwall-comfyui.nix` | — (manual) | — |
| REQ-NIX-005 | `flake.nix:devShells` | — (manual) | — |

---

## Directory → Requirement Mapping

Quick lookup: which requirements does this file affect?

| Directory/File | Affects Requirements |
|----------------|---------------------|
| `src/darkwall_comfyui/cli.py` | REQ-CLI-*, REQ-CORE-003, REQ-MONITOR-009 |
| `src/darkwall_comfyui/config.py` | REQ-CONFIG-*, REQ-THEME-*, REQ-WORKFLOW-*, REQ-MONITOR-002 through 007 |
| `src/darkwall_comfyui/prompt_generator.py` | REQ-PROMPT-*, REQ-WORKFLOW-003, REQ-SCHED-001, REQ-MONITOR-008 |
| `src/darkwall_comfyui/comfy/client.py` | REQ-COMFY-* |
| `src/darkwall_comfyui/wallpaper/setter.py` | REQ-WALL-* |
| `src/darkwall_comfyui/history/manager.py` | REQ-HIST-* |
| `src/darkwall_comfyui/commands/generate.py` | REQ-CORE-001, REQ-CORE-002, REQ-CLI-003 |
| `src/darkwall_comfyui/commands/status.py` | REQ-COMFY-005, REQ-SCHED-004, REQ-MISC-003 |
| `src/darkwall_comfyui/commands/gallery.py` | REQ-HIST-002 |
| `src/darkwall_comfyui/commands/prompt.py` | REQ-PROMPT-006, REQ-PROMPT-007 |
| `src/darkwall_comfyui/monitor_detection.py` (NEW) | REQ-MONITOR-001 |
| `src/darkwall_comfyui/schedule.py` (NEW) | REQ-SCHED-002, REQ-SCHED-003 |
| `src/darkwall_comfyui/notifications.py` (NEW) | REQ-MISC-001 |
| `flake.nix` | REQ-NIX-* |

---

## Test File → Requirement Mapping

| Test File | Verifies Requirements |
|-----------|----------------------|
| `tests/test_cli.py` | REQ-CLI-* |
| `tests/test_commands.py` | REQ-CORE-*, REQ-PROMPT-006, REQ-PROMPT-007, REQ-COMFY-005, REQ-SCHED-004, REQ-MISC-003 |
| `tests/test_config.py` | REQ-CONFIG-*, REQ-THEME-*, REQ-WORKFLOW-*, REQ-MONITOR-002 through 007 |
| `tests/test_comfy_client.py` | REQ-COMFY-001 through 004 |
| `tests/test_prompt_generator.py` | REQ-PROMPT-*, REQ-WORKFLOW-003, REQ-SCHED-001, REQ-MONITOR-008 |
| `tests/test_wallpaper.py` | REQ-WALL-* |
| `tests/test_history.py` | REQ-HIST-* |
| `tests/test_state.py` | REQ-MONITOR-005 |
| `tests/test_integration.py` | REQ-CORE-002 |
| `tests/test_monitor_detection.py` (NEW) | REQ-MONITOR-001 |
| `tests/test_schedule.py` (NEW) | REQ-SCHED-002, REQ-SCHED-003 |
| `tests/test_notifications.py` (NEW) | REQ-MISC-001 |

---

*Last Updated: 2025-11-29*
