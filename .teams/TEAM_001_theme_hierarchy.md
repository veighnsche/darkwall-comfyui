# TEAM_001 — Theme Hierarchy & Time-Based Content

**Session Date**: 2025-11-29
**Focus**: Restructure config for themes + sundown/sunrise NSFW scheduling

## Task Overview

1. Implement theme-based hierarchy for atoms/prompts/workflows
2. Add sundown-to-sunrise time-based theme switching (NSFW at night)
3. Improve config.toml structure to support this cleanly

## Session Progress

### Analysis Complete
- Reviewed current architecture: Lines → Atoms → Prompts → Workflows → Monitors
- Identified limitations: single atoms_dir, no theme switching, no time-based scheduling
- Proposed themes/ directory structure with SFW/NSFW separation

### Planned Features (Added to TODO.md)
- Theme hierarchy with separate atoms/prompts per theme
- Sundown/Sunrise detection for automatic NSFW scheduling
- Per-monitor theme/workflow/template profiles

### Implementation Complete ✅

#### config.py Changes
- Added `ThemeConfig` dataclass with `name`, `atoms_dir`, `prompts_dir`, `default_template`
- Added `themes: Dict[str, ThemeConfig]` field to `Config` class
- Added `get_theme()` method with legacy fallback support
- Added `get_theme_atoms_path()` and `get_theme_prompts_path()` helper methods
- Updated `validate_toml_structure()` to accept `themes` section
- Updated `Config.load()` to parse themes from TOML
- Updated `_copy_config_files()` to use recursive copy for nested themes/
- Added `_copy_directory_recursive()` helper method

#### prompt_generator.py Changes
- Updated `__init__` to accept optional `atoms_dir` and `prompts_dir` paths
- Added `_atoms_dir` and `_prompts_dir` instance variables
- Updated `_load_atom_file()` to use theme-aware atoms directory
- Updated `_load_template()` to use theme-aware prompts directory
- Added `PromptGenerator.from_config()` factory method for theme-aware creation

#### Directory Structure Changes
- Moved `config/atoms/` → `config/themes/default/atoms/`
- Moved `config/prompts/` → `config/themes/default/prompts/`
- Updated `required_dirs` in config init from `["atoms", "workflows", "prompts"]` to `["workflows", "themes"]`

### Tests
- All prompt_generator tests pass (11/11)
- All config-related tests pass (11/11)
- Pre-existing test failures unrelated to this work

## Handoff
- [x] Team file complete
- [x] TODO.md updated with new features
- [x] Code compiles (Python)
- [x] Core tests pass
- [x] Theme hierarchy implemented with legacy fallback

## Next Steps for Future Teams
1. ~~Implement ThemeConfig dataclass in config.py~~ ✅ DONE
2. Add `astral` dependency to flake.nix for solar calculations
3. Create themes/nsfw/ directory with NSFW atoms
4. Implement theme scheduler based on sundown/sunrise
5. Update CLI commands to use `PromptGenerator.from_config()`
6. Add tests for theme switching
