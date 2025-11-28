# Configuration Reference

Complete reference for all DarkWall ComfyUI configuration options in `config.toml`.

## Configuration File Location

```
~/.config/darkwall-comfyui/config.toml
```

## Environment Variable Overrides

All configuration options can be overridden with environment variables using the pattern:
```
DARKWALL_[SECTION]_[KEY]=value
```

Examples:
```bash
export DARKWALL_COMFYUI_BASE_URL="http://localhost:8188"
export DARKWALL_MONITORS_COUNT="2"
export DARKWALL_HISTORY_ENABLED="false"
```

## Configuration Sections

### [comfyui] - ComfyUI Server Settings

Connection and communication settings for the ComfyUI server.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `base_url` | string | `"https://comfyui.home.arpa"` | ComfyUI server URL |
| `workflow_path` | string | `"workflow.json"` | Path to workflow JSON file |
| `timeout` | integer | `300` | Generation timeout in seconds (1-3600) |
| `poll_interval` | integer | `5` | Status poll interval in seconds (1-60) |
| `headers` | dict | `{}` | Additional HTTP headers |

#### URL Requirements
- Must be valid HTTP/HTTPS URL
- Supports IP addresses (e.g., `http://192.168.1.100:8188`)
- Supports localhost (e.g., `http://localhost:8188`)
- Supports domain names (e.g., `https://comfyui.example.com`)

#### Headers Example
```toml
[comfyui.headers]
Authorization = "Bearer your-token"
User-Agent = "DarkWall/1.0"
```

### [monitors] - Monitor Configuration

Settings for monitor detection, output paths, and wallpaper commands.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `count` | integer | `3` | Number of monitors (1-10) |
| `pattern` | string | `"~/Pictures/wallpapers/monitor_{index}.png"` | Output filename pattern |
| `paths` | array | `null` | Explicit output paths per monitor |
| `command` | string | `"swaybg"` | Wallpaper setter command |
| `backup_pattern` | string | `"~/Pictures/wallpapers/backups/monitor_{index}_{timestamp}.png"` | Backup filename pattern |
| `workflows` | array | `null` | Per-monitor workflow paths |
| `templates` | array | `null` | Per-monitor template files |

#### Pattern Placeholders
- `{index}`: Monitor index (0-based)
- `{timestamp}`: Unix timestamp for backups

#### Command Options
- `"swaybg"`: Sway wallpaper tool (recommended for Sway/Wlroots)
- `"swww"`: Simple Fast Wallpaper Switcher
- `"feh"`: Lightweight image viewer (X11)
- `"nitrogen"`: Background browser and setter (X11)
- `"custom:<command>"`: Custom command with placeholders

#### Custom Command Example
```toml
[monitors]
command = "custom:wallpaper-setter --image {path} --monitor {index} --mode fill"
```

#### Per-Monitor Configuration Example
```toml
[monitors]
count = 2
paths = [
    "~/Pictures/wallpapers/ultrawide.png",
    "~/Pictures/wallpapers/portrait.png"
]
workflows = [
    "ultrawide_workflow.json",
    "portrait_workflow.json"
]
templates = [
    "ultrawide.prompt",
    "portrait.prompt"
]
```

### [output] - Output Settings

File output and backup settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `create_backup` | boolean | `true` | Create backups before overwriting |

#### Backup Behavior
- Backups created in `backup_pattern` location
- Timestamp format: `YYYYMMDD_HHMMSS`
- Only created when file exists and `create_backup` is true

### [prompt] - Prompt Generation Settings

Configuration for prompt generation and template processing.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `time_slot_minutes` | integer | `30` | Time slot duration for deterministic seeds |
| `theme` | string | `"default"` | Prompt theme name |
| `atoms_dir` | string | `"atoms"` | Directory name for atom files |
| `use_monitor_seed` | boolean | `true` | Include monitor index in seed generation |
| `default_template` | string | `"default.prompt"` | Default prompt template file |

#### Time Slot Seeding
- Seeds are deterministic based on time slots
- Same time slot + monitor = same wallpaper
- Useful for synchronized wallpapers across restarts
- Range: 1-1440 minutes (max 24 hours)

#### Atoms Directory Structure
```
~/.config/darkwall-comfyui/atoms/
├── subjects.txt
├── environments.txt
├── lighting.txt
├── styles.txt
├── colors.txt
├── moods.txt
└── compositions.txt
```

#### Template Files
Template files use wildcard and variant syntax:
```
__subjects/nature__, __environments/outdoor__, __styles/artistic__
{cinematic|dramatic|moody} lighting

---negative---
__negative/quality__, __negative/artifacts__
```

### [history] - Wallpaper History Settings

Configuration for wallpaper history and gallery functionality.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | boolean | `true` | Enable history saving |
| `history_dir` | string | `"~/Pictures/wallpapers/history"` | History directory path |
| `max_entries` | integer | `1000` | Maximum history entries before cleanup |

#### History Directory Structure
```
~/Pictures/wallpapers/history/
├── 2025/
│   ├── 01/
│   │   ├── 20250128_120000_monitor_0.png
│   │   └── 20250128_121500_monitor_1.png
│   └── 02/
└── index.json
```

#### Cleanup Policy (Optional)
```toml
[history.cleanup_policy]
max_count = 500           # Keep maximum 500 wallpapers
max_days = 90            # Keep wallpapers newer than 90 days
min_favorites = 10       # Always keep at least 10 favorites
max_size_mb = 5000       # Keep history under 5GB
```

### [logging] - Logging Configuration

Control logging verbosity and output format.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `level` | string | `"INFO"` | Log level |
| `verbose` | boolean | `false` | Enable verbose output |

#### Log Levels (in order of severity)
- `DEBUG`: Detailed debugging information
- `INFO`: General information messages
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical errors that prevent operation

## Complete Configuration Example

```toml
# DarkWall ComfyUI Configuration
# Location: ~/.config/darkwall-comfyui/config.toml

[comfyui]
base_url = "https://comfyui.home.arpa"
workflow_path = "qwen_t2i_workflow.json"
timeout = 300
poll_interval = 5

[comfyui.headers]
Authorization = "Bearer your-api-token"

[monitors]
count = 3
pattern = "~/Pictures/wallpapers/monitor_{index}.png"
command = "swaybg"
backup_pattern = "~/Pictures/wallpapers/backups/monitor_{index}_{timestamp}.png"
# Optional: Per-monitor configurations
paths = [
    "~/Pictures/wallpapers/ultrawide.png",
    "~/Pictures/wallpapers/vertical.png",
    "~/Pictures/wallpapers/small.png"
]
workflows = [
    "ultrawide_workflow.json",
    "portrait_workflow.json",
    "small_workflow.json"
]
templates = [
    "ultrawide.prompt",
    "portrait.prompt",
    "minimal.prompt"
]

[output]
create_backup = true

[prompt]
time_slot_minutes = 30
theme = "dark_mode"
atoms_dir = "atoms"
use_monitor_seed = true
default_template = "default.prompt"

[history]
enabled = true
history_dir = "~/Pictures/wallpapers/history"
max_entries = 1000

[history.cleanup_policy]
max_count = 500
max_days = 90
min_favorites = 10
max_size_mb = 5000

[logging]
level = "INFO"
verbose = false
```

## Configuration Validation

### Built-in Validation

DarkWall validates configuration on startup and reports errors:

```bash
darkwall validate
```

### Common Validation Errors

#### URL Validation
```
ERROR: Invalid base URL format: not-a-url
```
**Solution**: Use valid HTTP/HTTPS URL format.

#### Range Validation
```
ERROR: Monitor count must be between 1 and 10
```
**Solution**: Adjust value to be within valid range.

#### Pattern Validation
```
ERROR: Monitor pattern must contain {index} placeholder
```
**Solution**: Include required placeholders in patterns.

#### Path Validation
```
ERROR: Workflow path must be a JSON file
```
**Solution**: Ensure workflow file has `.json` extension.

### Configuration Debugging

#### Show Effective Configuration
```bash
darkwall status
```
Shows all configuration values after environment variable overrides.

#### Test Configuration
```bash
darkwall --dry-run generate
```
Validates configuration without performing generation.

#### Environment Variable Debugging
```bash
env | grep DARKWALL_
```
Shows all active environment variable overrides.

## Advanced Configuration

### Conditional Configuration
Use environment variables for different environments:

```bash
# Development
export DARKWALL_COMFYUI_BASE_URL="http://localhost:8188"
export DARKWALL_LOGGING_LEVEL="DEBUG"

# Production
export DARKWALL_COMFYUI_BASE_URL="https://comfyui.production.com"
export DARKWALL_HISTORY_ENABLED="true"
```

### Multi-User Configuration
Share configuration with user-specific overrides:

```toml
# /etc/darkwall-comfyui/config.toml (system-wide)
[comfyui]
base_url = "https://comfyui.company.com"

# ~/.config/darkwall-comfyui/config.toml (user overrides)
[monitors]
count = 2  # User's monitor count
```

### Configuration Templates
Create templates for different setups:

```bash
# Gaming setup
cp templates/gaming.toml ~/.config/darkwall-comfyui/config.toml

# Work setup
cp templates/work.toml ~/.config/darkwall-comfyui/config.toml
```

## Migration Guide

### Upgrading from v0.1 to v0.2

New configuration options added:
```toml
# Add these sections if missing
[history]
enabled = true
history_dir = "~/Pictures/wallpapers/history"
max_entries = 1000

[prompt]
default_template = "default.prompt"
```

### Legacy Configuration Support

Old configuration files are automatically migrated. Backups are created as:
```
~/.config/darkwall-comfyui/config.toml.backup.YYYYMMDD_HHMMSS
```
