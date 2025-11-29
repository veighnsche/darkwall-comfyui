"""
DarkWall ComfyUI - Deterministic dark-mode wallpaper generator.

Generate deterministic dark-mode wallpapers using ComfyUI with
time-based prompts and multi-monitor support.
"""

__version__ = "0.1.0"
__author__ = "Vince"

from .config import (
    Config,
    StateManager,
    NamedStateManager,
    MonitorsConfig,
    PerMonitorConfig,
)
from .prompt_generator import PromptGenerator
from .comfy import ComfyClient, WorkflowManager
from .wallpaper import WallpaperTarget

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
    "Config",
    "StateManager",
    "NamedStateManager",
    "MonitorsConfig",
    "PerMonitorConfig",
    "PromptGenerator", 
    "ComfyClient",
    "WorkflowManager",
    "WallpaperTarget",
    "MonitorDetector",
    "Monitor",
    "detect_monitors",
    "get_monitor_names",
]
