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
    
    def __init__(self) -> None:
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
    
    def _run_command(self, cmd: list[str], timeout: int = 30, background: bool = False) -> bool:
        """
        Run a command and return success status.
        
        Args:
            cmd: Command to run as list of strings
            timeout: Timeout in seconds for foreground commands
            background: Whether to run command in background
            
        Returns:
            True if command succeeded
            
        Raises:
            CommandError: If command execution fails critically
        """
        cmd_str = ' '.join(cmd)  # For logging purposes
        
        try:
            if background:
                # Use subprocess.Popen to run in background without waiting
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                
                # Give it a moment to start and check if it's still running
                import time
                time.sleep(0.5)
                
                if process.poll() is None:
                    # Process is still running (expected for background daemons)
                    self.logger.debug(f"Background command started: {cmd_str}")
                    return True
                else:
                    # Process exited immediately (error)
                    self.logger.error(f"Background command failed to start: {cmd_str}")
                    return False
            else:
                self.logger.debug(f"Running command: {cmd_str}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                
                if result.returncode != 0:
                    error_msg = f"Command failed with exit code {result.returncode}: {cmd_str}"
                    if result.stderr:
                        error_msg += f"\nStderr: {result.stderr.strip()}"
                    elif result.stdout:
                        error_msg += f"\nStdout: {result.stdout.strip()}"
                    
                    self.logger.error(error_msg)
                    return False
                
                self.logger.debug(f"Command succeeded: {cmd_str}")
                return True
                
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Command timed out after {timeout}s: {cmd_str}")
            return False
        except FileNotFoundError as e:
            self.logger.error(f"Command not found: {cmd[0]} - ensure {cmd[0]} is installed and in PATH")
            return False
        except PermissionError as e:
            self.logger.error(f"Permission denied executing command: {cmd_str}: {e}")
            return False
        except OSError as e:
            self.logger.error(f"OS error executing command {cmd_str}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error executing command {cmd_str}: {e}")
            return False
    
    def _default_monitor_name(self, index: int) -> str:
        """Get default monitor name for index."""
        names = ["eDP-1", "DP-1", "DP-2", "HDMI-A-1", "HDMI-A-2"]
        return names[index] if index < len(names) else f"DP-{index}"


class SwwwSetter(WallpaperSetter):
    """Wallpaper setter using swww (Wayland)."""
    
    def set(self, image_path: Path, monitor_index: int, monitor_name: Optional[str] = None) -> bool:
        """
        Set wallpaper for a specific monitor.
        
        Args:
            image_path: Path to wallpaper image
            monitor_index: Monitor index (0-based)
            monitor_name: Optional monitor name (e.g., "DP-1")
            
        Returns:
            True if successful
            
        Raises:
            CommandError: If wallpaper setting fails critically
        """
        try:
            name = monitor_name or self._default_monitor_name(monitor_index)
            cmd = ["swww", "img", str(image_path), "--outputs", name, "--resize", "crop"]
            
            if self._run_command(cmd):
                self.logger.info(f"Set wallpaper on {name} via swww")
                return True
            else:
                self.logger.error(f"Failed to set wallpaper on {name} via swww")
                return False
                
        except Exception as e:
            self.logger.error(f"Unexpected error setting wallpaper via swww: {e}")
            return False


class SwaybgSetter(WallpaperSetter):
    """Wallpaper setter using swaybg (Sway/Wayland)."""
    
    def set(self, image_path: Path, monitor_index: int, monitor_name: Optional[str] = None) -> bool:
        """
        Set wallpaper for a specific monitor.
        
        Args:
            image_path: Path to wallpaper image
            monitor_index: Monitor index (0-based)
            monitor_name: Optional monitor name (e.g., "DP-1")
            
        Returns:
            True if successful
            
        Raises:
            CommandError: If wallpaper setting fails critically
        """
        try:
            name = monitor_name or self._default_monitor_name(monitor_index)
            
            # Validate image path exists
            if not image_path.exists():
                self.logger.error(f"Image file does not exist: {image_path}")
                return False
            
            # Kill existing swaybg processes for this monitor to avoid conflicts
            self._kill_existing_swaybg(name)
            
            # Run swaybg in background since it's a persistent daemon
            cmd = ["swaybg", "--output", name, "--mode", "fill", "--image", str(image_path)]
            
            if self._run_command(cmd, background=True):
                self.logger.info(f"Set wallpaper on {name} via swaybg (background)")
                return True
            else:
                self.logger.error(f"Failed to set wallpaper on {name} via swaybg")
                return False
                
        except Exception as e:
            self.logger.error(f"Unexpected error setting wallpaper via swaybg: {e}")
            return False
    
    def _kill_existing_swaybg(self, monitor_name: str) -> None:
        """
        Kill existing swaybg processes for the specific monitor.
        
        Args:
            monitor_name: Monitor output name (e.g., "DP-1")
        """
        try:
            # TEAM_565: Kill swaybg processes for this monitor
            # Try both short (-o) and long (--output) forms since different launchers use different forms
            for pattern in [f"swaybg.*-o {monitor_name}", f"swaybg.*--output {monitor_name}"]:
                result = subprocess.run(
                    ["pkill", "-f", pattern],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    self.logger.debug(f"Killed swaybg matching pattern: {pattern}")
            
            # Also use the original simple pattern for backwards compat
            result = subprocess.run(
                ["pkill", "-f", f"swaybg -o {monitor_name}"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                self.logger.debug(f"Killed existing swaybg processes for monitor {monitor_name}")
            else:
                self.logger.debug(f"No existing swaybg processes found for {monitor_name}")
                        
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Timeout killing swaybg processes for {monitor_name}")
        except FileNotFoundError:
            self.logger.warning("pkill command not found - cannot kill existing swaybg processes")
        except Exception as e:
            self.logger.warning(f"Failed to kill swaybg processes for {monitor_name}: {e}")


class FehSetter(WallpaperSetter):
    """Wallpaper setter using feh (X11)."""
    
    def set(self, image_path: Path, monitor_index: int, monitor_name: Optional[str] = None) -> bool:
        """
        Set wallpaper for a specific monitor.
        
        Args:
            image_path: Path to wallpaper image
            monitor_index: Monitor index (0-based) - ignored for feh
            monitor_name: Optional monitor name (e.g., "DP-1") - ignored for feh
            
        Returns:
            True if successful
            
        Raises:
            CommandError: If wallpaper setting fails critically
        """
        try:
            # Validate image path exists
            if not image_path.exists():
                self.logger.error(f"Image file does not exist: {image_path}")
                return False
            
            # feh sets all monitors at once, monitor_index is ignored
            cmd = ["feh", "--bg-fill", str(image_path)]
            
            if self._run_command(cmd):
                self.logger.info("Set wallpaper via feh")
                return True
            else:
                self.logger.error("Failed to set wallpaper via feh")
                return False
                
        except Exception as e:
            self.logger.error(f"Unexpected error setting wallpaper via feh: {e}")
            return False


class NitrogenSetter(WallpaperSetter):
    """Wallpaper setter using nitrogen (X11)."""
    
    def set(self, image_path: Path, monitor_index: int, monitor_name: Optional[str] = None) -> bool:
        """
        Set wallpaper for a specific monitor.
        
        Args:
            image_path: Path to wallpaper image
            monitor_index: Monitor index (0-based) - ignored for nitrogen
            monitor_name: Optional monitor name (e.g., "DP-1") - ignored for nitrogen
            
        Returns:
            True if successful
            
        Raises:
            CommandError: If wallpaper setting fails critically
        """
        try:
            # Validate image path exists
            if not image_path.exists():
                self.logger.error(f"Image file does not exist: {image_path}")
                return False
            
            cmd = ["nitrogen", "--set-zoom-fill", str(image_path)]
            
            if self._run_command(cmd):
                self.logger.info("Set wallpaper via nitrogen")
                return True
            else:
                self.logger.error("Failed to set wallpaper via nitrogen")
                return False
                
        except Exception as e:
            self.logger.error(f"Unexpected error setting wallpaper via nitrogen: {e}")
            return False


class CustomSetter(WallpaperSetter):
    """Wallpaper setter using a custom command template."""
    
    def __init__(self, command_template: str) -> None:
        super().__init__()
        self.template = command_template
    
    def set(self, image_path: Path, monitor_index: int, monitor_name: Optional[str] = None) -> bool:
        """
        Set wallpaper using a custom command template.
        
        Args:
            image_path: Path to wallpaper image
            monitor_index: Monitor index (0-based)
            monitor_name: Optional monitor name (e.g., "DP-1")
            
        Returns:
            True if successful
            
        Raises:
            CommandError: If command formatting or execution fails
        """
        try:
            # Validate image path exists
            if not image_path.exists():
                self.logger.error(f"Image file does not exist: {image_path}")
                return False
            
            try:
                cmd_str = self.template.format(
                    path=str(image_path),
                    index=monitor_index,
                    name=monitor_name or f"DP-{monitor_index}"
                )
                cmd = cmd_str.split()
            except KeyError as e:
                self.logger.error(f"Invalid placeholder in custom command template: {e}")
                self.logger.error(f"Available placeholders: {{path}}, {{index}}, {{name}}")
                return False
            except (ValueError, AttributeError) as e:
                self.logger.error(f"Error formatting custom command template: {e}")
                return False
            
            if self._run_command(cmd):
                self.logger.info(f"Set wallpaper via custom command: {cmd_str}")
                return True
            else:
                self.logger.error(f"Failed to set wallpaper via custom command: {cmd_str}")
                return False
                
        except Exception as e:
            self.logger.error(f"Unexpected error setting wallpaper via custom command: {e}")
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
