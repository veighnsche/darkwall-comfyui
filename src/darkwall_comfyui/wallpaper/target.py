"""
Wallpaper target and output management.

Handles saving wallpapers to disk and coordinating with wallpaper setters.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from ..config import MonitorsConfig
from ..exceptions import CommandError
from .setters import get_setter, WallpaperSetter

class WallpaperTarget:
    """
    Manages wallpaper output paths and filesystem operations.
    
    TEAM_006: Updated to use MonitorsConfig instead of legacy MonitorConfig.
    
    Responsibilities:
    - Creating output directories
    - Saving downloaded images
    - Coordinating with wallpaper setters
    """
    
    def __init__(self, monitors_config: MonitorsConfig) -> None:
        self.monitors_config = monitors_config
        self.logger = logging.getLogger(__name__)
        self._setter: Optional[WallpaperSetter] = None
    
    @property
    def setter(self) -> WallpaperSetter:
        """Lazy-load wallpaper setter."""
        if self._setter is None:
            self._setter = get_setter(self.monitors_config.command)
        return self._setter
    
    def save_wallpaper(self, image_data: bytes, output_path: Path) -> Path:
        """
        Save wallpaper image to disk.
        
        Args:
            image_data: Raw image bytes
            output_path: Where to save the image
            
        Returns:
            Path where wallpaper was saved
            
        Raises:
            CommandError: If saving fails
        """
        if not image_data:
            raise CommandError(f"No image data provided for {output_path}")
        
        self.logger.info(f"Saving wallpaper to: {output_path}")
        
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if directory is writable
            if not os.access(output_path.parent, os.W_OK):
                raise CommandError(f"Output directory is not writable: {output_path.parent}")
            
            # Write image data
            output_path.write_bytes(image_data)
            
            # Verify the file was written correctly
            if not output_path.exists():
                raise CommandError(f"Failed to create wallpaper file: {output_path}")
            
            file_size = output_path.stat().st_size
            if file_size == 0:
                raise CommandError(f"Wallpaper file is empty: {output_path}")
            
            if file_size != len(image_data):
                raise CommandError(f"Size mismatch: expected {len(image_data)} bytes, got {file_size}")
            
            self.logger.info(f"Saved {file_size} bytes to {output_path}")
            return output_path
            
        except OSError as e:
            raise CommandError(f"Filesystem error saving wallpaper to {output_path}: {e}")
        except Exception as e:
            raise CommandError(f"Unexpected error saving wallpaper to {output_path}: {e}")
    
    def set_wallpaper_by_name(self, wallpaper_path: Path, monitor_name: str) -> bool:
        """
        Set wallpaper using monitor name directly.
        
        REQ-MONITOR-002: Uses compositor output name.
        
        Args:
            wallpaper_path: Path to wallpaper image
            monitor_name: Compositor output name (e.g., "DP-1")
            
        Returns:
            True if successful
        """
        # Use index 0 as placeholder since we have the name
        return self.setter.set(wallpaper_path, 0, monitor_name)
    
