"""
Wallpaper target and output management.

Handles saving wallpapers to disk and coordinating with wallpaper setters.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .setters import get_setter


class WallpaperTarget:
    """
    Manages wallpaper output paths and filesystem operations.
    
    Responsibilities:
    - Creating output directories
    - Saving downloaded images
    - Creating backups before overwriting
    - Coordinating with wallpaper setters
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._setter = None
    
    @property
    def setter(self):
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
        """
        self.logger.info(f"Saving wallpaper to: {output_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create backup if enabled and file exists
        if self.config.output.create_backup and output_path.exists():
            self._create_backup(output_path)
        
        # Write image data
        output_path.write_bytes(image_data)
        
        # Verify
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(f"Failed to save wallpaper: {output_path}")
        
        self.logger.info(f"Saved {output_path.stat().st_size} bytes to {output_path}")
        return output_path
    
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
            
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(current_path, backup_path)
            
            self.logger.debug(f"Backup created: {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.warning(f"Backup failed: {e}")
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
