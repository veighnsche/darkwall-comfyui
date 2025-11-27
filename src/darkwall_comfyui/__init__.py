"""
DarkWall ComfyUI - Deterministic dark-mode wallpaper generator.

Generate deterministic dark-mode wallpapers using ComfyUI with
time-based prompts and multi-monitor support.
"""

__version__ = "0.1.0"
__author__ = "Vince"

from .config import Config, StateManager
from .prompt_generator import PromptGenerator
from .comfy import ComfyClient, WorkflowManager
from .wallpaper import WallpaperTarget

__all__ = [
    "Config",
    "StateManager",
    "PromptGenerator", 
    "ComfyClient",
    "WorkflowManager",
    "WallpaperTarget",
]
