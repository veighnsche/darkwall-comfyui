# DarkWall ComfyUI - TODO and Status

## Project Overview
Multi-monitor wallpaper generator using ComfyUI with deterministic prompts and rotation state management.

**Language Choice**: Python was selected for its strengths in HTTP API calls, JSON manipulation, subprocess management, and cross-platform compatibility. Startup time is not a concern since wallpaper generation takes minutes anyway.

## Recent Major Improvements ✨

### 🎯 CLI & Usability (COMPLETED)
- ✅ **Dry-run mode**: `--dry-run` flag shows what would happen without executing
- ✅ **Config validation**: `validate` command and `--validate-config` flag
- ✅ **Verbose output**: Enhanced logging with `--verbose` flag
- ✅ **Generate all**: `generate-all` command for all monitors

### 🛡️ Code Quality (COMPLETED)
- ✅ **Comprehensive error handling**: Specific exception types throughout
- ✅ **Complete type hints**: All functions properly annotated
- ✅ **Full documentation**: Docstrings on all classes and methods
- ✅ **Unit test suite**: pytest tests for all major modules

### 🚀 Deployment (COMPLETED)
- ✅ **Systemd integration**: Service and timer files with install script
- ✅ **Multi-monitor docs**: Comprehensive configuration examples
- ✅ **requirements.txt**: Added for non-Nix users
- ✅ **README updates**: Complete usage documentation

## Current Issues

### 🔴 Critical Issues
- ~~**Config Structure Mismatch**: TOML has `backup_pattern` in `[output]` section~~ ✅ FIXED - `backup_pattern` is correctly in `[monitors]` section and `MonitorConfig` dataclass
- ~~**File Permissions**: Atom files copied from Nix store have read-only permissions, preventing cleanup~~ ✅ FIXED - Uses read/write copy instead of shutil.copy2 to avoid inheriting Nix store permissions
- ~~**Path Resolution**: Atoms directory path mismatch~~ ✅ FIXED - atoms_dir defaults to "atoms" which matches `~/.config/darkwall-comfyui/atoms/`

### 🟡 Configuration Issues
- **Dataclass Conversion**: TOML dictionaries not properly converted to dataclass instances (partially fixed)
- **Environment Variable Overrides**: Need to verify all env vars work with new dataclass structure
- **Config Validation**: Missing validation for required fields and value ranges

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

### Multi-Monitor Support ✅
- [x] **MonitorConfig**: Dataclass for monitor configuration with patterns and commands
- [x] **Rotation State**: StateManager for tracking which monitor to update next
- [x] **Monitor-Specific Seeds**: Prompt generator supports monitor index in seed generation
- [x] **Wallpaper Commands**: Support for swaybg, swww, feh, nitrogen, and custom commands

### Configuration System
- [x] **TOML Configuration**: Complete config file with all sections
- [x] **Dataclasses**: Proper dataclass structure for all config sections
- [x] **Environment Variables**: Override system for all config options
- [x] **Config Initialization**: Automatic copying of defaults to user config directory
- [x] **Package Data**: Config files bundled in Nix package and accessible via environment variable

### Prompt Generation
- [x] **Atom Files**: Subject, environment, lighting, and style atoms loaded from config
- [x] **Deterministic Seeds**: Time-slot based seeding with monitor variation
- [x] **Prompt Construction**: Four-pillar prompt building with dark-mode optimization
- [x] **Fallback Logic**: Graceful handling of missing atom files

## In Progress Tasks 🟡

### Integration Testing
- [ ] **End-to-End Test**: Complete wallpaper generation workflow test
- [ ] **Multi-Monitor Test**: Verify rotation works across multiple monitors
- [ ] **Config Reload Test**: Test configuration changes take effect properly

## Pending Tasks 📋

### Testing & Quality Assurance
- [ ] **Integration Tests**: End-to-end workflow testing with mocked ComfyUI
- [ ] **Multi-Monitor Integration**: Test rotation across 3+ monitors
- [ ] **Error Scenario Testing**: Network failures, missing files, invalid configs
- [ ] **Performance Testing**: Large workflow files and slow generation

### Documentation & Polish
- [ ] **Man Page**: Complete CLI documentation with examples
- [ ] **Troubleshooting Guide**: Common issues and solutions
- [ ] **API Documentation**: Document internal APIs for extensibility

### Optional Enhancements
- [ ] **Docker Support**: Containerized deployment option
- [ ] **Desktop Integration**: Auto-start and desktop notifications
- [ ] **Plugin System**: Support for custom prompt generators and wallpaper setters

### Wallpaper Management ✅
- [x] **File Operations**: Save wallpapers with proper naming and directory structure
- [x] **Backup System**: Create backups before overwriting existing wallpapers
- [x] **Command Execution**: Actually run wallpaper setting commands (swww, swaybg, feh, nitrogen, custom)
- [x] **Error Handling**: Graceful handling of command failures and missing tools

### State Management ✅
- [x] **State Persistence**: Save rotation state to JSON file
- [x] **State Recovery**: Handle corrupted or missing state files
- [x] **Rotation Logic**: Proper cycling through monitors with configurable order
- [x] **Reset Functionality**: Implement state reset for testing/recovery

### CLI Features
- [x] **Generate All**: Implement wallpaper generation for all monitors at once
- [x] **Dry Run Mode**: Show what would be generated without actually doing it
- [x] **Verbose Output**: Detailed logging of each step in the process
- [x] **Configuration Validation**: Validate config files and show errors

### Documentation
- [x] **README Update**: Document multi-monitor features and configuration
- [ ] **Man Page**: Complete CLI documentation with examples
- [x] **Integration Guide**: Systemd timer setup and desktop environment integration
- [ ] **Troubleshooting**: Common issues and solutions

### Testing
- [x] **Unit Tests**: Test individual modules and functions
- [ ] **Integration Tests**: Test complete workflows
- [x] **Mock ComfyUI**: Test without actual ComfyUI instance
- [x] **Config Tests**: Test various configuration scenarios

### Deployment
- [x] **Systemd Service**: Timer service for automatic wallpaper rotation
- [x] **Package Installation**: Install to system with proper paths
- [ ] **Desktop Integration**: Auto-start and desktop notifications
- [ ] **Docker Support**: Containerized deployment option

## Technical Debt 🛠️

### Code Quality
- [x] **Error Handling**: Add comprehensive error handling throughout
- [x] **Type Hints**: Complete type annotations for all functions
- [x] **Documentation**: Add docstrings to all classes and methods
- [x] **Code Style**: Ensure consistent formatting and naming

### Architecture
- [ ] **Dependency Injection**: Reduce coupling between modules
- [ ] **Interface Segregation**: Split large interfaces into smaller ones
- [ ] **Configuration Schema**: Add schema validation for config files
- [ ] **Plugin System**: Support for custom prompt generators and wallpaper setters

### Performance
- [ ] **Caching**: Cache prompt generation and API responses
- [ ] **Async Operations**: Use async/await for API calls and file operations
- [ ] **Resource Management**: Proper cleanup of temporary files and connections
- [ ] **Memory Usage**: Optimize for long-running daemon mode

## Next Steps 🎯

1. **Create Integration Tests** (Immediate)
   - End-to-end workflow test with mocked ComfyUI responses
   - Multi-monitor rotation test
   - Error scenario testing

2. **Documentation Polish** (This Week)
   - Complete man page with all commands and examples
   - Add troubleshooting guide for common issues
   - Document internal APIs for extensibility

3. **Optional Enhancements** (Future)
   - Docker containerization
   - Desktop notifications
   - Plugin system for custom components

## Known Bugs 🐛

- ~~Config initialization creates read-only files from Nix store~~ ✅ FIXED
- ~~State file handling not implemented yet~~ ✅ FIXED
- ~~Wallpaper commands are mocked (not actually executed)~~ ✅ FIXED
- ~~No validation of ComfyUI URL connectivity~~ ✅ FIXED
- Missing integration tests for end-to-end workflows
- No error handling for network timeouts beyond basic retries

## Dependencies Needed 🔧

- `tomli` and `tomli-w` ✅ (added to Nix)
- `requests` ✅ (already included)
- `makeWrapper` ✅ (added to Nix)
- Test framework (pytest) - for future testing
- Mock ComfyUI server - for development testing

---
*Last Updated: 2025-11-27 23:21*

## Recent Fixes
- **File Permissions Fix**: Changed `_copy_config_files` to use `read_bytes()`/`write_bytes()` instead of `shutil.copy2` to avoid inheriting read-only permissions from Nix store
- **New CLI Command**: Added `fix-permissions` subcommand for troubleshooting
- **Status Enhancement**: Added file permissions display to `status` command showing ✓/✗ for each config file
- **Config Duplication Removed**: Deleted `src/darkwall_comfyui/config/` duplicate, rely solely on top-level `config/`
- **ComfyClient Fixed**: Updated to use nested dataclass config structure
- **Prompt Generator Fixed**: Removed dead fallback path, clear error message for missing atoms
- **TODO Accuracy Update**: Corrected TODO to reflect actual implementation status - ComfyUI integration, wallpaper setters, and state management are all complete

*Status: Core implementation complete, ready for integration testing and documentation polish*
