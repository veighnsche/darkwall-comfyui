"""
Wallpaper target and output management.

This module handles filesystem operations for saving generated
wallpapers to configured locations and managing the output pipeline
with multi-monitor support and wallpaper setting commands.
"""

import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from .config import Config
from .comfy_client import GenerationResult


class WallpaperTarget:
    """
    Manages wallpaper output paths and filesystem operations.
    
    This class handles:
    - Creating output directories
    - Saving downloaded images to configured paths
    - Managing wallpaper file naming and organization
    - Setting wallpapers using various desktop environment commands
    - Providing feedback on successful saves
    """
    
    def __init__(self, config: Config):
        """Initialize wallpaper target with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Supported wallpaper setting commands (defined here to access self)
        self.WALLPAPER_COMMANDS = {
            'swaybg': self._set_wallpaper_swaybg,
            'swww': self._set_wallpaper_swww,
            'feh': self._set_wallpaper_feh,
            'nitrogen': self._set_wallpaper_nitrogen,
        }
    
    def save_wallpaper(self, image_url: str, filename: str, output_path: Path) -> Path:
        """
        Save wallpaper from ComfyUI to local filesystem.
        
        Args:
            image_url: URL to download the image from
            filename: Original filename from ComfyUI
            output_path: Local path to save image
            
        Returns:
            Path where wallpaper was saved
            
        Raises:
            RuntimeError: If download fails
        """
        self.logger.info(f"Saving wallpaper to: {output_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create backup if enabled
        if self.config.output.create_backup and output_path.exists():
            self._create_backup(output_path)
        
        # Import here to avoid circular imports
        from .comfy_client import ComfyClient
        
        # Use ComfyClient's download method
        comfy_client = ComfyClient(self.config)
        success = comfy_client.download_image(image_url, output_path)
        
        if not success:
            raise RuntimeError(f"Failed to download wallpaper from {image_url}")
        
        # Verify the file was saved and has content
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(f"Wallpaper file not saved properly: {output_path}")
        
        self.logger.info(f"Wallpaper saved successfully: {output_path}")
        return output_path
    
    def _create_backup(self, current_path: Path) -> Optional[Path]:
        """
        Create a backup of the current wallpaper before overwriting.
        
        Args:
            current_path: Path to current wallpaper
            
        Returns:
            Path to backup file if created, None otherwise
        """
        try:
            # Extract monitor index from path for backup naming
            monitor_index = self._extract_monitor_index(current_path)
            
            # Create backup with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.config.monitors.get_backup_path(monitor_index, timestamp)
            
            # Ensure backup directory exists
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            import shutil
            shutil.copy2(current_path, backup_path)
            self.logger.debug(f"Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.warning(f"Failed to create backup: {e}")
            return None
    
    def _extract_monitor_index(self, path: Path) -> int:
        """
        Extract monitor index from wallpaper path.
        
        Args:
            path: Wallpaper path
            
        Returns:
            Monitor index (0-based)
        """
        # Try to extract monitor index from filename
        stem = path.stem
        
        # Look for patterns like "monitor_0", "monitor_1", etc.
        if "monitor_" in stem:
            try:
                parts = stem.split("monitor_")
                if len(parts) > 1:
                    return int(parts[1].split("_")[0])
            except (ValueError, IndexError):
                pass
        
        # Fallback to 0
        return 0
    
    def set_wallpaper(self, wallpaper_path: Path, monitor_index: int) -> bool:
        """
        Set wallpaper using configured command.
        
        Args:
            wallpaper_path: Path to wallpaper image
            monitor_index: Monitor index to set wallpaper for
            
        Returns:
            True if successful, False otherwise
        """
        command = self.config.monitors.command
        
        self.logger.info(f"Setting wallpaper for monitor {monitor_index} using: {command}")
        
        # Handle custom commands
        if command.startswith("custom:"):
            return self._set_wallpaper_custom(wallpaper_path, monitor_index, command[7:])
        
        # Handle built-in commands
        if command in self.WALLPAPER_COMMANDS:
            return self.WALLPAPER_COMMANDS[command](self, wallpaper_path, monitor_index)
        
        self.logger.error(f"Unknown wallpaper command: {command}")
        return False
    
    def _set_wallpaper_swaybg(self, wallpaper_path: Path, monitor_index: int) -> bool:
        """Set wallpaper using swaybg (for Sway/Wayland)."""
        try:
            # Get monitor name or use index
            monitor_name = self._get_monitor_name(monitor_index)
            
            cmd = [
                "swaybg",
                "--output", monitor_name,
                "--image", "fill",
                str(wallpaper_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.logger.error(f"swaybg failed: {result.stderr}")
                return False
            
            self.logger.info(f"Wallpaper set for monitor {monitor_name}")
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("swaybg command timed out")
            return False
        except Exception as e:
            self.logger.error(f"Failed to set wallpaper with swaybg: {e}")
            return False
    
    def _set_wallpaper_swww(self, wallpaper_path: Path, monitor_index: int) -> bool:
        """Set wallpaper using swww (for Wayland)."""
        try:
            # Get monitor name or use index
            monitor_name = self._get_monitor_name(monitor_index)
            
            cmd = [
                "swww",
                "img",
                str(wallpaper_path),
                "--outputs", monitor_name,
                "--resize", "crop"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.logger.error(f"swww failed: {result.stderr}")
                return False
            
            self.logger.info(f"Wallpaper set for monitor {monitor_name}")
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("swww command timed out")
            return False
        except Exception as e:
            self.logger.error(f"Failed to set wallpaper with swww: {e}")
            return False
    
    def _set_wallpaper_feh(self, wallpaper_path: Path, monitor_index: int) -> bool:
        """Set wallpaper using feh (for X11)."""
        try:
            # For feh, we typically set all monitors or use specific geometry
            cmd = [
                "feh",
                "--bg-fill",
                str(wallpaper_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.logger.error(f"feh failed: {result.stderr}")
                return False
            
            self.logger.info(f"Wallpaper set with feh")
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("feh command timed out")
            return False
        except Exception as e:
            self.logger.error(f"Failed to set wallpaper with feh: {e}")
            return False
    
    def _set_wallpaper_nitrogen(self, wallpaper_path: Path, monitor_index: int) -> bool:
        """Set wallpaper using nitrogen."""
        try:
            cmd = [
                "nitrogen",
                "--set-zoom-fill",
                str(wallpaper_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.logger.error(f"nitrogen failed: {result.stderr}")
                return False
            
            self.logger.info(f"Wallpaper set with nitrogen")
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("nitrogen command timed out")
            return False
        except Exception as e:
            self.logger.error(f"Failed to set wallpaper with nitrogen: {e}")
            return False
    
    def _set_wallpaper_custom(self, wallpaper_path: Path, monitor_index: int, command: str) -> bool:
        """Set wallpaper using custom command."""
        try:
            # Replace placeholders in command
            cmd = command.format(
                index=monitor_index,
                path=str(wallpaper_path),
                monitor=self._get_monitor_name(monitor_index)
            )
            
            # Split command into args
            args = cmd.split()
            
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.logger.error(f"Custom command failed: {result.stderr}")
                return False
            
            self.logger.info(f"Wallpaper set with custom command")
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("Custom wallpaper command timed out")
            return False
        except Exception as e:
            self.logger.error(f"Failed to set wallpaper with custom command: {e}")
            return False
    
    def _get_monitor_name(self, monitor_index: int) -> str:
        """
        Get monitor name for the given index.
        
        This is a simplified implementation. In a real scenario,
        you might want to query the display server for actual monitor names.
        
        Args:
            monitor_index: Monitor index
            
        Returns:
            Monitor name string
        """
        # Simple fallback naming
        common_names = ["eDP-1", "DP-1", "DP-2", "HDMI-1", "HDMI-2", "VGA-1"]
        
        if monitor_index < len(common_names):
            return common_names[monitor_index]
        
        # Fallback to generic name
        return f"monitor_{monitor_index}"
    
    def get_wallpaper_info(self, wallpaper_path: Path) -> Dict[str, Any]:
        """
        Get information about a saved wallpaper.
        
        Args:
            wallpaper_path: Path to wallpaper file
            
        Returns:
            Dictionary with file information
        """
        if not wallpaper_path.exists():
            return {"exists": False}
        
        stat = wallpaper_path.stat()
        
        return {
            "exists": True,
            "path": str(wallpaper_path),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": stat.st_mtime,
            "monitor_index": self._extract_monitor_index(wallpaper_path),
        }
    
    def list_wallpapers(self) -> List[Dict[str, Any]]:
        """
        List all generated wallpapers for all monitors.
        
        Returns:
            List of wallpaper information dictionaries
        """
        wallpapers = []
        
        for monitor_index in range(self.config.monitors.count):
            wallpaper_path = self.config.monitors.get_output_path(monitor_index)
            info = self.get_wallpaper_info(wallpaper_path)
            wallpapers.append(info)
        
        return wallpapers
