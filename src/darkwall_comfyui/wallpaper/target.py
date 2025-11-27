"""
Wallpaper target and output management.

Handles saving wallpapers to disk and coordinating with wallpaper setters.
"""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..config import Config
from .setters import get_setter, WallpaperSetter


class WallpaperTarget:
    """
    Manages wallpaper output paths and filesystem operations.
    
    Responsibilities:
    - Creating output directories
    - Saving downloaded images
    - Creating backups before overwriting
    - Coordinating with wallpaper setters
    """
    
    def __init__(self, config: Config) -> None:
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._setter: Optional[WallpaperSetter] = None
    
    @property
    def setter(self) -> WallpaperSetter:
        """Lazy-load wallpaper setter."""
        if self._setter is None:
            self._setter = get_setter(self.config.monitors.command)
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
            RuntimeError: If saving fails
        """
        if not image_data:
            raise RuntimeError(f"No image data provided for {output_path}")
        
        self.logger.info(f"Saving wallpaper to: {output_path}")
        
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if directory is writable
            if not os.access(output_path.parent, os.W_OK):
                raise RuntimeError(f"Output directory is not writable: {output_path.parent}")
            
            # Create backup if enabled and file exists
            if self.config.output.create_backup and output_path.exists():
                self._create_backup(output_path)
            
            # Write image data
            output_path.write_bytes(image_data)
            
            # Verify the file was written correctly
            if not output_path.exists():
                raise RuntimeError(f"Failed to create wallpaper file: {output_path}")
            
            file_size = output_path.stat().st_size
            if file_size == 0:
                raise RuntimeError(f"Wallpaper file is empty: {output_path}")
            
            if file_size != len(image_data):
                raise RuntimeError(f"Size mismatch: expected {len(image_data)} bytes, got {file_size}")
            
            self.logger.info(f"Saved {file_size} bytes to {output_path}")
            return output_path
            
        except OSError as e:
            raise RuntimeError(f"Filesystem error saving wallpaper to {output_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error saving wallpaper to {output_path}: {e}")
    
    def set_wallpaper(self, wallpaper_path: Path, monitor_index: int) -> bool:
        """
        Set wallpaper using configured command.
        
        Args:
            wallpaper_path: Path to wallpaper image
            monitor_index: Monitor index
            
        Returns:
            True if successful
        """
        return self.setter.set(wallpaper_path, monitor_index)
    
    def _create_backup(self, current_path: Path) -> Optional[Path]:
        """Create backup of existing wallpaper."""
        try:
            monitor_index = self._extract_monitor_index(current_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.config.monitors.get_backup_path(monitor_index, timestamp)
            
            # Ensure backup directory exists
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if backup directory is writable
            if not os.access(backup_path.parent, os.W_OK):
                self.logger.warning(f"Backup directory is not writable: {backup_path.parent}")
                return None
            
            # Copy the file
            shutil.copy2(current_path, backup_path)
            
            # Verify backup was created
            if not backup_path.exists():
                self.logger.error(f"Backup creation failed: {backup_path}")
                return None
            
            self.logger.debug(f"Backup created: {backup_path}")
            return backup_path
            
        except OSError as e:
            self.logger.warning(f"Filesystem error creating backup: {e}")
            return None
        except shutil.Error as e:
            self.logger.warning(f"Copy error creating backup: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"Unexpected error creating backup: {e}")
            return None
    
    def _extract_monitor_index(self, path: Path) -> int:
        """Extract monitor index from filename like 'monitor_0.png'."""
        stem = path.stem
        if "monitor_" in stem:
            try:
                return int(stem.split("monitor_")[1].split("_")[0])
            except (ValueError, IndexError):
                pass
        return 0
    
    def get_info(self, monitor_index: int) -> dict[str, Any]:
        """Get info about wallpaper for a specific monitor."""
        path = self.config.monitors.get_output_path(monitor_index)
        
        if not path.exists():
            return {"exists": False, "path": str(path), "monitor_index": monitor_index}
        
        stat = path.stat()
        return {
            "exists": True,
            "path": str(path),
            "monitor_index": monitor_index,
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    
    def list_all(self) -> list[dict[str, Any]]:
        """List wallpaper info for all monitors."""
        return [self.get_info(i) for i in range(self.config.monitors.count)]
