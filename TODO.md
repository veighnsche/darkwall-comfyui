# DarkWall ComfyUI - TODO and Status

## Project Overview
Multi-monitor wallpaper generator using ComfyUI with deterministic prompts and rotation state management.

## Current Issues

### 🔴 Critical Issues
- **Config Structure Mismatch**: TOML has `backup_pattern` in `[output]` section but `OutputConfig` dataclass doesn't include this field
- ~~**File Permissions**: Atom files copied from Nix store have read-only permissions, preventing cleanup~~ ✅ FIXED - Uses read/write copy instead of shutil.copy2 to avoid inheriting Nix store permissions
- **Path Resolution**: Atoms directory path mismatch - config expects `config/atoms` but initialization copies to `atoms/`

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

### Multi-Monitor Support
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

### Config Loading Fix
- [ ] **Fix backup_pattern**: Move from `[output]` to `[monitors]` section or add to OutputConfig
- [ ] **Fix atoms_dir**: Update default from `"config/atoms"` to `"atoms"` to match initialization
- [ ] **Test Dataclass Loading**: Verify all config sections load properly as dataclasses
- [ ] **Fix File Permissions**: Ensure copied config files have write permissions

### Integration Testing
- [ ] **End-to-End Test**: Complete wallpaper generation workflow test
- [ ] **Multi-Monitor Test**: Verify rotation works across multiple monitors
- [ ] **Config Reload Test**: Test configuration changes take effect properly

## Pending Tasks 📋

### ComfyUI Integration
- [ ] **Workflow Loading**: Implement actual ComfyUI workflow file loading
- [ ] **API Client**: Complete HTTP client for ComfyUI endpoints
- [ ] **Prompt Injection**: Inject generated prompts into workflow JSON
- [ ] **Result Polling**: Wait for generation completion and handle timeouts
- [ ] **Image Download**: Download generated wallpapers from ComfyUI

### Wallpaper Management
- [ ] **File Operations**: Save wallpapers with proper naming and directory structure
- [ ] **Backup System**: Create backups before overwriting existing wallpapers
- [ ] **Command Execution**: Actually run wallpaper setting commands (currently mocked)
- [ ] **Error Handling**: Graceful handling of command failures and missing tools

### State Management
- [ ] **State Persistence**: Save rotation state to JSON file
- [ ] **State Recovery**: Handle corrupted or missing state files
- [ ] **Rotation Logic**: Proper cycling through monitors with configurable order
- [ ] **Reset Functionality**: Implement state reset for testing/recovery

### CLI Features
- [ ] **Generate All**: Implement wallpaper generation for all monitors at once
- [ ] **Dry Run Mode**: Show what would be generated without actually doing it
- [ ] **Verbose Output**: Detailed logging of each step in the process
- [ ] **Configuration Validation**: Validate config files and show errors

### Documentation
- [ ] **README Update**: Document multi-monitor features and configuration
- [ ] **Man Page**: Complete CLI documentation with examples
- [ ] **Integration Guide**: Systemd timer setup and desktop environment integration
- [ ] **Troubleshooting**: Common issues and solutions

### Testing
- [ ] **Unit Tests**: Test individual modules and functions
- [ ] **Integration Tests**: Test complete workflows
- [ ] **Mock ComfyUI**: Test without actual ComfyUI instance
- [ ] **Config Tests**: Test various configuration scenarios

### Deployment
- [ ] **Systemd Service**: Timer service for automatic wallpaper rotation
- [ ] **Package Installation**: Install to system with proper paths
- [ ] **Desktop Integration**: Auto-start and desktop notifications
- [ ] **Docker Support**: Containerized deployment option

## Technical Debt 🛠️

### Code Quality
- [ ] **Error Handling**: Add comprehensive error handling throughout
- [ ] **Type Hints**: Complete type annotations for all functions
- [ ] **Documentation**: Add docstrings to all classes and methods
- [ ] **Code Style**: Ensure consistent formatting and naming

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

1. **Fix Critical Config Issues** (Immediate)
   - Move `backup_pattern` to correct section
   - Fix `atoms_dir` path mismatch
   - Test complete config loading

2. **Complete ComfyUI Integration** (This Week)
   - Implement workflow loading and prompt injection
   - Add API client with proper error handling
   - Test end-to-end generation

3. **Multi-Monitor Testing** (Next Week)
   - Test rotation across 3 monitors
   - Verify different wallpaper commands work
   - Test state persistence and recovery

4. **Documentation and Polish** (Following Week)
   - Update README with multi-monitor examples
   - Add systemd timer setup instructions
   - Complete CLI help and man page

## Known Bugs 🐛

- ~~Config initialization creates read-only files from Nix store~~ ✅ FIXED
- State file handling not implemented yet
- Wallpaper commands are mocked (not actually executed)
- No validation of ComfyUI URL connectivity
- Missing error handling for network failures

## Dependencies Needed 🔧

- `tomli` and `tomli-w` ✅ (added to Nix)
- `requests` ✅ (already included)
- `makeWrapper` ✅ (added to Nix)
- Test framework (pytest) - for future testing
- Mock ComfyUI server - for development testing

---
*Last Updated: 2025-11-27 17:59*

## Recent Fixes
- **File Permissions Fix**: Changed `_copy_config_files` to use `read_bytes()`/`write_bytes()` instead of `shutil.copy2` to avoid inheriting read-only permissions from Nix store
- **New CLI Command**: Added `fix-permissions` subcommand for troubleshooting
- **Status Enhancement**: Added file permissions display to `status` command showing ✓/✗ for each config file
*Status: Core infrastructure complete, ComfyUI integration in progress*
