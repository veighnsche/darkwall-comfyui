% DARKWALL(1) DarkWall ComfyUI Manual
% NAME
darkwall - Deterministic dark-mode wallpaper generator using ComfyUI

# SYNOPSIS

**darkwall** \[*OPTIONS*\] \[*COMMAND*\]

# DESCRIPTION

DarkWall ComfyUI is a multi-monitor wallpaper generator that creates deterministic, high-quality wallpapers using ComfyUI. It supports per-monitor configurations, custom prompt templates, and maintains a complete history of generated wallpapers.

The generator creates dark-mode optimized wallpapers with time-slot based seeding for consistent rotation across multiple monitors. All generated wallpapers are automatically saved to history for browsing and management.

# OPTIONS

**-h, --help**
: Show help message and exit.

**-v, --verbose**
: Enable debug logging for troubleshooting.

**-c, --config** *PATH*
: Path to configuration file (default: ~/.config/darkwall-comfyui/config.toml).

**--no-init**
: Skip automatic configuration directory initialization.

**--dry-run**
: Show what would be generated without actually doing it.

**--validate-config**
: Validate configuration and exit.

**--workflow** *PATH*
: Override workflow path for generate command.

**--template** *PATH*
: Override template file for generate command.

# COMMANDS

## generate
Generate wallpaper for the next monitor in rotation (default command).

## generate-all
Generate wallpapers for all monitors simultaneously.

## status
Show current configuration, system status, and generation history statistics.

## init
Initialize user configuration directory with default templates and atoms.

## reset
Reset monitor rotation state to start from the first monitor.

## fix-permissions
Fix read-only configuration files that may occur after Nix package installation.

## validate
Validate configuration file syntax and values.

## prompt
Manage prompt templates and atoms.

### prompt preview \[--template TEMPLATE\] \[--monitor N\] \[--seed N\]
Preview generated prompt without running generation.

### prompt list \[--atoms\]
List available prompt templates or atom files.

## gallery
Browse and manage wallpaper history.

### gallery list \[--monitor N\] \[--favorites\] \[--limit N\] \[--format table|json\]
List wallpapers in history with optional filtering.

### gallery info *TIMESTAMP*
Show detailed information about a specific wallpaper.

### gallery favorite *TIMESTAMP* \[--unfavorite\]
Mark or unmark wallpaper as favorite.

### gallery delete *TIMESTAMP*
Delete wallpaper from history.

### gallery stats
Show history statistics and storage usage.

### gallery cleanup
Run cleanup policy to remove old wallpapers.

# CONFIGURATION

The configuration file is located at `~/.config/darkwall-comfyui/config.toml`.

## Sections

### [comfyui]
ComfyUI server connection settings.

- **base_url** (string): ComfyUI server URL (default: "https://comfyui.home.arpa")
- **workflow_path** (string): Path to workflow JSON file (default: "workflow.json")
- **timeout** (int): Generation timeout in seconds (default: 300)
- **poll_interval** (int): Status poll interval in seconds (default: 5)

### [monitors]
Monitor configuration and wallpaper settings.

- **count** (int): Number of monitors (default: 3)
- **pattern** (string): Output filename pattern with {index} placeholder
- **command** (string): Wallpaper setter command (swaybg, swww, feh, nitrogen, or custom:)
- **backup_pattern** (string): Backup filename pattern
- **workflows** (array): Per-monitor workflow paths (optional)
- **templates** (array): Per-monitor template files (optional)

### [prompt]
Prompt generation settings.

- **time_slot_minutes** (int): Time slot duration for deterministic seeds (default: 30)
- **theme** (string): Prompt theme (default: "default")
- **atoms_dir** (string): Directory name for atom files (default: "atoms")
- **use_monitor_seed** (bool): Use monitor index in seed generation (default: true)
- **default_template** (string): Default prompt template file (default: "default.prompt")

### [history]
Wallpaper history settings.

- **enabled** (bool): Enable history saving (default: true)
- **history_dir** (string): History directory path (default: "~/Pictures/wallpapers/history")
- **max_entries** (int): Maximum history entries (default: 1000)

### [logging]
Logging configuration.

- **level** (string): Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **verbose** (bool): Enable verbose output (default: false)

# EXAMPLES

Generate wallpaper for next monitor:
```
darkwall generate
```

Generate for all monitors with custom workflow:
```
darkwall generate-all --workflow custom.json
```

Preview prompt without generation:
```
darkwall prompt preview --template cinematic.prompt --monitor 0
```

Browse wallpaper history:
```
darkwall gallery list --favorites --limit 10
darkwall gallery info 2025-01-28T12:00:00
```

Show system status:
```
darkwall status
```

# FILES

~/.config/darkwall-comfyui/config.toml
: Main configuration file

~/.config/darkwall-comfyui/state.json
: Rotation state file

~/.config/darkwall-comfyui/atoms/
: Prompt atom files directory

~/.config/darkwall-comfyui/prompts/
: Prompt template files directory

~/.config/darkwall-comfyui/workflows/
: ComfyUI workflow files directory

~/Pictures/wallpapers/history/
: Generated wallpaper history (YYYY/MM/ structure)

# ENVIRONMENT VARIABLES

DARKWALL_CONFIG_TEMPLATES
: Path to package configuration templates (set by Nix wrapper)

# EXIT STATUS

0
: Success

1
: General error or configuration issue

2
: ComfyUI connection error

130
: Interrupted by user (Ctrl+C)

# SEE ALSO

**swaybg**(1), **swww**(1), **feh**(1), **nitrogen**(1)

# BUGS

Report bugs at: https://github.com/yourusername/darkwall-comfyui/issues

# AUTHOR

DarkWall ComfyUI - Multi-monitor wallpaper generator
