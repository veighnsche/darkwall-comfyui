"""
DarkWall ComfyUI - Deterministic dark-mode wallpaper generator.

Generate deterministic dark-mode wallpapers using ComfyUI with
time-based prompts and multi-monitor support.
"""

__version__ = "0.1.0"
__author__ = "Vince"

from .config import (
    Config,
    ConfigV2,
    StateManager,
    NamedStateManager,
    MonitorsConfig,
    PerMonitorConfig,
    WorkflowConfig,  # TEAM_002: REQ-WORKFLOW-002
)
from .prompt_generator import PromptGenerator
from .comfy import ComfyClient, WorkflowManager
from .wallpaper import WallpaperTarget
from .schedule import ScheduleConfig, ThemeScheduler, ThemeResult  # TEAM_003: REQ-SCHED-002
from .notifications import NotificationConfig, NotificationSender  # TEAM_004: REQ-MISC-001

# Export all exceptions for external use
from .exceptions import (
    DarkWallError,
    ConfigError,
    ConfigValidationError,
    ConfigMigrationError,
    WorkflowError,
    WorkflowNotFoundError,
    WorkflowValidationError,
    GenerationError,
    ComfyClientError,
    ComfyConnectionError,
    ComfyTimeoutError,
    ComfyGenerationError,
    CommandError,
    CommandNotFoundError,
    CommandTimeoutError,
    CommandPermissionError,
    PromptError,
    TemplateNotFoundError,
    AtomFileError,
    TemplateParseError,
    StateError,
    MonitorDetectionError,
    CompositorNotFoundError,
    CompositorCommunicationError,
    NoMonitorsDetectedError,
    ScheduleError,
    SolarCalculationError,
    NotificationError,
)

# Monitor detection module (may not be available in cached builds)
try:
    from .monitor_detection import (
        MonitorDetector,
        Monitor,
        detect_monitors,
        get_monitor_names,
    )
    _HAS_MONITOR_DETECTION = True
except ImportError:
    _HAS_MONITOR_DETECTION = False
    MonitorDetector = None  # type: ignore
    Monitor = None  # type: ignore
    detect_monitors = None  # type: ignore
    get_monitor_names = None  # type: ignore

__all__ = [
    # Config
    "Config",
    "ConfigV2",
    "StateManager",
    "NamedStateManager",
    "MonitorsConfig",
    "PerMonitorConfig",
    "WorkflowConfig",
    # Schedule
    "ScheduleConfig",
    "ThemeScheduler",
    "ThemeResult",
    # Notifications
    "NotificationConfig",
    "NotificationSender",
    # Core
    "PromptGenerator", 
    "ComfyClient",
    "WorkflowManager",
    "WallpaperTarget",
    # Monitor detection
    "MonitorDetector",
    "Monitor",
    "detect_monitors",
    "get_monitor_names",
    # Exceptions - Base
    "DarkWallError",
    # Exceptions - Config
    "ConfigError",
    "ConfigValidationError",
    "ConfigMigrationError",
    # Exceptions - Workflow
    "WorkflowError",
    "WorkflowNotFoundError",
    "WorkflowValidationError",
    # Exceptions - Generation
    "GenerationError",
    "ComfyClientError",
    "ComfyConnectionError",
    "ComfyTimeoutError",
    "ComfyGenerationError",
    # Exceptions - Command
    "CommandError",
    "CommandNotFoundError",
    "CommandTimeoutError",
    "CommandPermissionError",
    # Exceptions - Prompt
    "PromptError",
    "TemplateNotFoundError",
    "AtomFileError",
    "TemplateParseError",
    # Exceptions - State
    "StateError",
    # Exceptions - Monitor Detection
    "MonitorDetectionError",
    "CompositorNotFoundError",
    "CompositorCommunicationError",
    "NoMonitorsDetectedError",
    # Exceptions - Schedule
    "ScheduleError",
    "SolarCalculationError",
    # Exceptions - Notifications
    "NotificationError",
]
