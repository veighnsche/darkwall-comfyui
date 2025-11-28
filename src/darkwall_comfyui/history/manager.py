"""
Wallpaper history management.

Handles saving, organizing, and managing wallpaper generation history
with metadata, favorites, and cleanup policies.
"""

import json
import logging
import os
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from ..prompt_generator import PromptResult
from ..config import HistoryConfig, CleanupPolicy
from ..exceptions import DarkWallError
from .exceptions import HistoryError, HistoryStorageError


@dataclass
class HistoryEntry:
    """Single wallpaper history entry with metadata."""
    timestamp: str  # ISO format
    filename: str
    path: str  # Relative to history directory
    monitor_index: int
    prompt_id: str
    positive_prompt: str
    negative_prompt: Optional[str] = None
    template: Optional[str] = None
    workflow: Optional[str] = None
    seed: Optional[int] = None
    file_size: int = 0
    favorite: bool = False
    tags: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        data = asdict(self)
        data['tags'] = list(self.tags)  # Convert set to list for JSON
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HistoryEntry':
        """Create from JSON dict."""
        if 'tags' in data:
            data['tags'] = set(data['tags'])  # Convert list back to set
        return cls(**data)


class WallpaperHistory:
    """
    Manages wallpaper generation history.
    
    Saves every generated wallpaper with metadata, provides gallery browsing,
    favorites management, and cleanup policies.
    """
    
    def __init__(self, config: HistoryConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.history_dir = config.get_history_dir()
        self.index_file = self.history_dir / "index.json"
        
        # Initialize history directory
        self._ensure_history_dir()
        
        # Load existing index
        self._entries: List[HistoryEntry] = self._load_index()
    
    def save_wallpaper(self, image_data: bytes, generation_result: Any, 
                      prompt_result: PromptResult, monitor_index: int,
                      template: Optional[str] = None, workflow: Optional[str] = None,
                      seed: Optional[int] = None) -> HistoryEntry:
        """
        Save wallpaper to history with full metadata.
        
        Args:
            image_data: Raw image bytes
            generation_result: GenerationResult from ComfyClient
            prompt_result: PromptResult with positive/negative prompts
            monitor_index: Monitor index
            template: Template file used
            workflow: Workflow file used
            seed: Seed used for generation
            
        Returns:
            Created HistoryEntry
        """
        if not self.config.enabled:
            self.logger.debug("History disabled, skipping save")
            return None
        
        timestamp = datetime.now()
        timestamp_str = timestamp.isoformat()
        
        # Generate filename: YYYYMMDD_HHMMSS_monitor_{index}.png
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_monitor_{monitor_index}.png"
        
        # Create subdirectory by date: history/YYYY/MM/
        date_subdir = self.history_dir / timestamp.strftime('%Y') / timestamp.strftime('%m')
        date_subdir.mkdir(parents=True, exist_ok=True)
        
        # Save image
        image_path = date_subdir / filename
        try:
            image_path.write_bytes(image_data)
            file_size = image_path.stat().st_size
            self.logger.info(f"Saved wallpaper to history: {image_path}")
        except OSError as e:
            raise HistoryStorageError(f"Failed to save wallpaper to {image_path}: {e}")
        
        # Create history entry
        entry = HistoryEntry(
            timestamp=timestamp_str,
            filename=filename,
            path=str(image_path.relative_to(self.history_dir)),
            monitor_index=monitor_index,
            prompt_id=generation_result.prompt_id,
            positive_prompt=prompt_result.positive,
            negative_prompt=prompt_result.negative,
            template=template,
            workflow=workflow,
            seed=seed,
            file_size=file_size
        )
        
        # Add to index
        self._entries.append(entry)
        self._save_index()
        
        # Run cleanup if needed
        self._cleanup_if_needed()
        
        return entry
    
    def list_entries(self, monitor_index: Optional[int] = None,
                    favorites_only: bool = False,
                    limit: Optional[int] = None) -> List[HistoryEntry]:
        """
        List history entries with optional filtering.
        
        Args:
            monitor_index: Filter by monitor index
            favorites_only: Only show favorites
            limit: Maximum number of entries to return
            
        Returns:
            List of HistoryEntry (newest first)
        """
        entries = self._entries.copy()
        
        # Apply filters
        if monitor_index is not None:
            entries = [e for e in entries if e.monitor_index == monitor_index]
        
        if favorites_only:
            entries = [e for e in entries if e.favorite]
        
        # Sort by timestamp (newest first)
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        
        # Apply limit
        if limit:
            entries = entries[:limit]
        
        return entries
    
    def get_entry(self, timestamp: str) -> Optional[HistoryEntry]:
        """Get specific history entry by timestamp."""
        for entry in self._entries:
            if entry.timestamp == timestamp:
                return entry
        return None
    
    def set_favorite(self, timestamp: str, favorite: bool = True) -> bool:
        """Mark entry as favorite/unfavorite."""
        entry = self.get_entry(timestamp)
        if entry:
            entry.favorite = favorite
            self._save_index()
            return True
        return False
    
    def delete_entry(self, timestamp: str) -> bool:
        """Delete entry and its image file."""
        entry = self.get_entry(timestamp)
        if not entry:
            return False
        
        # Delete image file
        image_path = self.history_dir / entry.path
        try:
            if image_path.exists():
                image_path.unlink()
                self.logger.info(f"Deleted history image: {image_path}")
        except OSError as e:
            self.logger.warning(f"Failed to delete image file {image_path}: {e}")
        
        # Remove from index
        self._entries = [e for e in self._entries if e.timestamp != timestamp]
        self._save_index()
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get history statistics."""
        total_entries = len(self._entries)
        total_size = sum(e.file_size for e in self._entries)
        favorite_count = sum(1 for e in self._entries if e.favorite)
        
        # Monitor breakdown
        monitor_counts = {}
        for entry in self._entries:
            monitor_counts[entry.monitor_index] = monitor_counts.get(entry.monitor_index, 0) + 1
        
        return {
            'total_entries': total_entries,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'favorite_count': favorite_count,
            'monitor_counts': monitor_counts,
            'oldest_entry': min((e.timestamp for e in self._entries), default=None),
            'newest_entry': max((e.timestamp for e in self._entries), default=None),
        }
    
    def cleanup(self, policy: Optional[CleanupPolicy] = None) -> int:
        """
        Run cleanup with specified policy or default config policy.
        
        Args:
            policy: Cleanup policy to use, or None to use config policy
            
        Returns:
            Number of entries deleted
        """
        cleanup_policy = policy or self.config.cleanup_policy
        if not cleanup_policy:
            self.logger.info("No cleanup policy configured")
            return 0
        
        # Sort entries by timestamp (oldest first for deletion)
        sorted_entries = sorted(self._entries, key=lambda e: e.timestamp)
        total_size_mb = sum(e.file_size for e in self._entries) / (1024 * 1024)
        
        entries_to_delete = []
        
        for entry in sorted_entries:
            # Check if we should keep this entry
            if not cleanup_policy.should_keep(entry, self._entries, total_size_mb):
                entries_to_delete.append(entry)
        
        # Delete entries
        deleted_count = 0
        for entry in entries_to_delete:
            if self.delete_entry(entry.timestamp):
                deleted_count += 1
        
        self.logger.info(f"Cleanup completed: deleted {deleted_count} entries")
        return deleted_count
    
    def _ensure_history_dir(self) -> None:
        """Ensure history directory exists and is writable."""
        try:
            self.history_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if directory is writable
            if not os.access(self.history_dir, os.W_OK):
                raise HistoryStorageError(f"History directory is not writable: {self.history_dir}")
                
        except OSError as e:
            raise HistoryStorageError(f"Failed to create history directory {self.history_dir}: {e}")
    
    def _load_index(self) -> List[HistoryEntry]:
        """Load history index from file."""
        if not self.index_file.exists():
            return []
        
        try:
            data = json.loads(self.index_file.read_text())
            return [HistoryEntry.from_dict(entry) for entry in data]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.warning(f"Invalid history index file, starting fresh: {e}")
            return []
    
    def _save_index(self) -> None:
        """Save history index to file."""
        try:
            data = [entry.to_dict() for entry in self._entries]
            self.index_file.write_text(json.dumps(data, indent=2))
        except OSError as e:
            raise HistoryStorageError(f"Failed to save history index: {e}")
    
    def _cleanup_if_needed(self) -> None:
        """Run cleanup if we exceed configured limits."""
        if len(self._entries) > self.config.max_entries:
            self.logger.info(f"History exceeds max entries ({len(self._entries)} > {self.config.max_entries}), running cleanup")
            self.cleanup()
