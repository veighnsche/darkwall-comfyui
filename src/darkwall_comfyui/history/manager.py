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
            
        Raises:
            HistoryError: If saving fails
            HistoryStorageError: If file operations fail
        """
        if not self.config.enabled:
            self.logger.debug("History disabled, skipping save")
            return None
        
        if not image_data:
            raise HistoryError("No image data provided for history save")
        
        try:
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
            except Exception as e:
                raise HistoryStorageError(f"Unexpected error saving wallpaper to {image_path}: {e}")
            
            # Validate file was written correctly
            if file_size == 0:
                raise HistoryStorageError(f"Saved wallpaper file is empty: {image_path}")
            
            if file_size != len(image_data):
                raise HistoryStorageError(f"Size mismatch for saved wallpaper: expected {len(image_data)} bytes, got {file_size}")
            
            # Format prompts for storage (combines all sections with labels)
            sections = prompt_result.sections()
            positive_parts = []
            negative_parts = []
            for section in sections:
                prompt = prompt_result.get_prompt(section)
                negative = prompt_result.get_negative(section)
                if prompt:
                    positive_parts.append(f"[{section.upper()}]\n{prompt}")
                if negative:
                    negative_parts.append(f"[{section.upper()}]\n{negative}")
            positive_text = "\n\n".join(positive_parts)
            negative_text = "\n\n".join(negative_parts)
            
            # Create history entry
            entry = HistoryEntry(
                timestamp=timestamp_str,
                filename=filename,
                path=str(image_path.relative_to(self.history_dir)),
                monitor_index=monitor_index,
                prompt_id=generation_result.prompt_id,
                positive_prompt=positive_text,
                negative_prompt=negative_text,
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
            
        except HistoryError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            raise HistoryError(f"Failed to save wallpaper to history: {e}")
    
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
        """
        Delete entry and its image file.
        
        Args:
            timestamp: Timestamp of entry to delete
            
        Returns:
            True if entry was found and deleted
            
        Raises:
            HistoryError: If deletion fails critically
        """
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
            # Continue with index removal even if file deletion fails
        except Exception as e:
            self.logger.warning(f"Unexpected error deleting image file {image_path}: {e}")
            # Continue with index removal even if file deletion fails
        
        # Remove from index
        try:
            self._entries = [e for e in self._entries if e.timestamp != timestamp]
            self._save_index()
        except Exception as e:
            raise HistoryError(f"Failed to remove entry from index: {e}")
        
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
            
        Raises:
            HistoryError: If cleanup fails critically
        """
        cleanup_policy = policy or self.config.cleanup_policy
        if not cleanup_policy:
            self.logger.info("No cleanup policy configured")
            return 0
        
        try:
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
                try:
                    if self.delete_entry(entry.timestamp):
                        deleted_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to delete entry {entry.timestamp} during cleanup: {e}")
                    # Continue with other entries
            
            self.logger.info(f"Cleanup completed: deleted {deleted_count} entries")
            return deleted_count
            
        except Exception as e:
            raise HistoryError(f"Cleanup failed: {e}")
    
    def _ensure_history_dir(self) -> None:
        """
        Ensure history directory exists and is writable.
        
        Raises:
            HistoryStorageError: If directory creation or permission check fails
        """
        try:
            self.history_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if directory is writable
            if not os.access(self.history_dir, os.W_OK):
                raise HistoryStorageError(f"History directory is not writable: {self.history_dir}")
                
        except OSError as e:
            raise HistoryStorageError(f"Failed to create history directory {self.history_dir}: {e}")
        except Exception as e:
            raise HistoryStorageError(f"Unexpected error creating history directory {self.history_dir}: {e}")
    
    def _load_index(self) -> List[HistoryEntry]:
        """
        Load history index from file.
        
        Returns:
            List of history entries (empty if file not found or invalid)
            
        Raises:
            HistoryStorageError: If critical file system errors occur
        """
        if not self.index_file.exists():
            return []
        
        try:
            data = json.loads(self.index_file.read_text(encoding='utf-8'))
            
            # Validate data structure
            if not isinstance(data, list):
                self.logger.warning(f"Invalid history index structure: expected list, got {type(data).__name__}")
                return []
            
            entries = []
            for i, entry_data in enumerate(data):
                try:
                    entry = HistoryEntry.from_dict(entry_data)
                    entries.append(entry)
                except (KeyError, TypeError, ValueError) as e:
                    self.logger.warning(f"Skipping invalid history entry {i}: {e}")
                    # Continue with other entries
            
            self.logger.debug(f"Loaded {len(entries)} history entries from index")
            return entries
            
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.logger.warning(f"Invalid history index file format, starting fresh: {e}")
            return []
        except OSError as e:
            raise HistoryStorageError(f"Failed to read history index file {self.index_file}: {e}")
        except Exception as e:
            self.logger.warning(f"Unexpected error loading history index: {e}")
            return []
    
    def _save_index(self) -> None:
        """
        Save history index to file.
        
        Raises:
            HistoryStorageError: If saving fails
        """
        try:
            data = [entry.to_dict() for entry in self._entries]
            
            # Create backup before overwriting
            if self.index_file.exists():
                backup_file = self.index_file.with_suffix('.json.bak')
                try:
                    shutil.copy2(self.index_file, backup_file)
                except OSError as e:
                    self.logger.warning(f"Failed to create index backup: {e}")
            
            # Write new index
            self.index_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
            self.logger.debug(f"Saved {len(self._entries)} entries to history index")
            
        except (OSError, UnicodeEncodeError) as e:
            raise HistoryStorageError(f"Failed to save history index to {self.index_file}: {e}")
        except Exception as e:
            raise HistoryStorageError(f"Unexpected error saving history index: {e}")
    
    def _cleanup_if_needed(self) -> None:
        """
        Run cleanup if we exceed configured limits.
        
        Raises:
            HistoryError: If cleanup fails critically
        """
        try:
            if len(self._entries) > self.config.max_entries:
                self.logger.info(f"History exceeds max entries ({len(self._entries)} > {self.config.max_entries}), running cleanup")
                self.cleanup()
        except Exception as e:
            self.logger.warning(f"Automatic cleanup failed: {e}")
            # Don't fail the save operation if cleanup fails
