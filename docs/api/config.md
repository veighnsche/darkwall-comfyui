# Configuration System API

The configuration system provides type-safe configuration loading, validation, and environment variable overrides.

## Core Classes

### Config
Main configuration class that aggregates all configuration sections.

```python
@dataclass
class Config:
    comfyui: ComfyUIConfig
    monitors: MonitorConfig
    output: OutputConfig
    prompt: PromptConfig
    logging: LoggingConfig
    history: HistoryConfig
```

#### Methods

##### `load(config_file: Optional[Path] = None, initialize: bool = True) -> Config`
Load configuration from file with environment variable overrides.

**Parameters:**
- `config_file`: Path to custom config file (default: ~/.config/darkwall-comfyui/config.toml)
- `initialize`: Whether to initialize config directory if missing

**Returns:** Config instance with validation applied

**Raises:**
- `ConfigError`: Invalid configuration syntax or values
- `StateError`: Configuration directory issues

##### `get_config_dir() -> Path`
Get user configuration directory path.

**Returns:** Path to ~/.config/darkwall-comfyui/

##### `get_state_file() -> Path`
Get state file path.

**Returns:** Path to ~/.config/darkwall-comfyui/state.json

##### `initialize_config(package_config_dir: Optional[Path] = None) -> None`
Initialize user configuration directory with defaults.

**Parameters:**
- `package_config_dir`: Path to package config templates

### ComfyUIConfig
ComfyUI server connection settings.

```python
@dataclass
class ComfyUIConfig:
    base_url: str = "https://comfyui.home.arpa"
    workflow_path: Path = field(default_factory=lambda: Path("workflow.json"))
    timeout: int = 300
    poll_interval: int = 5
    headers: Dict[str, str] = field(default_factory=dict)
```

### MonitorConfig
Monitor configuration and output settings.

```python
@dataclass
class MonitorConfig:
    count: int = 3
    pattern: str = "~/Pictures/wallpapers/monitor_{index}.png"
    paths: Optional[List[str]] = None
    command: str = "swaybg"
    backup_pattern: str = "~/Pictures/wallpapers/backups/monitor_{index}_{timestamp}.png"
    workflows: Optional[List[str]] = None
    templates: Optional[List[str]] = None
```

#### Methods

##### `get_output_path(index: int) -> Path`
Get output path for specific monitor index.

##### `get_backup_path(index: int, timestamp: str) -> Path`
Get backup path for specific monitor index.

##### `get_workflow_path(index: int, global_workflow_path: str) -> str`
Get workflow path for specific monitor index.

##### `get_template_path(index: int, default_template: str) -> str`
Get template path for specific monitor index.

### HistoryConfig
Wallpaper history configuration.

```python
@dataclass
class HistoryConfig:
    enabled: bool = True
    history_dir: str = "~/Pictures/wallpapers/history"
    max_entries: int = 1000
    cleanup_policy: Optional[CleanupPolicy] = None
```

#### Methods

##### `get_history_dir() -> Path`
Get absolute history directory path.

### CleanupPolicy
History cleanup policy configuration.

```python
@dataclass
class CleanupPolicy:
    max_count: Optional[int] = None
    max_days: Optional[int] = None
    min_favorites: Optional[int] = None
    max_size_mb: Optional[int] = None
```

#### Methods

##### `should_keep(entry: HistoryEntry, all_entries: List[HistoryEntry], total_size_mb: float) -> bool`
Determine if entry should be kept based on policy.

## Environment Variable Processing

Environment variables override configuration file values using the pattern:
```
DARKWALL_[SECTION]_[KEY]=value
```

### Processing Rules

1. **Section names** are uppercase and prefixed with `DARKWALL_`
2. **Key names** are uppercase
3. **Nested sections** use double underscore separation
4. **Arrays** are comma-separated values
5. **Booleans** accept "true", "false", "1", "0"

### Examples

```bash
# Simple values
export DARKWALL_COMFYUI_BASE_URL="http://localhost:8188"
export DARKWALL_MONITORS_COUNT="2"

# Nested values
export DARKWALL_HISTORY_CLEANUP_POLICY_MAX_DAYS="90"

# Arrays
export DARKWALL_MONITORS_PATHS="/path/1.png,/path/2.png,/path/3.png"

# Booleans
export DARKWALL_HISTORY_ENABLED="false"
```

## Validation System

### Validation Functions

##### `validate_toml_structure(config_dict: Dict[str, Any], config_file: Path) -> None`
Validate TOML structure before creating dataclasses.

**Parameters:**
- `config_dict`: Loaded TOML configuration dictionary
- `config_file`: Path to config file for error messages

**Raises:**
- `ConfigError`: Unknown sections or invalid structure

### Built-in Validations

#### URL Validation
ComfyUI URLs must match HTTP/HTTPS pattern with optional port.

#### Range Validation
- `timeout`: 1-3600 seconds
- `poll_interval`: 1-60 seconds
- `monitor_count`: 1-10 monitors
- `time_slot_minutes`: 1-1440 minutes

#### Pattern Validation
- Monitor patterns must contain `{index}` placeholder
- Backup patterns must contain `{index}` and `{timestamp}` placeholders

#### Type Validation
All configuration values are validated against expected types.

## Error Handling

### ConfigError
Base exception for configuration errors.

```python
class ConfigError(DarkWallError):
    """Configuration-related errors."""
    pass
```

### Common ConfigError Scenarios

- Invalid TOML syntax
- Missing required sections
- Invalid value ranges
- Unknown configuration keys
- File permission issues

## Usage Examples

### Basic Configuration Loading

```python
from darkwall_comfyui.config import Config

# Load with defaults
config = Config.load()

# Load custom config
config = Config.load(Path("/custom/path/config.toml"))

# Load without initialization
config = Config.load(initialize=False)
```

### Configuration Validation

```python
try:
    config = Config.load()
except ConfigError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)
```

### Environment Variable Overrides

```python
import os
from darkwall_comfyui.config import Config

# Set environment variables
os.environ['DARKWALL_COMFYUI_TIMEOUT'] = '600'
os.environ['DARKWALL_MONITORS_COUNT'] = '2'

# Load with overrides
config = Config.load()
assert config.comfyui.timeout == 600
assert config.monitors.count == 2
```

### Custom Configuration Creation

```python
from darkwall_comfyui.config import Config, ComfyUIConfig, MonitorConfig

# Create programmatically
config = Config(
    comfyui=ComfyUIConfig(base_url="http://localhost:8188"),
    monitors=MonitorConfig(count=2, command="swww")
)

# Validation runs automatically in __post_init__
```

## Extension Points

### Custom Configuration Sections
Add new configuration sections by:

1. Creating dataclass in config.py
2. Adding to valid_structure in validation
3. Adding to main Config class
4. Implementing environment variable processing

### Custom Validation
Add custom validation by extending `Config.__post_init__()` method.

### Custom Defaults
Override defaults by modifying dataclass field defaults.
