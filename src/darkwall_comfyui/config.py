"""
Configuration management for DarkWall ComfyUI.

This module handles loading configuration from TOML files and environment variables,
providing defaults and validation, plus config initialization and state management.
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

try:
    import tomli
    import tomli_w
except ImportError:
    raise ImportError("Required packages 'tomli' and 'tomli-w' not found. Install with: pip install tomli tomli-w")

from .exceptions import ConfigError, StateError


@dataclass
class CleanupPolicy:
    """Cleanup policy for history management."""
    max_count: Optional[int] = None  # Keep max N wallpapers
    max_days: Optional[int] = None   # Keep wallpapers newer than X days
    min_favorites: Optional[int] = None  # Always keep at least N favorites
    max_size_mb: Optional[int] = None  # Keep history under X MB


@dataclass
class ThemeConfig:
    """
    Configuration for a content theme.
    
    Themes contain atoms (phrase fragments) and prompts (templates).
    Each theme is a self-contained content set that can be switched.
    """
    name: str
    atoms_dir: str = "atoms"      # Relative to theme directory
    prompts_dir: str = "prompts"  # Relative to theme directory
    default_template: str = "default.prompt"
    
    def get_atoms_path(self, config_dir: Path) -> Path:
        """Get absolute path to atoms directory for this theme."""
        return config_dir / "themes" / self.name / self.atoms_dir
    
    def get_prompts_path(self, config_dir: Path) -> Path:
        """Get absolute path to prompts directory for this theme."""
        return config_dir / "themes" / self.name / self.prompts_dir
    
    def get_template_path(self, config_dir: Path, template_name: Optional[str] = None) -> Path:
        """Get absolute path to a template file."""
        template = template_name or self.default_template
        return self.get_prompts_path(config_dir) / template


@dataclass
class WorkflowConfig:
    """
    Configuration for a workflow with optional prompt filtering.
    
    TEAM_002: REQ-WORKFLOW-001, REQ-WORKFLOW-002
    
    Workflow ID = filename (without .json extension).
    Prompts can be optionally restricted to a subset.
    """
    name: str  # Workflow ID (filename without .json)
    prompts: Optional[List[str]] = None  # Optional: restrict to these prompts only
    
    def get_workflow_path(self, config_dir: Path) -> Path:
        """
        Get workflow file path.
        
        REQ-WORKFLOW-001: Workflow ID = filename.
        """
        workflow_id = self.name
        if not workflow_id.endswith(".json"):
            workflow_id = f"{workflow_id}.json"
        return config_dir / "workflows" / workflow_id
    
    def filter_prompts(self, available_prompts: List[str]) -> List[str]:
        """
        Filter available prompts based on workflow config.
        
        REQ-WORKFLOW-002: Optional prompt filtering.
        
        Args:
            available_prompts: All prompts available in the theme
            
        Returns:
            Filtered list of prompts (all if no filter configured)
        """
        if self.prompts is None:
            return available_prompts
        return [p for p in available_prompts if p in self.prompts]


# URL validation regex
URL_PATTERN = re.compile(
    r'^https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
    r'localhost|'  # localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


# ============================================================================
# DEPRECATED CONFIG KEYS (REQ-CONFIG-005)
# ============================================================================

# Keys that are deprecated and must error with migration instructions
DEPRECATED_KEYS: Dict[str, str] = {
    "monitors.count": (
        "Auto-detection from compositor replaces manual count.\n"
        "  Migration: Remove 'count' and add [monitors.{name}] sections for each monitor.\n"
        "  Example:\n"
        "    [monitors.DP-1]\n"
        "    workflow = \"2327x1309\"\n"
        "    [monitors.HDMI-A-1]\n"
        "    workflow = \"1920x1080\""
    ),
    "monitors.pattern": (
        "Per-monitor output paths replace global pattern.\n"
        "  Migration: Add 'output' to each [monitors.{name}] section.\n"
        "  Example:\n"
        "    [monitors.DP-1]\n"
        "    output = \"~/Pictures/wallpapers/DP-1.png\""
    ),
    "monitors.backup_pattern": (
        "Per-monitor backup paths replace global pattern.\n"
        "  Migration: Add 'backup' to each [monitors.{name}] section."
    ),
    "monitors.workflows": (
        "Array-style workflows are deprecated.\n"
        "  Migration: Add 'workflow' to each [monitors.{name}] section.\n"
        "  Example:\n"
        "    [monitors.DP-1]\n"
        "    workflow = \"2327x1309\""
    ),
    "monitors.templates": (
        "Array-style templates are deprecated.\n"
        "  Migration: Configure templates per workflow in [workflows.{name}] sections."
    ),
    "monitors.paths": (
        "Array-style paths are deprecated.\n"
        "  Migration: Add 'output' to each [monitors.{name}] section."
    ),
    "monitors.names": (
        "Array-style names are deprecated.\n"
        "  Migration: Use [monitors.{name}] sections directly with compositor output names."
    ),
}


def check_deprecated_keys(config_dict: Dict[str, Any], config_file: Path) -> None:
    """
    Check for deprecated config keys and error with migration instructions.
    
    REQ-CONFIG-005: Breaking changes fail hard with clear errors.
    
    Args:
        config_dict: Loaded TOML configuration dictionary
        config_file: Path to config file for error messages
        
    Raises:
        ConfigError: If deprecated keys are found
    """
    errors = []
    
    # Check monitors section for deprecated keys
    monitors = config_dict.get("monitors", {})
    if isinstance(monitors, dict):
        for key in monitors:
            full_key = f"monitors.{key}"
            if full_key in DEPRECATED_KEYS:
                errors.append(f'"{full_key}" is deprecated.\n{DEPRECATED_KEYS[full_key]}')
    
    if errors:
        error_msg = (
            f"Deprecated configuration keys found in {config_file}:\n\n"
            + "\n\n".join(errors)
            + "\n\nSee docs/requirements/REQUIREMENTS.md for full migration guide."
        )
        raise ConfigError(error_msg)


def validate_toml_structure(config_dict: Dict[str, Any], config_file: Path) -> None:
    """
    Validate TOML structure before creating dataclasses.
    
    Checks for unknown sections and keys, providing helpful error messages.
    
    Args:
        config_dict: Loaded TOML configuration dictionary
        config_file: Path to config file for error messages
        
    Raises:
        ConfigError: If structure validation fails
    """
    # Define valid sections and their keys
    # NOTE: monitors section now uses [monitors.{name}] format (per-monitor config)
    # The old flat monitors keys are caught by check_deprecated_keys() first
    valid_structure = {
        'comfyui': {
            'base_url': str,
            'workflow_path': str,
            'timeout': int,
            'poll_interval': int,
            'headers': dict,  # Optional
        },
        'monitors': dict,  # Dynamic: [monitors.{name}] sections with per-monitor config
        'output': {
            'create_backup': bool,
        },
        'prompt': {
            'time_slot_minutes': int,
            'theme': str,
            'atoms_dir': str,
            'use_monitor_seed': bool,
            'default_template': str,  # Optional
            'variations_per_monitor': int,
        },
        'logging': {
            'level': str,
            'verbose': bool,
        },
        'history': {
            'enabled': bool,
            'history_dir': str,
            'max_entries': int,
            'cleanup_policy': dict,  # Optional
        },
        # TEAM_001: Theme definitions
        'themes': dict,  # Dynamic keys: theme names -> theme config
        # TEAM_002: Workflow definitions with optional prompt filtering
        'workflows': dict,  # Dynamic keys: workflow names -> workflow config
        # TEAM_003: Schedule configuration for theme switching
        'schedule': {
            'latitude': float,
            'longitude': float,
            'day_theme': str,
            'night_theme': str,
            'nsfw_start': str,  # "HH:MM" format
            'nsfw_end': str,    # "HH:MM" format
            'blend_duration_minutes': int,
            'timezone': str,
        },
        # TEAM_004: Notifications configuration
        'notifications': {
            'enabled': bool,
            'show_preview': bool,
            'timeout_ms': int,
            'urgency': str,
        },
    }
    
    # Check for unknown sections
    for section in config_dict:
        if section not in valid_structure:
            raise ConfigError(
                f"Unknown config section '{section}' in {config_file}. "
                f"Valid sections: {list(valid_structure.keys())}"
            )
    
    # Check each section for unknown keys and type validation
    for section_name, section_config in config_dict.items():
        if not isinstance(section_config, dict):
            raise ConfigError(
                f"Section '{section_name}' must be a dictionary in {config_file}"
            )
        
        valid_keys = valid_structure[section_name]
        
        # Skip validation for dynamic sections (monitors, themes, workflows)
        # These use [section.{name}] format with arbitrary keys
        if valid_keys == dict:
            continue
        
        for key, value in section_config.items():
            if key not in valid_keys:
                raise ConfigError(
                    f"Unknown key '{key}' in section '{section_name}' in {config_file}. "
                    f"Valid keys: {list(valid_keys.keys())}"
                )
            
            # Basic type checking
            expected_type = valid_keys[key]
            if expected_type != dict and not isinstance(value, expected_type):
                raise ConfigError(
                    f"Key '{section_name}.{key}' must be of type {expected_type.__name__} "
                    f"in {config_file}, got {type(value).__name__}"
                )


@dataclass
class PerMonitorConfig:
    """
    Configuration for a single monitor (new format).
    
    REQ-MONITOR-003: Inline config sections per monitor.
    """
    name: str  # Compositor output name (e.g., "DP-1")
    workflow: str = "default"  # Workflow ID (filename without .json)
    output: Optional[str] = None  # Output path (defaults to ~/Pictures/wallpapers/{name}.png)
    backup: Optional[str] = None  # Backup path pattern
    templates: Optional[List[str]] = None  # Allowed templates for this monitor
    
    def get_output_path(self) -> Path:
        """Get output path for this monitor."""
        if self.output:
            return Path(self.output).expanduser()
        return Path(f"~/Pictures/wallpapers/{self.name}.png").expanduser()
    
    def get_backup_path(self, timestamp: str) -> Path:
        """Get backup path for this monitor."""
        if self.backup:
            return Path(self.backup.format(name=self.name, timestamp=timestamp)).expanduser()
        return Path(f"~/Pictures/wallpapers/backups/{self.name}_{timestamp}.png").expanduser()
    
    def get_workflow_path(self, config_dir: Path) -> Path:
        """Get workflow file path."""
        workflow_id = self.workflow
        if not workflow_id.endswith(".json"):
            workflow_id = f"{workflow_id}.json"
        return config_dir / "workflows" / workflow_id


@dataclass
class MonitorsConfig:
    """
    New-style monitors configuration using compositor names.
    
    REQ-MONITOR-001: Auto-detection via compositor
    REQ-MONITOR-002: Compositor names as identifiers
    REQ-MONITOR-003: Inline config sections
    """
    monitors: Dict[str, PerMonitorConfig] = field(default_factory=dict)
    command: str = "swaybg"  # Wallpaper setter command
    
    def __len__(self) -> int:
        return len(self.monitors)
    
    def get_monitor(self, name: str) -> Optional[PerMonitorConfig]:
        """Get configuration for a specific monitor."""
        return self.monitors.get(name)
    
    def get_monitor_names(self) -> List[str]:
        """Get list of configured monitor names."""
        return list(self.monitors.keys())
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MonitorsConfig':
        """
        Create MonitorsConfig from config dictionary.
        
        Expects format:
        {
            "DP-1": {"workflow": "2327x1309"},
            "HDMI-A-1": {"workflow": "1920x1080"},
            "command": "swaybg"
        }
        """
        monitors = {}
        command = "swaybg"
        
        for key, value in config_dict.items():
            if key == "command":
                command = value
            elif isinstance(value, dict):
                # This is a monitor config
                monitors[key] = PerMonitorConfig(
                    name=key,
                    workflow=value.get("workflow", "default"),
                    output=value.get("output"),
                    backup=value.get("backup"),
                    templates=value.get("templates"),
                )
        
        return cls(monitors=monitors, command=command)


@dataclass
class MonitorConfig:
    """Configuration for monitor management (legacy format - deprecated)."""
    count: int = 3
    pattern: str = "~/Pictures/wallpapers/monitor_{index}.png"
    paths: Optional[List[str]] = None
    command: str = "swaybg"
    backup_pattern: str = "~/Pictures/wallpapers/backups/monitor_{index}_{timestamp}.png"
    workflows: Optional[List[str]] = None  # Per-monitor workflow paths
    templates: Optional[List[str]] = None  # Per-monitor template files
    names: Optional[List[str]] = None      # Per-monitor output names (e.g. eDP-1, HDMI-A-1)
    
    def get_output_path(self, index: int) -> Path:
        """Get output path for specific monitor index."""
        if self.paths and len(self.paths) > index:
            return Path(self.paths[index]).expanduser()
        
        return Path(self.pattern.format(index=index)).expanduser()
    
    def get_backup_path(self, index: int, timestamp: str) -> Path:
        """Get backup path for specific monitor index."""
        return Path(self.backup_pattern.format(index=index, timestamp=timestamp)).expanduser()
    
    def get_workflow_path(self, index: int, global_workflow_path: str) -> str:
        """Get workflow path for specific monitor index."""
        if self.workflows and len(self.workflows) > index and self.workflows[index]:
            return self.workflows[index]
        
        return global_workflow_path
    
    def get_template_path(self, index: int, default_template: str) -> str:
        """Get template path for specific monitor index."""
        if self.templates and len(self.templates) > index and self.templates[index]:
            return self.templates[index]
        
        return default_template

    def get_monitor_name(self, index: int) -> Optional[str]:
        """Get configured monitor output name for a specific index, if available."""
        if self.names and len(self.names) > index and self.names[index]:
            return self.names[index]
        return None


@dataclass
class ComfyUIConfig:
    """ComfyUI connection settings."""
    base_url: str = "https://comfyui.home.arpa"
    workflow_path: Path = field(default_factory=lambda: Path("workflow.json"))
    timeout: int = 300
    poll_interval: int = 5
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class OutputConfig:
    """Output settings."""
    create_backup: bool = True


@dataclass
class PromptConfig:
    """Prompt generation settings."""
    time_slot_minutes: int = 30
    theme: str = "default"  # TEAM_001: Now references themes/<name>/ directory
    use_monitor_seed: bool = True
    default_template: str = "default.prompt"  # Default prompt template
    variations_per_monitor: int = 1
    # TEAM_001: Deprecated - kept for backwards compatibility, ignored if themes/ exists
    atoms_dir: str = "atoms"


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    verbose: bool = False


@dataclass
class HistoryConfig:
    """Wallpaper history configuration."""
    enabled: bool = True
    history_dir: str = "~/Pictures/wallpapers/history"
    max_entries: int = 1000
    cleanup_policy: Optional[CleanupPolicy] = None
    
    def get_history_dir(self) -> Path:
        """Get absolute history directory path."""
        return Path(self.history_dir).expanduser()


@dataclass
class Config:
    """
    Main configuration class for DarkWall ComfyUI.
    
    Configuration is loaded from TOML files with environment variable overrides.
    """
    
    comfyui: ComfyUIConfig = field(default_factory=ComfyUIConfig)
    monitors: MonitorConfig = field(default_factory=MonitorConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    prompt: PromptConfig = field(default_factory=PromptConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    history: HistoryConfig = field(default_factory=HistoryConfig)
    # TEAM_001: Theme definitions - maps theme name to ThemeConfig
    themes: Dict[str, ThemeConfig] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate and post-process configuration."""
        # Validate ComfyUI settings
        if not URL_PATTERN.match(self.comfyui.base_url):
            raise ConfigError(f"Invalid base URL format: {self.comfyui.base_url}")
        
        if self.comfyui.timeout <= 0 or self.comfyui.timeout > 3600:  # Max 1 hour
            raise ConfigError("Generation timeout must be between 1 and 3600 seconds")
        
        if self.comfyui.poll_interval <= 0 or self.comfyui.poll_interval > 60:  # Max 1 minute
            raise ConfigError("Poll interval must be between 1 and 60 seconds")
        
        # Validate workflow path format
        workflow_path = Path(self.comfyui.workflow_path)
        if workflow_path.suffix.lower() != '.json':
            raise ConfigError(f"Workflow path must be a JSON file: {workflow_path}")
        
        # Validate monitor settings
        if self.monitors.count <= 0 or self.monitors.count > 10:
            raise ConfigError("Monitor count must be between 1 and 10")
        
        # Validate wallpaper command
        valid_commands = ['swaybg', 'swww', 'feh', 'nitrogen']
        if not self.monitors.command.startswith('custom:'):
            if self.monitors.command not in valid_commands:
                raise ConfigError(
                    f"Invalid wallpaper command: {self.monitors.command}. "
                    f"Valid commands: {valid_commands} or 'custom:<template>'"
                )
        
        # Validate path patterns contain required placeholders
        if '{index}' not in self.monitors.pattern:
            raise ConfigError("Monitor pattern must contain {index} placeholder")
        
        if '{index}' not in self.monitors.backup_pattern:
            raise ConfigError("Backup pattern must contain {index} placeholder")
        
        if '{timestamp}' not in self.monitors.backup_pattern:
            raise ConfigError("Backup pattern must contain {timestamp} placeholder")
        
        # Validate paths array if provided
        if self.monitors.paths is not None:
            if len(self.monitors.paths) != self.monitors.count:
                raise ConfigError(
                    f"Paths array length ({len(self.monitors.paths)}) must match monitor count ({self.monitors.count})"
                )
        
        # Validate workflows array if provided
        if self.monitors.workflows is not None:
            if len(self.monitors.workflows) != self.monitors.count:
                raise ConfigError(
                    f"Workflows array length ({len(self.monitors.workflows)}) must match monitor count ({self.monitors.count})"
                )
        
        # Validate names array if provided
        if getattr(self.monitors, 'names', None) is not None:
            if len(self.monitors.names) != self.monitors.count:
                raise ConfigError(
                    f"Names array length ({len(self.monitors.names)}) must match monitor count ({self.monitors.count})"
                )
        
        # Validate prompt settings
        if self.prompt.time_slot_minutes <= 0 or self.prompt.time_slot_minutes > 1440:
            raise ConfigError("Time slot minutes must be between 1 and 1440")
        
        if getattr(self.prompt, 'variations_per_monitor', 1) <= 0 or getattr(self.prompt, 'variations_per_monitor', 1) > 20:
            raise ConfigError("variations_per_monitor must be between 1 and 20")
        
        # TEAM_001: Ensure default theme exists if themes are configured
        if self.themes and self.prompt.theme not in self.themes:
            available = list(self.themes.keys())
            raise ConfigError(
                f"Theme '{self.prompt.theme}' not found. Available themes: {available}"
            )
        
        # Validate logging settings
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.level.upper() not in valid_levels:
            raise ConfigError(f"Log level must be one of: {valid_levels}")
    
    def get_theme(self, theme_name: Optional[str] = None) -> ThemeConfig:
        """
        Get theme configuration by name.
        
        TEAM_001: Returns ThemeConfig for the specified theme, or creates
        a default one based on legacy atoms_dir if no themes are configured.
        
        Args:
            theme_name: Theme name to look up (defaults to prompt.theme)
            
        Returns:
            ThemeConfig for the requested theme
        """
        name = theme_name or self.prompt.theme
        
        # If themes are explicitly configured, use them
        if self.themes:
            if name in self.themes:
                return self.themes[name]
            # Fallback to first available theme
            return next(iter(self.themes.values()))
        
        # TEAM_001: Legacy mode - create ThemeConfig from flat structure
        # This supports existing configs with atoms/ and prompts/ at root level
        return ThemeConfig(
            name=name,
            atoms_dir=self.prompt.atoms_dir,
            prompts_dir="prompts",
            default_template=self.prompt.default_template,
        )
    
    def get_theme_atoms_path(self, theme_name: Optional[str] = None) -> Path:
        """Get atoms directory path for a theme."""
        theme = self.get_theme(theme_name)
        config_dir = self.get_config_dir()
        
        # TEAM_001: Check if themes/ structure exists, otherwise use legacy flat structure
        theme_path = theme.get_atoms_path(config_dir)
        if theme_path.exists():
            return theme_path
        
        # Legacy fallback: atoms/ at config root
        legacy_path = config_dir / self.prompt.atoms_dir
        return legacy_path
    
    def get_theme_prompts_path(self, theme_name: Optional[str] = None) -> Path:
        """Get prompts directory path for a theme."""
        theme = self.get_theme(theme_name)
        config_dir = self.get_config_dir()
        
        # TEAM_001: Check if themes/ structure exists, otherwise use legacy flat structure
        theme_path = theme.get_prompts_path(config_dir)
        if theme_path.exists():
            return theme_path
        
        # Legacy fallback: prompts/ at config root
        legacy_path = config_dir / "prompts"
        return legacy_path
    
    @classmethod
    def get_config_dir(cls) -> Path:
        """Get user configuration directory."""
        return Path.home() / ".config" / "darkwall-comfyui"
    
    @classmethod
    def get_state_file(cls) -> Path:
        """Get state file path."""
        return cls.get_config_dir() / "state.json"
    
    @classmethod
    def initialize_config(cls, package_config_dir: Optional[Path] = None) -> None:
        """
        Initialize user configuration directory with defaults.
        
        Copies missing files from package config directory to user config directory.
        Preserves existing user files.
        
        Config templates are found via DARKWALL_CONFIG_TEMPLATES env var (set by Nix wrapper).
        
        Args:
            package_config_dir: Path to package's config directory (for finding defaults)
        """
        logger = logging.getLogger(__name__)
        user_config_dir = cls.get_config_dir()
        user_config_dir.mkdir(parents=True, exist_ok=True)
        
        # If a user config already exists, consider the config initialized and
        # avoid emitting noisy warnings about missing templates on every run.
        existing_config = user_config_dir / "config.toml"
        if existing_config.exists():
            logger.debug(f"Config already initialized at {existing_config}, skipping template copy")
            return
        
        # Use environment variable (set by Nix wrapper)
        config_templates_dir = os.environ.get('DARKWALL_CONFIG_TEMPLATES')
        
        if config_templates_dir:
            package_config_dir = Path(config_templates_dir)
            logger.debug(f"Using config templates from environment: {package_config_dir}")
        
        if package_config_dir and package_config_dir.exists():
            cls._copy_config_files(package_config_dir, user_config_dir)
        else:
            logger.warning(
                f"Config templates not found. Set DARKWALL_CONFIG_TEMPLATES or run via 'nix run'.\n"
                f"  Tried: {package_config_dir}"
            )
    
    @classmethod
    def _copy_file_mutable(cls, src: Path, dst: Path) -> None:
        """
        Copy a file ensuring the destination is mutable.
        
        Reads content and writes to new file to avoid inheriting
        read-only permissions from Nix store.
        
        Args:
            src: Source file path
            dst: Destination file path
            
        Raises:
            ConfigError: If copy operation fails
        """
        try:
            # Read content from source (works even if source is read-only)
            content = src.read_bytes()
            # Write to destination (creates with default permissions)
            dst.write_bytes(content)
            # Explicitly set write permissions
            os.chmod(dst, 0o644)  # rw-r--r--
        except OSError as e:
            raise ConfigError(f"Failed to copy file from {src} to {dst}: {e}")
        except Exception as e:
            raise ConfigError(f"Unexpected error copying file from {src} to {dst}: {e}")
    
    @classmethod
    def _copy_config_files(cls, source_dir: Path, target_dir: Path) -> None:
        """
        Copy config files from source to target directory.
        
        Uses read/write instead of shutil.copy2 to avoid inheriting
        read-only permissions from Nix store.
        
        Args:
            source_dir: Source config directory
            target_dir: Target user config directory
            
        Raises:
            ConfigError: If directory creation or file copying fails
        """
        logger = logging.getLogger(__name__)
        
        try:
            # Ensure target directory has proper permissions
            target_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(target_dir, 0o755)  # rwxr-xr-x
        except OSError as e:
            raise ConfigError(f"Failed to create config directory {target_dir}: {e}")
        
        # Files that should always be present
        required_files = ["config.toml"]
        # TEAM_001: Changed from flat atoms/prompts to themes/ structure
        required_dirs = ["workflows", "themes"]
        
        # Copy missing files
        for required_file in required_files:
            src = source_dir / required_file
            dst = target_dir / required_file
            
            if not dst.exists() and src.exists():
                cls._copy_file_mutable(src, dst)
                logger.info(f"Copied default config: {required_file}")
        
        # Copy missing directories (TEAM_001: now handles nested directories like themes/)
        for required_dir in required_dirs:
            src_dir = source_dir / required_dir
            dst_dir = target_dir / required_dir
            
            if src_dir.exists():
                cls._copy_directory_recursive(src_dir, dst_dir, logger)
                logger.info(f"Initialized directory: {required_dir}")
    
    @classmethod
    def _copy_directory_recursive(cls, src_dir: Path, dst_dir: Path, log: 'logging.Logger') -> None:
        """
        Recursively copy a directory, handling Nix store read-only files.
        
        TEAM_001: Added to support nested theme directories.
        
        Args:
            src_dir: Source directory
            dst_dir: Destination directory
            log: Logger instance
        """
        # Create directory if needed
        dst_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(dst_dir, 0o755)  # rwxr-xr-x
        except OSError:
            pass  # May fail on some systems, continue anyway
        
        for src_item in src_dir.iterdir():
            dst_item = dst_dir / src_item.name
            
            if src_item.is_dir():
                # Recurse into subdirectories
                cls._copy_directory_recursive(src_item, dst_item, log)
            elif src_item.is_file():
                should_copy = False
                reason = ""
                
                if not dst_item.exists():
                    should_copy = True
                    reason = "missing"
                elif not os.access(dst_item, os.W_OK):
                    # Destination exists but is read-only (Nix store leftover)
                    should_copy = True
                    reason = "read-only, fixing"
                    try:
                        dst_item.unlink()
                    except OSError as e:
                        log.warning(f"Failed to remove read-only file {dst_item}: {e}")
                
                if should_copy:
                    try:
                        cls._copy_file_mutable(src_item, dst_item)
                        log.debug(f"Copied {src_item.relative_to(src_dir.parent)} ({reason})")
                    except ConfigError as e:
                        log.error(f"Failed to copy {src_item.name}: {e}")
    
    @classmethod
    def load(cls, config_file: Optional[Path] = None, initialize: bool = True) -> 'Config':
        """
        Load configuration from TOML file and environment variables.
        
        Args:
            config_file: Optional path to config TOML file
            initialize: Whether to initialize config directory with defaults
            
        Returns:
            Config instance with loaded settings
        """
        # Initialize config directory if requested
        if initialize:
            cls.initialize_config()
        
        # Determine config file path
        if not config_file:
            config_file = cls.get_config_dir() / "config.toml"
        
        # Load from TOML file if it exists
        config_dict = {}
        
        if config_file.exists():
            try:
                with open(config_file, 'rb') as f:
                    config_dict = tomli.load(f)
                
                # REQ-CONFIG-005: Check for deprecated keys FIRST (fail hard)
                check_deprecated_keys(config_dict, config_file)
                
                # Validate TOML structure before proceeding
                validate_toml_structure(config_dict, config_file)
                
                logging.getLogger(__name__).info(f"Loaded config from {config_file}")
            except (tomli.TOMLDecodeError, OSError, ConfigError) as e:
                logging.getLogger(__name__).warning(f"Failed to load config file {config_file}: {e}")
                # If validation fails, re-raise as ConfigError
                if isinstance(e, ConfigError):
                    raise
                # For other errors (like TOML parsing), continue with defaults
        else:
            logging.getLogger(__name__).warning(f"Config file not found: {config_file}, using defaults")
        
        # Extract environment variable overrides
        env_overrides = cls._load_env_overrides()
        
        # Merge configurations: defaults -> file -> env vars
        merged_config = cls._merge_configs(config_dict, env_overrides)
        
        # Convert section dictionaries to dataclass instances
        comfyui_config = ComfyUIConfig(**merged_config.get('comfyui', {}))
        monitors_config = MonitorConfig(**merged_config.get('monitors', {}))
        output_config = OutputConfig(**merged_config.get('output', {}))
        prompt_config = PromptConfig(**merged_config.get('prompt', {}))
        logging_config = LoggingConfig(**merged_config.get('logging', {}))
        
        # TEAM_001: Parse themes section into ThemeConfig instances
        themes_dict: Dict[str, ThemeConfig] = {}
        if 'themes' in merged_config:
            for theme_name, theme_data in merged_config['themes'].items():
                if isinstance(theme_data, dict):
                    themes_dict[theme_name] = ThemeConfig(
                        name=theme_name,
                        atoms_dir=theme_data.get('atoms_dir', 'atoms'),
                        prompts_dir=theme_data.get('prompts_dir', 'prompts'),
                        default_template=theme_data.get('default_template', 'default.prompt'),
                    )
                else:
                    # Simple theme reference (just the name, use defaults)
                    themes_dict[theme_name] = ThemeConfig(name=theme_name)
        
        # Create Config instance with dataclass fields
        config = cls(
            comfyui=comfyui_config,
            monitors=monitors_config,
            output=output_config,
            prompt=prompt_config,
            logging=logging_config,
            themes=themes_dict,
        )
        
        return config
    
    @classmethod
    def load_v2(
        cls,
        config_file: Optional[Path] = None,
        initialize: bool = True,
        detect_monitors: bool = True,
    ) -> 'ConfigV2':
        """
        Load configuration using new per-monitor format with auto-detection.
        
        REQ-MONITOR-001: Auto-detect monitors from compositor
        REQ-MONITOR-003: Use [monitors.{name}] sections
        REQ-MONITOR-012: Handle unconfigured monitors (skip with warning)
        REQ-MONITOR-013: Handle disconnected monitors (warn and skip)
        
        Args:
            config_file: Optional path to config TOML file
            initialize: Whether to initialize config directory with defaults
            detect_monitors: Whether to auto-detect monitors from compositor
            
        Returns:
            ConfigV2 instance with loaded settings
        """
        logger = logging.getLogger(__name__)
        
        # Initialize config directory if requested
        if initialize:
            cls.initialize_config()
        
        # Determine config file path
        if not config_file:
            config_file = cls.get_config_dir() / "config.toml"
        
        # Load from TOML file
        config_dict = {}
        if config_file.exists():
            try:
                with open(config_file, 'rb') as f:
                    config_dict = tomli.load(f)
                
                # REQ-CONFIG-005: Check for deprecated keys FIRST
                check_deprecated_keys(config_dict, config_file)
                
                logger.info(f"Loaded config from {config_file}")
            except (tomli.TOMLDecodeError, OSError, ConfigError) as e:
                if isinstance(e, ConfigError):
                    raise
                logger.warning(f"Failed to load config: {e}")
        
        # Parse monitors section (new format)
        monitors_dict = config_dict.get('monitors', {})
        monitors_config = MonitorsConfig.from_dict(monitors_dict)
        
        # Auto-detect connected monitors
        detected_monitors: List[str] = []
        if detect_monitors:
            try:
                from .monitor_detection import detect_monitors as do_detect
                detected = do_detect()
                detected_monitors = [m.name for m in detected]
                logger.info(f"Detected monitors: {detected_monitors}")
            except Exception as e:
                logger.warning(f"Monitor detection failed: {e}")
        
        # REQ-MONITOR-012: Check for unconfigured monitors
        configured_names = monitors_config.get_monitor_names()
        for detected_name in detected_monitors:
            if detected_name not in configured_names:
                logger.warning(
                    f"Monitor '{detected_name}' detected but not configured. "
                    f"Add [monitors.{detected_name}] section to config. Skipping."
                )
        
        # REQ-MONITOR-013: Check for disconnected configured monitors
        active_monitors: List[str] = []
        for configured_name in configured_names:
            if detected_monitors and configured_name not in detected_monitors:
                logger.warning(
                    f"Monitor '{configured_name}' configured but not connected. Skipping."
                )
            else:
                active_monitors.append(configured_name)
        
        # TEAM_002: REQ-WORKFLOW-001 - Validate workflow files exist for active monitors
        config_dir = cls.get_config_dir()
        for monitor_name in active_monitors:
            monitor = monitors_config.get_monitor(monitor_name)
            if monitor:
                workflow_path = monitor.get_workflow_path(config_dir)
                if not workflow_path.exists():
                    raise ConfigError(
                        f"Workflow file not found for monitor '{monitor_name}': {workflow_path}\n"
                        f"  Create the workflow file or update [monitors.{monitor_name}].workflow"
                    )
        
        # Parse other sections
        comfyui_config = ComfyUIConfig(**config_dict.get('comfyui', {}))
        output_config = OutputConfig(**config_dict.get('output', {}))
        prompt_config = PromptConfig(**config_dict.get('prompt', {}))
        logging_config = LoggingConfig(**config_dict.get('logging', {}))
        
        # Parse themes
        themes_dict: Dict[str, ThemeConfig] = {}
        if 'themes' in config_dict:
            for theme_name, theme_data in config_dict['themes'].items():
                if isinstance(theme_data, dict):
                    themes_dict[theme_name] = ThemeConfig(
                        name=theme_name,
                        atoms_dir=theme_data.get('atoms_dir', 'atoms'),
                        prompts_dir=theme_data.get('prompts_dir', 'prompts'),
                        default_template=theme_data.get('default_template', 'default.prompt'),
                    )
                else:
                    themes_dict[theme_name] = ThemeConfig(name=theme_name)
        
        # TEAM_002: Parse workflows section (REQ-WORKFLOW-002)
        workflows_dict: Dict[str, WorkflowConfig] = {}
        if 'workflows' in config_dict:
            for workflow_name, workflow_data in config_dict['workflows'].items():
                if isinstance(workflow_data, dict):
                    workflows_dict[workflow_name] = WorkflowConfig(
                        name=workflow_name,
                        prompts=workflow_data.get('prompts'),  # Optional list of prompts
                    )
                else:
                    # Simple workflow reference (just the name, no prompt filtering)
                    workflows_dict[workflow_name] = WorkflowConfig(name=workflow_name)
        
        # TEAM_003: Parse schedule section (REQ-SCHED-002)
        schedule_config = None
        if 'schedule' in config_dict:
            from .schedule import ScheduleConfig
            sched_data = config_dict['schedule']
            schedule_config = ScheduleConfig(
                latitude=sched_data.get('latitude'),
                longitude=sched_data.get('longitude'),
                day_theme=sched_data.get('day_theme', 'default'),
                night_theme=sched_data.get('night_theme', 'nsfw'),
                nsfw_start=sched_data.get('nsfw_start'),
                nsfw_end=sched_data.get('nsfw_end'),
                blend_duration_minutes=sched_data.get('blend_duration_minutes', 30),
                timezone=sched_data.get('timezone'),
            )
        
        # TEAM_004: Parse notifications section (REQ-MISC-001)
        notifications_config = None
        if 'notifications' in config_dict:
            from .notifications import NotificationConfig
            notif_data = config_dict['notifications']
            notifications_config = NotificationConfig(
                enabled=notif_data.get('enabled', False),
                show_preview=notif_data.get('show_preview', True),
                timeout_ms=notif_data.get('timeout_ms', 5000),
                urgency=notif_data.get('urgency', 'normal'),
            )
        
        return ConfigV2(
            comfyui=comfyui_config,
            monitors=monitors_config,
            active_monitors=active_monitors,
            output=output_config,
            prompt=prompt_config,
            logging=logging_config,
            themes=themes_dict,
            workflows=workflows_dict,
            schedule=schedule_config,
            notifications=notifications_config,
        )
    
    @classmethod
    def _load_env_overrides(cls) -> Dict[str, Any]:
        """Load configuration overrides from environment variables."""
        overrides = {}
        
        # ComfyUI settings
        if 'COMFYUI_BASE_URL' in os.environ:
            overrides.setdefault('comfyui', {})['base_url'] = os.environ['COMFYUI_BASE_URL']
        
        if 'COMFYUI_WORKFLOW_PATH' in os.environ:
            overrides.setdefault('comfyui', {})['workflow_path'] = os.environ['COMFYUI_WORKFLOW_PATH']
        
        if 'COMFYUI_TIMEOUT' in os.environ:
            try:
                overrides.setdefault('comfyui', {})['timeout'] = int(os.environ['COMFYUI_TIMEOUT'])
            except ValueError as e:
                raise ConfigError(f"Invalid COMFYUI_TIMEOUT value: {os.environ['COMFYUI_TIMEOUT']}: {e}")
        
        if 'COMFYUI_POLL_INTERVAL' in os.environ:
            try:
                overrides.setdefault('comfyui', {})['poll_interval'] = int(os.environ['COMFYUI_POLL_INTERVAL'])
            except ValueError as e:
                raise ConfigError(f"Invalid COMFYUI_POLL_INTERVAL value: {os.environ['COMFYUI_POLL_INTERVAL']}: {e}")
        
        # Monitor settings
        if 'MONITOR_COUNT' in os.environ:
            try:
                overrides.setdefault('monitors', {})['count'] = int(os.environ['MONITOR_COUNT'])
            except ValueError as e:
                raise ConfigError(f"Invalid MONITOR_COUNT value: {os.environ['MONITOR_COUNT']}: {e}")
        
        if 'MONITOR_PATTERN' in os.environ:
            overrides.setdefault('monitors', {})['pattern'] = os.environ['MONITOR_PATTERN']
        
        if 'WALLPAPER_COMMAND' in os.environ:
            overrides.setdefault('monitors', {})['command'] = os.environ['WALLPAPER_COMMAND']
        
        # Prompt settings
        if 'TIME_SLOT_MINUTES' in os.environ:
            try:
                overrides.setdefault('prompt', {})['time_slot_minutes'] = int(os.environ['TIME_SLOT_MINUTES'])
            except ValueError as e:
                raise ConfigError(f"Invalid TIME_SLOT_MINUTES value: {os.environ['TIME_SLOT_MINUTES']}: {e}")
        
        if 'DARKWALL_THEME' in os.environ:
            overrides.setdefault('prompt', {})['theme'] = os.environ['DARKWALL_THEME']
        
        # Logging settings
        if 'DARKWALL_LOG_LEVEL' in os.environ:
            overrides.setdefault('logging', {})['level'] = os.environ['DARKWALL_LOG_LEVEL']
        
        return overrides
    
    @classmethod
    def _merge_configs(cls, base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in overrides.items():
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = {**result[key], **value}
            else:
                result[key] = value
        
        return result
    
    def save(self, config_file: Optional[Path] = None) -> None:
        """
        Save current configuration to TOML file.
        
        Args:
            config_file: Path to save configuration (defaults to user config dir)
        """
        if not config_file:
            config_file = self.get_config_dir() / "config.toml"
        
        # Convert to dict for TOML serialization
        config_dict = {
            'comfyui': {
                'base_url': self.comfyui.base_url,
                'workflow_path': str(self.comfyui.workflow_path),
                'timeout': self.comfyui.timeout,
                'poll_interval': self.comfyui.poll_interval,
            },
            'monitors': {
                'count': self.monitors.count,
                'pattern': self.monitors.pattern,
                'command': self.monitors.command,
                'backup_pattern': self.monitors.backup_pattern,
            },
            'output': {
                'create_backup': self.output.create_backup,
            },
            'prompt': {
                'time_slot_minutes': self.prompt.time_slot_minutes,
                'theme': self.prompt.theme,
                'atoms_dir': self.prompt.atoms_dir,
                'use_monitor_seed': self.prompt.use_monitor_seed,
                'default_template': self.prompt.default_template,
                'variations_per_monitor': getattr(self.prompt, 'variations_per_monitor', 1),
            },
            'logging': {
                'level': self.logging.level,
                'verbose': self.logging.verbose,
            },
        }
        
        # Add optional fields
        if self.monitors.paths:
            config_dict['monitors']['paths'] = self.monitors.paths
        
        if getattr(self.monitors, 'names', None):
            config_dict['monitors']['names'] = self.monitors.names
        
        if self.comfyui.headers:
            config_dict['comfyui']['headers'] = self.comfyui.headers
        
        # Ensure directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_file, 'wb') as f:
                tomli_w.dump(config_dict, f)
            
            logging.getLogger(__name__).info(f"Saved config to {config_file}")
        except OSError as e:
            raise ConfigError(f"Failed to save config to {config_file}: {e}")
        except Exception as e:
            raise ConfigError(f"Unexpected error saving config to {config_file}: {e}")


@dataclass
class ConfigV2:
    """
    New-style configuration using per-monitor format.
    
    REQ-MONITOR-001: Auto-detection via compositor
    REQ-MONITOR-002: Compositor names as identifiers
    REQ-MONITOR-003: Inline config sections
    TEAM_002: REQ-WORKFLOW-001, REQ-WORKFLOW-002 - Workflow config with prompt filtering
    TEAM_003: REQ-SCHED-002, REQ-SCHED-003 - Theme scheduling
    """
    comfyui: ComfyUIConfig = field(default_factory=ComfyUIConfig)
    monitors: MonitorsConfig = field(default_factory=MonitorsConfig)
    active_monitors: List[str] = field(default_factory=list)  # Currently connected & configured
    output: OutputConfig = field(default_factory=OutputConfig)
    prompt: PromptConfig = field(default_factory=PromptConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    themes: Dict[str, ThemeConfig] = field(default_factory=dict)
    # TEAM_002: Workflow definitions with optional prompt filtering
    workflows: Dict[str, WorkflowConfig] = field(default_factory=dict)
    # TEAM_003: Schedule configuration for theme switching
    schedule: Optional['ScheduleConfig'] = None
    # TEAM_004: Notifications configuration
    notifications: Optional['NotificationConfig'] = None
    
    def get_monitor_config(self, name: str) -> Optional[PerMonitorConfig]:
        """Get configuration for a specific monitor."""
        return self.monitors.get_monitor(name)
    
    def get_active_monitor_names(self) -> List[str]:
        """Get list of active (connected & configured) monitor names."""
        return self.active_monitors
    
    def get_workflow_for_monitor(self, name: str) -> Optional[Path]:
        """Get workflow path for a monitor."""
        monitor = self.monitors.get_monitor(name)
        if monitor:
            return monitor.get_workflow_path(Config.get_config_dir())
        return None
    
    def get_workflow_config(self, workflow_id: str) -> Optional[WorkflowConfig]:
        """
        Get workflow configuration by ID.
        
        TEAM_002: REQ-WORKFLOW-002 - Returns WorkflowConfig for prompt filtering.
        
        Args:
            workflow_id: Workflow ID (filename without .json)
            
        Returns:
            WorkflowConfig if explicitly configured, None otherwise
        """
        return self.workflows.get(workflow_id)
    
    def get_eligible_prompts_for_workflow(self, workflow_id: str, available_prompts: List[str]) -> List[str]:
        """
        Get eligible prompts for a workflow, applying optional filtering.
        
        TEAM_002: REQ-WORKFLOW-002 - Optional prompt filtering per workflow.
        
        Args:
            workflow_id: Workflow ID (filename without .json)
            available_prompts: All prompts available in the theme
            
        Returns:
            Filtered list of prompts (all if no filter configured)
        """
        workflow_config = self.get_workflow_config(workflow_id)
        if workflow_config:
            return workflow_config.filter_prompts(available_prompts)
        return available_prompts
    
    def get_output_for_monitor(self, name: str) -> Optional[Path]:
        """Get output path for a monitor."""
        monitor = self.monitors.get_monitor(name)
        if monitor:
            return monitor.get_output_path()
        return None
    
    @classmethod
    def get_config_dir(cls) -> Path:
        """Get user configuration directory."""
        return Config.get_config_dir()
    
    @classmethod
    def get_state_file(cls) -> Path:
        """Get state file path."""
        return Config.get_state_file()


class StateManager:
    """Manages persistent state for multi-monitor rotation."""
    
    def __init__(self, monitor_config: MonitorConfig) -> None:
        self.monitor_config = monitor_config
        self.state_file = Config.get_state_file()  # Still need Config for static method
        self.logger = logging.getLogger(__name__)
    
    def get_state(self) -> Dict[str, Any]:
        """Load current state."""
        if not self.state_file.exists():
            return {'last_monitor_index': -1, 'rotation_count': 0}
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            self.logger.warning(f"Failed to load state file: {e}")
            return {'last_monitor_index': -1, 'rotation_count': 0}
        except Exception as e:
            self.logger.error(f"Unexpected error loading state file: {e}")
            return {'last_monitor_index': -1, 'rotation_count': 0}
    
    def save_state(self, state: Dict[str, Any]) -> None:
        """Save current state."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except (OSError, PermissionError) as e:
            raise StateError(f"Failed to save state file {self.state_file}: {e}")
        except Exception as e:
            raise StateError(f"Unexpected error saving state file {self.state_file}: {e}")
    
    def get_next_monitor_index(self) -> int:
        """Get the next monitor index to update."""
        state = self.get_state()
        last_index = state.get('last_monitor_index', -1)
        
        # Cycle to next monitor
        next_index = (last_index + 1) % self.monitor_config.count
        
        # Update state
        state['last_monitor_index'] = next_index
        state['rotation_count'] = state.get('rotation_count', 0) + 1
        self.save_state(state)
        
        self.logger.info(f"Rotating to monitor {next_index} (rotation #{state['rotation_count']})")
        return next_index
    
    def reset_rotation(self) -> None:
        """Reset rotation state."""
        self.save_state({'last_monitor_index': -1, 'rotation_count': 0})
        self.logger.info("Reset monitor rotation state")


class NamedStateManager:
    """
    Manages persistent state for named monitor rotation.
    
    REQ-MONITOR-002: Uses compositor output names instead of indices.
    """
    
    def __init__(self, monitor_names: List[str]) -> None:
        """
        Initialize with list of monitor names.
        
        Args:
            monitor_names: List of compositor output names (e.g., ["DP-1", "HDMI-A-1"])
        """
        self.monitor_names = monitor_names
        self.state_file = Config.get_state_file()
        self.logger = logging.getLogger(__name__)
    
    def get_state(self) -> Dict[str, Any]:
        """Load current state."""
        if not self.state_file.exists():
            return {
                'last_monitor': None,
                'rotation_count': 0,
                'monitor_order': self.monitor_names,
            }
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                # Ensure monitor_order is up to date
                state['monitor_order'] = self.monitor_names
                return state
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            self.logger.warning(f"Failed to load state file: {e}")
            return {
                'last_monitor': None,
                'rotation_count': 0,
                'monitor_order': self.monitor_names,
            }
    
    def save_state(self, state: Dict[str, Any]) -> None:
        """Save current state."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except (OSError, PermissionError) as e:
            raise StateError(f"Failed to save state file {self.state_file}: {e}")
    
    def get_next_monitor(self) -> str:
        """
        Get the next monitor name in rotation.
        
        Returns:
            Monitor name (e.g., "DP-1")
        """
        if not self.monitor_names:
            raise ConfigError("No monitors configured")
        
        state = self.get_state()
        last_monitor = state.get('last_monitor')
        
        # Find next monitor in rotation
        if last_monitor is None or last_monitor not in self.monitor_names:
            next_monitor = self.monitor_names[0]
        else:
            current_idx = self.monitor_names.index(last_monitor)
            next_idx = (current_idx + 1) % len(self.monitor_names)
            next_monitor = self.monitor_names[next_idx]
        
        # Update state
        state['last_monitor'] = next_monitor
        state['rotation_count'] = state.get('rotation_count', 0) + 1
        self.save_state(state)
        
        self.logger.info(f"Rotating to monitor {next_monitor} (rotation #{state['rotation_count']})")
        return next_monitor
    
    def peek_next_monitor(self) -> str:
        """Get next monitor without advancing rotation."""
        if not self.monitor_names:
            raise ConfigError("No monitors configured")
        
        state = self.get_state()
        last_monitor = state.get('last_monitor')
        
        if last_monitor is None or last_monitor not in self.monitor_names:
            return self.monitor_names[0]
        
        current_idx = self.monitor_names.index(last_monitor)
        next_idx = (current_idx + 1) % len(self.monitor_names)
        return self.monitor_names[next_idx]
    
    def reset_rotation(self) -> None:
        """Reset rotation state."""
        self.save_state({
            'last_monitor': None,
            'rotation_count': 0,
            'monitor_order': self.monitor_names,
        })
        self.logger.info("Reset monitor rotation state")
