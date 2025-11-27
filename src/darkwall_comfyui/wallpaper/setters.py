"""
Wallpaper setter implementations for various desktop environments.

Each setter handles the specifics of setting wallpapers for its target
environment (Wayland compositors, X11, etc.).
"""

import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class WallpaperSetter(ABC):
    """Abstract base class for wallpaper setters."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def set(self, image_path: Path, monitor_index: int, monitor_name: Optional[str] = None) -> bool:
        """
        Set wallpaper for a specific monitor.
        
        Args:
            image_path: Path to wallpaper image
            monitor_index: Monitor index (0-based)
            monitor_name: Optional monitor name (e.g., "DP-1")
            
        Returns:
            True if successful
        """
        pass
    
    def _run_command(self, cmd: list[str], timeout: int = 30) -> bool:
        """Run a command and return success status."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode != 0:
                self.logger.error(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
                return False
            return True
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {' '.join(cmd)}")
            return False
        except FileNotFoundError:
            self.logger.error(f"Command not found: {cmd[0]}")
            return False
        except Exception as e:
            self.logger.error(f"Command error: {e}")
            return False


class SwwwSetter(WallpaperSetter):
    """Wallpaper setter using swww (Wayland)."""
    
    def set(self, image_path: Path, monitor_index: int, monitor_name: Optional[str] = None) -> bool:
        name = monitor_name or self._default_monitor_name(monitor_index)
        cmd = ["swww", "img", str(image_path), "--outputs", name, "--resize", "crop"]
        
        if self._run_command(cmd):
            self.logger.info(f"Set wallpaper on {name} via swww")
            return True
        return False
    
    def _default_monitor_name(self, index: int) -> str:
        names = ["eDP-1", "DP-1", "DP-2", "HDMI-A-1", "HDMI-A-2"]
        return names[index] if index < len(names) else f"DP-{index}"


class SwaybgSetter(WallpaperSetter):
    """Wallpaper setter using swaybg (Sway/Wayland)."""
    
    def set(self, image_path: Path, monitor_index: int, monitor_name: Optional[str] = None) -> bool:
        name = monitor_name or self._default_monitor_name(monitor_index)
        cmd = ["swaybg", "--output", name, "--mode", "fill", "--image", str(image_path)]
        
        if self._run_command(cmd):
            self.logger.info(f"Set wallpaper on {name} via swaybg")
            return True
        return False
    
    def _default_monitor_name(self, index: int) -> str:
        names = ["eDP-1", "DP-1", "DP-2", "HDMI-A-1", "HDMI-A-2"]
        return names[index] if index < len(names) else f"DP-{index}"


class FehSetter(WallpaperSetter):
    """Wallpaper setter using feh (X11)."""
    
    def set(self, image_path: Path, monitor_index: int, monitor_name: Optional[str] = None) -> bool:
        # feh sets all monitors at once, monitor_index is ignored
        cmd = ["feh", "--bg-fill", str(image_path)]
        
        if self._run_command(cmd):
            self.logger.info("Set wallpaper via feh")
            return True
        return False


class NitrogenSetter(WallpaperSetter):
    """Wallpaper setter using nitrogen (X11)."""
    
    def set(self, image_path: Path, monitor_index: int, monitor_name: Optional[str] = None) -> bool:
        cmd = ["nitrogen", "--set-zoom-fill", str(image_path)]
        
        if self._run_command(cmd):
            self.logger.info("Set wallpaper via nitrogen")
            return True
        return False


class CustomSetter(WallpaperSetter):
    """Wallpaper setter using a custom command template."""
    
    def __init__(self, command_template: str):
        super().__init__()
        self.template = command_template
    
    def set(self, image_path: Path, monitor_index: int, monitor_name: Optional[str] = None) -> bool:
        name = monitor_name or f"monitor_{monitor_index}"
        
        try:
            cmd_str = self.template.format(
                path=str(image_path),
                index=monitor_index,
                monitor=name
            )
            cmd = cmd_str.split()
        except KeyError as e:
            self.logger.error(f"Invalid placeholder in custom command: {e}")
            return False
        
        if self._run_command(cmd):
            self.logger.info(f"Set wallpaper via custom command")
            return True
        return False


# Registry of available setters
SETTERS = {
    "swww": SwwwSetter,
    "swaybg": SwaybgSetter,
    "feh": FehSetter,
    "nitrogen": NitrogenSetter,
}


def get_setter(command: str) -> WallpaperSetter:
    """
    Get appropriate wallpaper setter for the given command.
    
    Args:
        command: Setter name ("swww", "swaybg", etc.) or "custom:template"
        
    Returns:
        WallpaperSetter instance
    """
    if command.startswith("custom:"):
        return CustomSetter(command[7:])
    
    if command in SETTERS:
        return SETTERS[command]()
    
    raise ValueError(f"Unknown wallpaper command: {command}. Available: {list(SETTERS.keys())}")
