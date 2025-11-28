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


# URL validation regex
URL_PATTERN = re.compile(
    r'^https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
    r'localhost|'  # localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


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
    valid_structure = {
        'comfyui': {
            'base_url': str,
            'workflow_path': str,
            'timeout': int,
            'poll_interval': int,
            'headers': dict,  # Optional
        },
        'monitors': {
            'count': int,
            'pattern': str,
            'paths': list,  # Optional
            'names': list,  # Optional per-monitor output names
            'command': str,
            'backup_pattern': str,
            'workflows': list,  # Optional
            'templates': list,  # Optional
        },
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
class MonitorConfig:
    """Configuration for monitor management."""
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
    theme: str = "default"
    atoms_dir: str = "atoms"
    use_monitor_seed: bool = True
    default_template: str = "default.prompt"  # Default prompt template
    variations_per_monitor: int = 1


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
        
        # Validate atoms directory name
        if not self.prompt.atoms_dir.isidentifier() and self.prompt.atoms_dir != 'atoms':
            raise ConfigError(f"Invalid atoms directory name: {self.prompt.atoms_dir}")
        
        # Validate logging settings
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.level.upper() not in valid_levels:
            raise ConfigError(f"Log level must be one of: {valid_levels}")
    
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
        required_dirs = ["atoms", "workflows", "prompts"]
        
        # Copy missing files
        for required_file in required_files:
            src = source_dir / required_file
            dst = target_dir / required_file
            
            if not dst.exists() and src.exists():
                cls._copy_file_mutable(src, dst)
                logger.info(f"Copied default config: {required_file}")
        
        # Copy missing directories
        for required_dir in required_dirs:
            src_dir = source_dir / required_dir
            dst_dir = target_dir / required_dir
            
            if src_dir.exists():
                # Create directory if needed
                dst_dir.mkdir(parents=True, exist_ok=True)
                os.chmod(dst_dir, 0o755)  # rwxr-xr-x
                
                # Copy all files from source (overwrite if source is newer or dest is read-only)
                for src_file in src_dir.iterdir():
                    if src_file.is_file():
                        dst_file = dst_dir / src_file.name
                        
                        should_copy = False
                        if not dst_file.exists():
                            should_copy = True
                            reason = "missing"
                        elif not os.access(dst_file, os.W_OK):
                            # Destination exists but is read-only (Nix store leftover)
                            should_copy = True
                            reason = "read-only, fixing"
                            # Remove the read-only file first
                            try:
                                dst_file.unlink()
                            except OSError as e:
                                logger.warning(f"Failed to remove read-only file {dst_file}: {e}")
                        
                        if should_copy:
                            try:
                                cls._copy_file_mutable(src_file, dst_file)
                                logger.debug(f"Copied {src_file.name} ({reason})")
                            except ConfigError as e:
                                logger.error(f"Failed to copy {src_file.name}: {e}")
                                # Continue with other files but don't fail completely
                
                # Final permission fix for any remaining read-only files
                for file_path in dst_dir.rglob('*'):
                    if file_path.is_file() and not os.access(file_path, os.W_OK):
                        try:
                            # Try to fix permissions in place
                            os.chmod(file_path, 0o644)
                        except PermissionError:
                            try:
                                # If that fails, replace the file
                                content = file_path.read_bytes()
                                file_path.unlink()
                                file_path.write_bytes(content)
                                os.chmod(file_path, 0o644)
                                logger.debug(f"Replaced read-only file: {file_path.name}")
                            except OSError as e:
                                logger.warning(f"Failed to fix permissions for {file_path.name}: {e}")
                        except OSError as e:
                            logger.warning(f"Failed to fix permissions for {file_path.name}: {e}")
                
                logger.info(f"Initialized directory: {required_dir}")
    
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
        
        # Create Config instance with dataclass fields
        config = cls(
            comfyui=comfyui_config,
            monitors=monitors_config,
            output=output_config,
            prompt=prompt_config,
            logging=logging_config
        )
        
        return config
    
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
