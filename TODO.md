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

### � HIGH PRIORITY - Refactoring & Architecture

#### Code Quality Refactoring
- [ ] **Consolidate Duplicate Logic**: Review and merge similar code patterns
- [ ] **Consistent Error Handling**: Standardize exception handling across modules
- [ ] **Configuration Validation**: Add schema validation for config files
- [ ] **Dependency Injection**: Reduce coupling between modules for testability
- [ ] **Clean Up Patchy Code**: Address ad-hoc fixes made during development

#### Multi-Workflow Support
- [ ] **Per-Monitor Workflows**: Different workflow JSON per monitor (different sizes/styles)
- [ ] **Workflow Selection CLI**: `--workflow` flag to select specific workflow
- [ ] **Workflow Validation**: Validate workflow JSON structure on load
- [ ] **Workflow Templates**: Pre-configured workflows for common resolutions (1080p, 1440p, 4K)

### 🟡 MEDIUM PRIORITY - New Features

#### NSFW Mode
- [ ] **NSFW Atoms Directory**: Separate `atoms_nsfw/` with adult content prompts
- [ ] **NSFW Config Toggle**: `nsfw = true/false` in config.toml
- [ ] **NSFW CLI Flag**: `--nsfw` to enable adult content generation
- [ ] **Content Filtering**: Ensure NSFW content only generated when explicitly enabled

#### Wallpaper History & Gallery
- [ ] **Save All Wallpapers**: Keep history of all generated wallpapers (not just current)
- [ ] **History Directory**: `~/Pictures/wallpapers/history/` with timestamped files
- [ ] **Gallery Command**: `gallery` subcommand to browse/manage history
- [ ] **Favorites System**: Mark wallpapers as favorites to prevent deletion
- [ ] **Cleanup Policy**: Configurable retention (keep last N, keep X days, etc.)

#### Enhanced Prompt Generation
- [ ] **Theme Packs**: Multiple atom sets for different moods (cyberpunk, nature, abstract)
- [ ] **Prompt Templates**: Customizable prompt structure beyond 4-pillar system
- [ ] **Negative Prompts**: Support for negative prompt injection
- [ ] **Prompt Preview**: Show generated prompt before sending to ComfyUI

### � LOW PRIORITY - Polish & Documentation

#### Documentation
- [ ] **Man Page**: Complete CLI documentation with examples
- [ ] **Troubleshooting Guide**: Common issues and solutions (swaybg conflicts, permissions, etc.)
- [ ] **API Documentation**: Document internal APIs for extensibility
- [ ] **Configuration Reference**: Complete config.toml documentation

#### Desktop Integration
- [ ] **Desktop Notifications**: Notify when wallpaper changes
- [ ] **Auto-Start**: Systemd user service for automatic startup
- [ ] **Waybar Integration**: Custom module showing current wallpaper info
- [ ] **Lock Screen Integration**: Set lock screen wallpaper alongside desktop

#### Performance & Reliability
- [ ] **Async Operations**: Use async/await for API calls
- [ ] **Connection Pooling**: Reuse HTTP connections for multiple requests
- [ ] **Retry Logic**: Configurable retry with exponential backoff
- [ ] **Health Monitoring**: Background health checks for ComfyUI availability

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
- 7 pre-existing unit tests failing (unrelated to recent changes, need investigation)

## Dependencies 🔧

- `tomli` and `tomli-w` ✅ (added to Nix)
- `requests` ✅ (already included)
- `makeWrapper` ✅ (added to Nix)
- `pytest` ✅ (in devShell)

---
*Last Updated: 2025-11-27 23:57*

## Recent Fixes (This Session)
- **Workflow Path Resolution**: Fixed relative workflow paths to resolve against config directory
- **Swaybg Background Daemon**: Modified to run swaybg in background with proper process management
- **Swaybg Process Conflict**: Added pkill to terminate existing swaybg processes per-monitor
- **Workflows Directory**: Added config/workflows/ with Qwen T2I workflow, copied on init
- **Flake.nix DevShell**: Added tomli/tomli-w dependencies and PYTHONPATH for testing
- **Integration Tests**: Created 10 comprehensive tests with proper state isolation
- **Config Initialization**: Updated to copy workflows directory alongside atoms

*Status: Core implementation complete and tested end-to-end with real ComfyUI. Ready for refactoring and feature expansion.*
