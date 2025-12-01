"""
Main Config class for DarkWall ComfyUI.

TEAM_007: Split from monolithic config.py for better organization.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass, field

try:
    import tomli
except ImportError:
    raise ImportError("Required package 'tomli' not found. Install with: pip install tomli")

from ..exceptions import ConfigError, ConfigValidationError

from .dataclasses import (
    CleanupPolicy,
    WeightedWorkflow,
    ThemeConfig,
    WorkflowConfig,
    PerMonitorConfig,
    MonitorsConfig,
    ComfyUIConfig,
    PromptConfig,
    LoggingConfig,
    HistoryConfig,
)
from .validation import (
    URL_PATTERN,
    validate_toml_structure,
)

if TYPE_CHECKING:
    from ..schedule import ScheduleConfig
    from ..notifications import NotificationConfig


@dataclass
class Config:
    """
    Main configuration class for DarkWall ComfyUI.
    
    TEAM_006: Merged ConfigV2 into Config. Uses per-monitor format with MonitorsConfig.
    TEAM_007: Split into config/ package for better organization.
    
    Configuration is loaded from TOML files with environment variable overrides.
    """
    
    comfyui: ComfyUIConfig = field(default_factory=ComfyUIConfig)
    monitors: MonitorsConfig = field(default_factory=MonitorsConfig)
    active_monitors: List[str] = field(default_factory=list)
    prompt: PromptConfig = field(default_factory=PromptConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    history: HistoryConfig = field(default_factory=HistoryConfig)
    # TEAM_001: Theme definitions - maps theme name to ThemeConfig
    themes: Dict[str, ThemeConfig] = field(default_factory=dict)
    # TEAM_002: Workflow definitions with optional prompt filtering
    workflows: Dict[str, WorkflowConfig] = field(default_factory=dict)
    # TEAM_003: Schedule configuration for theme switching
    schedule: Optional['ScheduleConfig'] = None
    # TEAM_004: Notifications configuration
    notifications: Optional['NotificationConfig'] = None
    
    def __post_init__(self) -> None:
        """Validate and post-process configuration."""
        # Validate ComfyUI settings
        if not URL_PATTERN.match(self.comfyui.base_url):
            raise ConfigValidationError(
                f"Invalid base URL format: {self.comfyui.base_url}\n"
                "Expected format: http://hostname:port or https://hostname"
            )
        
        if self.comfyui.timeout <= 0:
            raise ConfigValidationError(
                f"Generation timeout ({self.comfyui.timeout}s) must be positive."
            )
        
        if self.comfyui.poll_interval <= 0 or self.comfyui.poll_interval > 60:  # Max 1 minute
            raise ConfigValidationError(
                f"Poll interval ({self.comfyui.poll_interval}s) out of range.\n"
                "Must be between 1 and 60 seconds."
            )
        
        # Validate prompt settings
        if self.prompt.time_slot_minutes <= 0 or self.prompt.time_slot_minutes > 1440:
            raise ConfigValidationError(
                f"Time slot minutes ({self.prompt.time_slot_minutes}) out of range.\n"
                "Must be between 1 and 1440 (24 hours)."
            )
        
        if getattr(self.prompt, 'variations_per_monitor', 1) <= 0 or getattr(self.prompt, 'variations_per_monitor', 1) > 20:
            raise ConfigValidationError(
                f"variations_per_monitor out of range.\n"
                "Must be between 1 and 20."
            )
        
        # Validate logging settings
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.level.upper() not in valid_levels:
            raise ConfigValidationError(
                f"Invalid log level: {self.logging.level}\n"
                f"Must be one of: {valid_levels}"
            )
    
    def get_monitor_config(self, name: str) -> Optional[PerMonitorConfig]:
        """Get configuration for a specific monitor."""
        return self.monitors.get_monitor(name)
    
    def get_active_monitor_names(self) -> List[str]:
        """Get list of active (connected & configured) monitor names."""
        return self.active_monitors
    
    def get_workflow_for_monitor(self, name: str, theme: Optional[ThemeConfig] = None) -> Optional[Path]:
        """Get workflow path for a monitor."""
        monitor = self.monitors.get_monitor(name)
        if monitor:
            return monitor.get_workflow_path(self.get_config_dir(), theme)
        return None
    
    def get_workflow_config(self, workflow_id: str) -> Optional[WorkflowConfig]:
        """Get workflow configuration by ID."""
        return self.workflows.get(workflow_id)
    
    def get_eligible_prompts_for_workflow(self, workflow_id: str, available_prompts: List[str]) -> List[str]:
        """Get eligible prompts for a workflow, applying optional filtering."""
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
    
    def get_theme(self, theme_name: Optional[str] = None) -> ThemeConfig:
        """
        Get theme configuration by name.
        
        Args:
            theme_name: Theme name to look up (defaults to prompt.theme)
            
        Returns:
            ThemeConfig for the requested theme
            
        Raises:
            ConfigError: If no themes are configured or theme not found
        """
        name = theme_name or self.prompt.theme
        
        if not self.themes:
            raise ConfigError(
                "No themes configured. Add [themes.{name}] sections to config.toml"
            )
        
        if name in self.themes:
            return self.themes[name]
        
        # Fallback to first available theme with warning
        first_theme = next(iter(self.themes.values()))
        logging.getLogger(__name__).warning(
            f"Theme '{name}' not found, using '{first_theme.name}'"
        )
        return first_theme
    
    def get_theme_atoms_path(self, theme_name: Optional[str] = None) -> Path:
        """Get atoms directory path for a theme."""
        theme = self.get_theme(theme_name)
        return theme.get_atoms_path(self.get_config_dir())
    
    def get_theme_prompts_path(self, theme_name: Optional[str] = None) -> Path:
        """Get prompts directory path for a theme."""
        theme = self.get_theme(theme_name)
        return theme.get_prompts_path(self.get_config_dir())
    
    @classmethod
    def get_config_dir(cls) -> Path:
        """
        Get user configuration directory.
        
        Uses XDG_CONFIG_HOME if set, otherwise defaults to ~/.config.
        """
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / "darkwall-comfyui"
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
        """
        try:
            content = src.read_bytes()
            dst.write_bytes(content)
            os.chmod(dst, 0o644)  # rw-r--r--
        except OSError as e:
            raise ConfigError(f"Failed to copy file from {src} to {dst}: {e}")
        except Exception as e:
            raise ConfigError(f"Unexpected error copying file from {src} to {dst}: {e}")
    
    @classmethod
    def _copy_config_files(cls, source_dir: Path, target_dir: Path) -> None:
        """Copy config files from source to target directory."""
        logger = logging.getLogger(__name__)
        
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(target_dir, 0o755)  # rwxr-xr-x
        except OSError as e:
            raise ConfigError(f"Failed to create config directory {target_dir}: {e}")
        
        required_files = ["config.toml"]
        required_dirs = ["workflows", "themes"]
        
        for required_file in required_files:
            src = source_dir / required_file
            dst = target_dir / required_file
            
            if not dst.exists() and src.exists():
                cls._copy_file_mutable(src, dst)
                logger.info(f"Copied default config: {required_file}")
        
        for required_dir in required_dirs:
            src_dir = source_dir / required_dir
            dst_dir = target_dir / required_dir
            
            if src_dir.exists():
                cls._copy_directory_recursive(src_dir, dst_dir, logger)
                logger.info(f"Initialized directory: {required_dir}")
    
    @classmethod
    def _copy_directory_recursive(cls, src_dir: Path, dst_dir: Path, log: 'logging.Logger') -> None:
        """Recursively copy a directory, handling Nix store read-only files."""
        dst_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(dst_dir, 0o755)
        except OSError:
            pass
        
        for src_item in src_dir.iterdir():
            dst_item = dst_dir / src_item.name
            
            if src_item.is_dir():
                cls._copy_directory_recursive(src_item, dst_item, log)
            elif src_item.is_file():
                should_copy = False
                reason = ""
                
                if not dst_item.exists():
                    should_copy = True
                    reason = "missing"
                elif not os.access(dst_item, os.W_OK):
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
    def load(
        cls,
        config_file: Optional[Path] = None,
        initialize: bool = True,
        detect_monitors: bool = True,
    ) -> 'Config':
        """
        Load configuration from TOML file with monitor auto-detection.
        
        REQ-MONITOR-001: Auto-detect monitors from compositor
        REQ-MONITOR-003: Use [monitors.{name}] sections
        REQ-MONITOR-012: Handle unconfigured monitors (skip with warning)
        REQ-MONITOR-013: Handle disconnected monitors (warn and skip)
        
        Args:
            config_file: Optional path to config TOML file
            initialize: Whether to initialize config directory with defaults
            detect_monitors: Whether to auto-detect monitors from compositor
            
        Returns:
            Config instance with loaded settings
        """
        logger = logging.getLogger(__name__)
        
        if initialize:
            cls.initialize_config()
        
        if not config_file:
            config_file = cls.get_config_dir() / "config.toml"
        
        config_dict = {}
        if config_file.exists():
            try:
                with open(config_file, 'rb') as f:
                    config_dict = tomli.load(f)
                
                validate_toml_structure(config_dict, config_file)
                
                logger.info(f"Loaded config from {config_file}")
            except (tomli.TOMLDecodeError, OSError, ConfigError) as e:
                if isinstance(e, ConfigError):
                    raise
                logger.warning(f"Failed to load config: {e}")
        
        # Parse monitors section
        monitors_dict = config_dict.get('monitors', {})
        monitors_config = MonitorsConfig.from_dict(monitors_dict)
        
        # Auto-detect connected monitors
        detected_monitors: List[str] = []
        if detect_monitors:
            try:
                from ..monitor_detection import detect_monitors as do_detect
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
        
        # Parse other sections
        comfyui_config = ComfyUIConfig(**config_dict.get('comfyui', {}))
        
        # Filter prompt config to only known fields (ignore deprecated atoms_dir)
        prompt_dict = config_dict.get('prompt', {})
        prompt_fields = {'time_slot_minutes', 'theme', 'use_monitor_seed', 'default_template', 'variations_per_monitor'}
        filtered_prompt = {k: v for k, v in prompt_dict.items() if k in prompt_fields}
        prompt_config = PromptConfig(**filtered_prompt)
        
        logging_config = LoggingConfig(**config_dict.get('logging', {}))
        
        # Parse themes
        themes_dict: Dict[str, ThemeConfig] = {}
        if 'themes' in config_dict:
            for theme_name, theme_data in config_dict['themes'].items():
                if isinstance(theme_data, dict):
                    workflows_list = None
                    if 'workflows' in theme_data:
                        workflows_list = [
                            WeightedWorkflow.from_config(w) for w in theme_data['workflows']
                        ]
                    
                    themes_dict[theme_name] = ThemeConfig(
                        name=theme_name,
                        atoms_dir=theme_data.get('atoms_dir', 'atoms'),
                        prompts_dir=theme_data.get('prompts_dir', 'prompts'),
                        default_template=theme_data.get('default_template', 'default.prompt'),
                        workflow_prefix=theme_data.get('workflow_prefix'),
                        workflows=workflows_list,
                    )
                else:
                    themes_dict[theme_name] = ThemeConfig(name=theme_name)
        
        # Parse workflows section
        workflows_dict: Dict[str, WorkflowConfig] = {}
        if 'workflows' in config_dict:
            for workflow_name, workflow_data in config_dict['workflows'].items():
                if isinstance(workflow_data, dict):
                    workflows_dict[workflow_name] = WorkflowConfig(
                        name=workflow_name,
                        prompts=workflow_data.get('prompts'),
                    )
                else:
                    workflows_dict[workflow_name] = WorkflowConfig(name=workflow_name)
        
        # Parse schedule section
        schedule_config = None
        if 'schedule' in config_dict:
            from ..schedule import ScheduleConfig, WeightedTheme
            sched_data = config_dict['schedule']
            
            day_themes = None
            if 'day_themes' in sched_data:
                day_themes = [
                    WeightedTheme.from_config(t) for t in sched_data['day_themes']
                ]
            
            night_themes = None
            if 'night_themes' in sched_data:
                night_themes = [
                    WeightedTheme.from_config(t) for t in sched_data['night_themes']
                ]
            
            schedule_config = ScheduleConfig(
                latitude=sched_data.get('latitude'),
                longitude=sched_data.get('longitude'),
                day_theme=sched_data.get('day_theme', 'default'),
                night_theme=sched_data.get('night_theme', 'nsfw'),
                day_themes=day_themes,
                night_themes=night_themes,
                nsfw_start=sched_data.get('nsfw_start'),
                nsfw_end=sched_data.get('nsfw_end'),
                blend_duration_minutes=sched_data.get('blend_duration_minutes', 30),
                timezone=sched_data.get('timezone'),
            )
        
        # Parse notifications section
        notifications_config = None
        if 'notifications' in config_dict:
            from ..notifications import NotificationConfig
            notif_data = config_dict['notifications']
            notifications_config = NotificationConfig(
                enabled=notif_data.get('enabled', False),
                show_preview=notif_data.get('show_preview', True),
                timeout_ms=notif_data.get('timeout_ms', 5000),
                urgency=notif_data.get('urgency', 'normal'),
            )
        
        return cls(
            comfyui=comfyui_config,
            monitors=monitors_config,
            active_monitors=active_monitors,
            prompt=prompt_config,
            logging=logging_config,
            themes=themes_dict,
            workflows=workflows_dict,
            schedule=schedule_config,
            notifications=notifications_config,
        )
