# DarkWall ComfyUI - TODO and Status

## Project Overview
Multi-monitor wallpaper generator using ComfyUI with deterministic prompts and rotation state management.

**Language Choice**: Python was selected for its strengths in HTTP API calls, JSON manipulation, subprocess management, and cross-platform compatibility. Startup time is not a concern since wallpaper generation takes minutes anyway.

## Recent Session Accomplishments ✨ (2025-11-27)

### 🎯 Real End-to-End Testing (COMPLETED)
- ✅ **ComfyUI Integration**: Successfully connected to local ComfyUI at `192.168.178.29:8188`
- ✅ **Qwen T2I Workflow**: Added working workflow JSON for wallpaper generation
- ✅ **Real Wallpaper Generation**: Generated actual wallpapers (1.7-2MB each) with creative prompts
- ✅ **Workflow Path Resolution**: Fixed relative paths to resolve against config directory

### 🔧 Swaybg/NixOS Fix (COMPLETED)
- ✅ **Process Conflict Resolution**: Fixed swaybg timeout by killing existing processes per-monitor
- ✅ **Background Daemon Handling**: Modified swaybg setter to run in background (persistent daemon)
- ✅ **NixOS Systemd Compatibility**: Works alongside existing niri-swaybg-launch systemd service

### � Workflow Management (COMPLETED)
- ✅ **Workflows Directory**: Added `config/workflows/` with default Qwen T2I workflow
- ✅ **Config Initialization**: Workflows directory copied to user config on init
- ✅ **Relative Path Support**: Workflow paths resolve relative to config directory

### 🧪 Integration Tests (COMPLETED)
- ✅ **10 Passing Tests**: Comprehensive mocked integration tests
- ✅ **State Isolation**: Fixed test state bleeding with config directory mocking
- ✅ **Error Scenarios**: Tests for ComfyUI unreachable, workflow errors, generation failures
- ✅ **Flake.nix DevShell**: Fixed to include tomli/tomli-w and PYTHONPATH

## Pending Tasks 📋

### 🎯 HIGH PRIORITY - NixOS Integration & Deployment

#### Nix Package Implementation (IN PROGRESS)
- [x] **Comprehensive Flake.nix**: Created full flake with runtime dependencies, systemd integration, and modules
- [x] **Runtime Dependencies**: Wrapped wallpaper setters (swww, swaybg, feh, nitrogen) in PATH
- [x] **NixOS Module**: System-level deployment module with systemd service/timer configuration
- [x] **Home Manager Module**: User-level deployment module for home-manager integration
- [x] **Non-flake Compatibility**: Created pkgs/darkwall-comfyui.nix for classic NixOS configs
- [ ] **Additional Wallpaper Setters**: Expand support beyond swww/swaybg/feh/nitrogen to include:
  - [ ] **hyprpaper**: For Hyprland users
  - [ ] **wallutils**: Cross-platform wallpaper utility
  - [ ] **wpaperd**: Wallpaper daemon for Wayland
  - [ ] **maliit**: For mobile/embedded environments
  - [ ] **gnome-backgrounds**: GNOME desktop integration
  - [ ] **plasma-workspace**: KDE Plasma integration
- [ ] **Local Testing**: Verify build works immediately and systemd integration functions

### 🎯 HIGH PRIORITY - Refactoring & Architecture

#### Code Quality Refactoring (COMPLETED)
- [x] **Consolidate Duplicate Logic**: Review and merge similar code patterns - Fixed duplicate _run_command and _default_monitor_name methods
- [x] **Consistent Error Handling**: Standardize exception handling across modules - Implemented specific exceptions, removed silent failures
- [x] **Configuration Validation**: Add schema validation for config files - Added comprehensive validation in Config.__post_init__
- [x] **Dependency Injection**: Reduce coupling between modules for testability - All classes now accept specific config objects
- [x] **Clean Up Patchy Code**: Address ad-hoc fixes made during development - Replaced broad exception handling with specific types
- [x] **Comprehensive Testing**: Created 52 tests to freeze refactoring behavior and prevent regressions

#### Multi-Workflow Support (COMPLETED)
- [x] **Per-Monitor Workflows**: Different workflow JSON per monitor (different sizes/styles) - Added workflows field to MonitorConfig with validation
- [x] **Workflow Selection CLI**: `--workflow` flag to select specific workflow - Added CLI flag for generate-once override
- [x] **Workflow Validation**: Validate workflow JSON structure on load - Enhanced dry-run to show validation warnings
- [ ] **Workflow Templates**: Pre-configured workflows for common resolutions (1080p, 1440p, 4K)

#### Prompt / Workflow / Monitor Hierarchy (PLANNED)
- [ ] **Canonical Hierarchy**: Make the data model explicit and config-driven:
  - Multiple wildcards per atom file (lines in `atoms/*.txt`)
  - Multiple atoms per prompt template (`prompts/*.prompt`)
  - Multiple prompt templates per workflow
  - Multiple workflows per monitor
- [ ] **Config: Workflow-Centric Prompts**: Introduce a `[workflows]` table in `config.toml` so each workflow can declare:
  - `path = "workflows/z-image.json"`
  - `prompts = ["default.prompt", "cinematic.prompt", "cyberpunk.prompt", "minimal.prompt"]`
  This makes prompts belong to workflows, not directly to monitors.
- [ ] **Config: Monitor → Workflow Mapping**: Change monitor configuration so monitors reference workflows (by ID or index) instead of raw JSON paths + templates:
  - Each monitor selects a workflow from the `[workflows]` table
  - Workflows then control which prompt templates are eligible
- [ ] **Selection Semantics**: Define deterministic selection using existing seeding so that:
  - For a given monitor + workflow, prompts are chosen from that workflow's `prompts` list
  - Over time, all configured prompts for that workflow are used across all monitors (no prompt stranded on a single monitor unless explicitly configured).
- [ ] **Code: Config Types**: Add a `WorkflowConfig` dataclass (or similar) to model workflows + their prompts, and wire it into `Config` loading/validation.
- [ ] **Code: Generate Path**: Update `commands/generate.py` so the flow is:
  1. Monitor index → workflow selection from config
  2. Workflow → prompt template list
  3. PromptGenerator → pick a template from that list (using the deterministic seed), then resolve atoms/wildcards inside the template
  4. ComfyClient → run the selected workflow with the resolved prompt
- [ ] **Migration & Cleanup**: Remove or deprecate `MonitorConfig.templates` and the direct `workflows` array usage in favor of the workflow table (break callers and fix them rather than duplicating behavior).
- [ ] **Tests & Docs**: Add tests for:
  - Per-workflow prompt pools
  - Per-monitor workflow mapping
  - Deterministic prompt/workflow selection across runs
  And update docs/configuration.md to describe the new hierarchy and config options.

### 🔴 HIGH PRIORITY - Critical Issues

#### Prompt Injection System (COMPLETED ✅)
- [x] **Replace Heuristic Detection**: Current system uses fragile heuristics to detect prompt fields
- [x] **Implement Placeholder System**: Require `__POSITIVE_PROMPT__` and `__NEGATIVE_PROMPT__` placeholders in workflows
- [x] **Workflow Migration**: Create migration guide for existing workflows
- [x] **Update Validation**: Warn when workflows don't contain required placeholders
- [x] **Breaking Change**: This requires users to update their exported workflows

**✅ RESOLVED**: Implemented deterministic placeholder-based prompt injection system:
- Replaced fragile heuristic detection with exact placeholder matching
- Updated default workflow (qwen_t2i.json) to include both placeholders
- Removed backwards compatibility - placeholders now required
- Added clear error messages with migration instructions
- Created comprehensive migration guide (docs/workflow-migration.md)
- Enhanced validation to fail fast on missing placeholders

**User Experience**: New users get proper workflows via `darkwall init`, existing users get actionable error messages.

### 🟡 MEDIUM PRIORITY - Features & Enhancements

#### 🔄 PROMPT BUILDER REDESIGN (Replaces NSFW Mode)

**STATUS**: COMPLETE - Template system fully implemented with examples

##### Problem Statement
The current 4-atom system (subject, environment, lighting, style) is too rigid:
- NSFW mode was a band-aid solution
- Users can't customize prompt structure
- No per-monitor customization
- Negative prompts not supported

##### 🏆 DESIGN: Hybrid Wildcards + Templates

**Directory Structure** (`~/.config/darkwall-comfyui/`):
```
atoms/
├── subjects/           # Each file = wildcard
│   ├── nature.txt      # One prompt fragment per line
│   ├── abstract.txt
│   ├── characters.txt
│   └── nsfw/           # Optional NSFW subfolder
│       └── adult.txt
├── styles/
│   ├── artistic.txt
│   ├── photorealistic.txt
│   └── anime.txt
├── environments/
│   └── ...
├── modifiers/
│   └── ...
└── negative/           # Negative prompt atoms
    ├── quality.txt     # "blurry, low quality, watermark"
    └── artifacts.txt

prompts/
├── monitor_0.prompt    # Per-monitor prompt templates
├── monitor_1.prompt
└── default.prompt      # Fallback
```

**Prompt Template Syntax** (`.prompt` files):
```
# Positive prompt template
__subjects/nature__, __environments/outdoor__, __styles/artistic__

# Supports inline variants
{cinematic|dramatic|moody} lighting

# Supports weights
{0.8::masterpiece|0.2::experimental}, high quality

---negative---
__negative/quality__, __negative/artifacts__
```

**Config Integration** (`config.toml`):
```toml
[prompts]
default_template = "default.prompt"

[monitors.0]
name = "ultrawide"
template = "monitor_0.prompt"  # Custom template

[monitors.1]
name = "portrait"
template = "default.prompt"    # Uses default
```

##### Implementation Plan

- [x] **Phase 1: Simplify prompt_generator.py** (COMPLETE)
  - Removed `PromptPillars` dataclass (unnecessary intermediate)
  - Removed `generate_pillars()` (replaced by template parsing)
  - Removed `build_prompt()` (template IS the prompt)
  - Kept `get_time_slot_seed()` and `select_atom()` (core logic)
  - Added template parsing with `__wildcard__` and `{variant}` syntax
  
- [x] **Phase 2: Template Parser** (COMPLETE)
  - Parse `.prompt` files with positive/negative sections
  - Resolve `__path__` → random line from `atoms/path.txt`
  - Resolve `{a|b|c}` → random choice
  - Resolve `{0.5::a|2::b}` → weighted random
  
- [x] **Phase 3: Config Updates** (COMPLETE)
  - Added `default_template` to PromptConfig
  - Created `prompts/default.prompt` template
  - Updated config initialization to copy prompts/ directory
  
- [x] **Phase 4: Negative Prompt Support** (COMPLETE)
  - Parse `---negative---` section in templates
  - `generate_prompt_pair()` returns PromptResult with positive & negative
  - TODO: Inject negative prompt into workflow JSON (when workflow has negative node)
  
- [x] **Phase 5: BREAK EVERYTHING** (COMPLETE)
  - Removed `atoms` property (use `_load_atom_file()` directly)
  - Removed `select_atom()` method (use `_select_from_list()`)
  - Removed `_generate_legacy_template()` fallback
  - Renamed atom files: `subject.txt`, `environment.txt`, `lighting.txt`, `style.txt`
  - Template file is REQUIRED - no fallback

- [x] **Phase 6: Template Examples & CLI** (COMPLETE)
  - Added new atom categories: `colors.txt`, `moods.txt`, `compositions.txt`
  - Created example templates: `cinematic.prompt`, `cyberpunk.prompt`, `minimal.prompt`
  - Implemented `darkwall prompt preview` command with seed support
  - Implemented `darkwall prompt list [--atoms]` command
  - All templates showcase wildcard and variant syntax

- [x] **Phase 7: Per-Monitor Templates** (COMPLETE)
  - Added `templates` field to MonitorConfig dataclass (Optional[List[str]])
  - Added get_template_path() method to MonitorConfig
  - Added `--template` CLI flag to override template for generate command
  - Updated generate commands to use per-monitor templates when available
  - Template override only affects 'generate', not 'generate-all' (respects per-monitor)

- [x] **Phase 8: Workflow Negative Prompt Injection** (COMPLETE)
  - Added PromptResult support to ComfyClient.generate() method
  - Implemented _inject_prompts() to detect CLIPTextEncode nodes with negative prompts
  - Injects negative prompt into nodes with 'negative' field or NEGATIVE placeholder
  - Logs warning when negative prompt provided but no negative node found
  - Updated generate commands to pass PromptResult instead of just prompt string

- [ ] **Phase 9: Atom Management Commands** (SKIPPED)
  - Users can edit atom files directly in their text editor
  - CLI commands would be redundant with existing file-based approach

##### Simplification Benefits

| Before | After |
|--------|-------|
| `PromptPillars` dataclass | Removed - template is the structure |
| `generate_pillars()` | Removed - inline resolution |
| `build_prompt()` hard-coded | Template file defines structure |
| 4 fixed atom files | Any `.txt` file in atoms/ |
| No negative prompts | `---negative---` section |
| No per-monitor themes | Per-monitor `.prompt` files |

---

#### Wallpaper History & Gallery (COMPLETED)
- [x] **Save All Wallpapers**: Keep history of all generated wallpapers (not just current)
- [x] **History Directory**: `~/Pictures/wallpapers/history/` with timestamped files in YYYY/MM/ structure
- [x] **Gallery Command**: `gallery` subcommand to browse/manage history (list, info, favorite, delete, stats, cleanup)
- [x] **Favorites System**: Mark wallpapers as favorites to prevent deletion with ★ markers
- [x] **Cleanup Policy**: Configurable retention (keep last N, keep X days, size limits, protect favorites)

#### Enhanced Prompt Generation (Superseded by Prompt Builder Redesign above)
- [x] **Theme Packs**: ~~Multiple atom sets~~ → Solved by atoms/ subdirectories
- [x] **Prompt Templates**: ~~Customizable structure~~ → Solved by .prompt files
- [x] **Negative Prompts**: ~~Support for negative prompts~~ → Solved by ---negative--- section
- [x] **Prompt Preview**: Kept as `darkwall prompt preview` command

### � LOW PRIORITY - Polish & Documentation

#### Documentation (COMPLETED)
- [x] **Man Page**: Complete CLI documentation with examples
- [x] **Troubleshooting Guide**: Common issues and solutions (swaybg conflicts, permissions, etc.)
- [x] **API Documentation**: Document internal APIs for extensibility
- [x] **Configuration Reference**: Complete config.toml documentation

#### Desktop Integration
- [ ] **Desktop Notifications**: Notify when wallpaper changes
- [ ] **Auto-Start**: Systemd user service for automatic startup
- [ ] **Waybar Integration**: Custom module showing current wallpaper info
- [ ] **Lock Screen Integration**: Set lock screen wallpaper alongside desktop

#### Performance & Reliability (COMPLETED ✅)
- [x] **Async Operations**: Use async/await for API calls - Skipped (overkill for CLI tool)
- [x] **Connection Pooling**: Reuse HTTP connections for multiple requests - Implemented HTTPAdapter with pool_connections=10, pool_maxsize=20
- [x] **Retry Logic**: Configurable retry with exponential backoff - Added urllib3.Retry with 2s, 4s, 8s backoff for connection errors/timeouts/5xx
- [x] **Health Monitoring**: Background health checks for ComfyUI availability - Enhanced health check with response times and system stats

**✅ RESOLVED**: Implemented comprehensive performance and reliability improvements:
- Added automatic retry logic with exponential backoff for network failures
- Optimized HTTP session with connection pooling for multiple requests
- Enhanced health monitoring with detailed system information and response times
- Implemented adaptive polling that backs off on repeated failures
- Improved error messages with actual elapsed times and failure tracking
- Enhanced status command to show device info, VRAM, queue status, and response times

**Performance Benefits**: Faster repeated requests, automatic recovery from temporary failures, better visibility into system health, and more efficient polling behavior.

## Completed Tasks ✅

### Core Infrastructure
- [x] **Project Structure**: Created Python package with proper module organization
- [x] **Nix Flake**: Working build system with dependencies and wrapper script
- [x] **CLI Interface**: Argument parsing with subcommands (init, status, generate, etc.)
- [x] **Logging**: Configurable logging system with multiple levels

### ComfyUI Integration ✅
- [x] **Workflow Loading**: Complete workflow JSON loading with validation and caching
- [x] **API Client**: Full HTTP client for ComfyUI endpoints with error handling
- [x] **Prompt Injection**: Inject generated prompts into workflow JSON
- [x] **Result Polling**: Wait for generation completion and handle timeouts
- [x] **Image Download**: Download generated wallpapers from ComfyUI
- [x] **Health Checks**: Verify ComfyUI connectivity before generation
- [x] **Relative Path Resolution**: Workflow paths resolve against config directory

### Multi-Monitor Support ✅
- [x] **MonitorConfig**: Dataclass for monitor configuration with patterns and commands
- [x] **Rotation State**: StateManager for tracking which monitor to update next
- [x] **Monitor-Specific Seeds**: Prompt generator supports monitor index in seed generation
- [x] **Wallpaper Commands**: Support for swaybg, swww, feh, nitrogen, and custom commands
- [x] **Swaybg Process Management**: Kill existing processes before setting new wallpaper

### Configuration System ✅
- [x] **TOML Configuration**: Complete config file with all sections
- [x] **Dataclasses**: Proper dataclass structure for all config sections
- [x] **Environment Variables**: Override system for all config options
- [x] **Config Initialization**: Automatic copying of defaults to user config directory
- [x] **Package Data**: Config files bundled in Nix package and accessible via environment variable
- [x] **Workflows Directory**: Default workflows copied to user config

### Prompt Generation ✅
- [x] **Atom Files**: Subject, environment, lighting, and style atoms loaded from config
- [x] **Deterministic Seeds**: Time-slot based seeding with monitor variation
- [x] **Prompt Construction**: Four-pillar prompt building with dark-mode optimization
- [x] **Fallback Logic**: Graceful handling of missing atom files

### Wallpaper Management ✅
- [x] **File Operations**: Save wallpapers with proper naming and directory structure
- [x] **Backup System**: Create backups before overwriting existing wallpapers
- [x] **Command Execution**: Actually run wallpaper setting commands (swww, swaybg, feh, nitrogen, custom)
- [x] **Error Handling**: Graceful handling of command failures and missing tools
- [x] **Background Daemon Support**: Swaybg runs in background as persistent daemon

### State Management ✅
- [x] **State Persistence**: Save rotation state to JSON file
- [x] **State Recovery**: Handle corrupted or missing state files
- [x] **Rotation Logic**: Proper cycling through monitors with configurable order
- [x] **Reset Functionality**: Implement state reset for testing/recovery

### CLI Features ✅
- [x] **Generate All**: Implement wallpaper generation for all monitors at once
- [x] **Dry Run Mode**: Show what would be generated without actually doing it
- [x] **Verbose Output**: Detailed logging of each step in the process
- [x] **Configuration Validation**: Validate config files and show errors

### Testing ✅
- [x] **Unit Tests**: Test individual modules and functions
- [x] **Integration Tests**: 10 comprehensive tests with mocked ComfyUI
- [x] **Mock ComfyUI**: Test without actual ComfyUI instance
- [x] **Config Tests**: Test various configuration scenarios
- [x] **State Isolation**: Proper test isolation with config directory mocking

### Deployment ✅
- [x] **Systemd Service**: Timer service for automatic wallpaper rotation
- [x] **Package Installation**: Install to system with proper paths
- [x] **Nix DevShell**: Development environment with all dependencies

## Technical Debt 🛠️

### Code Quality (Needs Refactoring)
- [ ] **Patchy Fixes**: Several ad-hoc fixes need consolidation
- [ ] **Inconsistent Patterns**: Different error handling approaches across modules
- [ ] **Missing Abstractions**: Some code could benefit from better abstraction
- [ ] **Test Coverage Gaps**: Some edge cases not covered by tests

### Architecture Improvements
- [ ] **Dependency Injection**: Reduce coupling between modules
- [ ] **Interface Segregation**: Split large interfaces into smaller ones
- [ ] **Configuration Schema**: Add schema validation for config files
- [ ] **Plugin System**: Support for custom prompt generators and wallpaper setters

### Performance
- [ ] **Caching**: Cache prompt generation and API responses
- [ ] **Async Operations**: Use async/await for API calls and file operations
- [ ] **Resource Management**: Proper cleanup of temporary files and connections
- [ ] **Memory Usage**: Optimize for long-running daemon mode

## Known Bugs 🐛

- ~~Config initialization creates read-only files from Nix store~~ ✅ FIXED
- ~~State file handling not implemented yet~~ ✅ FIXED
- ~~Wallpaper commands are mocked (not actually executed)~~ ✅ FIXED
- ~~No validation of ComfyUI URL connectivity~~ ✅ FIXED
- ~~Swaybg timeout due to persistent daemon conflict~~ ✅ FIXED
- ~~Workflow path not resolving relative to config directory~~ ✅ FIXED
- ~~7 pre-existing unit tests failing~~ ✅ FIXED (87 tests now passing)

## Dependencies 🔧

- `tomli` and `tomli-w` ✅ (added to Nix)
- `requests` ✅ (already included)
- `makeWrapper` ✅ (added to Nix)
- `pytest` ✅ (in devShell)

---
*Last Updated: 2025-11-28 01:05*

## Recent Fixes (This Session)
- **Workflow Path Resolution**: Fixed relative workflow paths to resolve against config directory
- **Swaybg Background Daemon**: Modified to run swaybg in background with proper process management
- **Swaybg Process Conflict**: Added pkill to terminate existing swaybg processes per-monitor
- **Workflows Directory**: Added config/workflows/ with Qwen T2I workflow, copied on init
- **Flake.nix DevShell**: Added tomli/tomli-w dependencies and PYTHONPATH for testing
- **Integration Tests**: Created 10 comprehensive tests with proper state isolation
- **Config Initialization**: Updated to copy workflows directory alongside atoms

*Status: Core implementation complete and tested end-to-end with real ComfyUI. Ready for refactoring and feature expansion.*
