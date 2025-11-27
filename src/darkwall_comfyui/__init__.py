"""
DarkWall ComfyUI - Deterministic dark-mode wallpaper generator.

This package provides tools to generate deterministic dark-mode wallpapers
by calling ComfyUI instances with time-based prompts.
"""

__version__ = "0.1.0"
__author__ = "Vince"

from .config import Config
from .prompt_generator import PromptGenerator
from .comfy_client import ComfyClient
from .wallpaper_target import WallpaperTarget

__all__ = [
    "Config",
    "PromptGenerator", 
    "ComfyClient",
    "WallpaperTarget",
]
