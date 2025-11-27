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
            'command': str,
            'backup_pattern': str,
            'workflows': list,  # Optional
        },
        'output': {
            'create_backup': bool,
        },
        'prompt': {
            'time_slot_minutes': int,
            'theme': str,
            'atoms_dir': str,
            'use_monitor_seed': bool,
        },
        'logging': {
            'level': str,
            'verbose': bool,
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


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    verbose: bool = False


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
        
        # Validate prompt settings
        if self.prompt.time_slot_minutes <= 0 or self.prompt.time_slot_minutes > 1440:
            raise ConfigError("Time slot minutes must be between 1 and 1440")
        
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
        """
        # Read content from source (works even if source is read-only)
        content = src.read_bytes()
        # Write to destination (creates with default permissions)
        dst.write_bytes(content)
        # Explicitly set write permissions
        os.chmod(dst, 0o644)  # rw-r--r--
    
    @classmethod
    def _copy_config_files(cls, source_dir: Path, target_dir: Path) -> None:
        """
        Copy config files from source to target directory.
        
        Uses read/write instead of shutil.copy2 to avoid inheriting
        read-only permissions from Nix store.
        
        Args:
            source_dir: Source config directory
            target_dir: Target user config directory
        """
        logger = logging.getLogger(__name__)
        
        # Ensure target directory has proper permissions
        target_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(target_dir, 0o755)  # rwxr-xr-x
        
        # Files that should always be present
        required_files = ["config.toml"]
        required_dirs = ["atoms", "workflows"]
        
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
                            dst_file.unlink()
                        
                        if should_copy:
                            cls._copy_file_mutable(src_file, dst_file)
                            logger.debug(f"Copied {src_file.name} ({reason})")
                
                # Final permission fix for any remaining read-only files
                for file_path in dst_dir.rglob('*'):
                    if file_path.is_file() and not os.access(file_path, os.W_OK):
                        try:
                            # Try to fix permissions in place
                            os.chmod(file_path, 0o644)
                        except PermissionError:
                            # If that fails, replace the file
                            content = file_path.read_bytes()
                            file_path.unlink()
                            file_path.write_bytes(content)
                            os.chmod(file_path, 0o644)
                            logger.debug(f"Replaced read-only file: {file_path.name}")
                
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
            overrides.setdefault('comfyui', {})['timeout'] = int(os.environ['COMFYUI_TIMEOUT'])
        
        if 'COMFYUI_POLL_INTERVAL' in os.environ:
            overrides.setdefault('comfyui', {})['poll_interval'] = int(os.environ['COMFYUI_POLL_INTERVAL'])
        
        # Monitor settings
        if 'MONITOR_COUNT' in os.environ:
            overrides.setdefault('monitors', {})['count'] = int(os.environ['MONITOR_COUNT'])
        
        if 'MONITOR_PATTERN' in os.environ:
            overrides.setdefault('monitors', {})['pattern'] = os.environ['MONITOR_PATTERN']
        
        if 'WALLPAPER_COMMAND' in os.environ:
            overrides.setdefault('monitors', {})['command'] = os.environ['WALLPAPER_COMMAND']
        
        # Prompt settings
        if 'TIME_SLOT_MINUTES' in os.environ:
            overrides.setdefault('prompt', {})['time_slot_minutes'] = int(os.environ['TIME_SLOT_MINUTES'])
        
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
            },
            'logging': {
                'level': self.logging.level,
                'verbose': self.logging.verbose,
            },
        }
        
        # Add optional fields
        if self.monitors.paths:
            config_dict['monitors']['paths'] = self.monitors.paths
        
        if self.comfyui.headers:
            config_dict['comfyui']['headers'] = self.comfyui.headers
        
        # Ensure directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'wb') as f:
            tomli_w.dump(config_dict, f)
        
        logging.getLogger(__name__).info(f"Saved config to {config_file}")


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
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            self.logger.warning(f"Failed to load state file: {e}")
            return {'last_monitor_index': -1, 'rotation_count': 0}
    
    def save_state(self, state: Dict[str, Any]) -> None:
        """Save current state."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except (OSError, PermissionError) as e:
            self.logger.error(f"Failed to save state file: {e}")
    
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
