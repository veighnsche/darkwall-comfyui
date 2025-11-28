"""Gallery command for browsing wallpaper history."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import Config
from ..history import WallpaperHistory


def gallery_list(config: Config, monitor_index: Optional[int] = None,
                favorites_only: bool = False, limit: Optional[int] = None,
                format_output: str = "table") -> None:
    """
    List wallpapers in history with optional filtering.
    
    Args:
        config: Configuration object
        monitor_index: Filter by monitor index
        favorites_only: Only show favorites
        limit: Maximum number of entries to return
        format_output: Output format (table, json)
    """
    logger = logging.getLogger(__name__)
    
    try:
        history = WallpaperHistory(config.history)
        entries = history.list_entries(
            monitor_index=monitor_index,
            favorites_only=favorites_only,
            limit=limit
        )
        
        if not entries:
            print("No wallpapers found in history")
            return
        
        if format_output == "json":
            data = [entry.to_dict() for entry in entries]
            print(json.dumps(data, indent=2))
        else:
            # Table format
            print(f"Found {len(entries)} wallpapers in history:")
            print()
            
            # Header
            print(f"{'Timestamp':<20} {'Monitor':<8} {'Size(MB)':<10} {'Favorite':<9} {'Filename'}")
            print("-" * 80)
            
            # Entries
            for entry in entries:
                timestamp = datetime.fromisoformat(entry.timestamp).strftime("%Y-%m-%d %H:%M")
                size_mb = round(entry.file_size / (1024 * 1024), 2)
                favorite = "★" if entry.favorite else ""
                
                print(f"{timestamp:<20} {entry.monitor_index:<8} {size_mb:<10.2f} {favorite:<9} {entry.filename}")
            
            print()
    
    except Exception as e:
        logger.error(f"Failed to list gallery: {e}")
        sys.exit(1)


def gallery_info(config: Config, timestamp: str) -> None:
    """
    Show detailed information about a specific wallpaper.
    
    Args:
        config: Configuration object
        timestamp: Timestamp of the wallpaper entry
    """
    logger = logging.getLogger(__name__)
    
    try:
        history = WallpaperHistory(config.history)
        entry = history.get_entry(timestamp)
        
        if not entry:
            print(f"Wallpaper not found: {timestamp}")
            sys.exit(1)
        
        # Display detailed information
        print(f"Wallpaper Details:")
        print(f"  Timestamp: {entry.timestamp}")
        print(f"  Filename: {entry.filename}")
        print(f"  Path: {entry.path}")
        print(f"  Monitor: {entry.monitor_index}")
        print(f"  Prompt ID: {entry.prompt_id}")
        print(f"  File Size: {round(entry.file_size / (1024 * 1024), 2)} MB")
        print(f"  Favorite: {'Yes' if entry.favorite else 'No'}")
        
        if entry.template:
            print(f"  Template: {entry.template}")
        
        if entry.workflow:
            print(f"  Workflow: {entry.workflow}")
        
        if entry.seed is not None:
            print(f"  Seed: {entry.seed}")
        
        print()
        print(f"Positive Prompt:")
        print(f"  {entry.positive_prompt}")
        
        if entry.negative_prompt:
            print()
            print(f"Negative Prompt:")
            print(f"  {entry.negative_prompt}")
        
        if entry.tags:
            print()
            print(f"Tags: {', '.join(sorted(entry.tags))}")
        
        # Show full path
        full_path = config.history.get_history_dir() / entry.path
        print()
        print(f"Full Path: {full_path}")
        
    except Exception as e:
        logger.error(f"Failed to get wallpaper info: {e}")
        sys.exit(1)


def gallery_favorite(config: Config, timestamp: str, favorite: bool = True) -> None:
    """
    Mark or unmark a wallpaper as favorite.
    
    Args:
        config: Configuration object
        timestamp: Timestamp of the wallpaper entry
        favorite: Whether to mark as favorite (True) or unfavorite (False)
    """
    logger = logging.getLogger(__name__)
    
    try:
        history = WallpaperHistory(config.history)
        success = history.set_favorite(timestamp, favorite)
        
        if not success:
            print(f"Wallpaper not found: {timestamp}")
            sys.exit(1)
        
        action = "favorited" if favorite else "unfavorited"
        print(f"Wallpaper {action}: {timestamp}")
        
    except Exception as e:
        logger.error(f"Failed to set favorite: {e}")
        sys.exit(1)


def gallery_delete(config: Config, timestamp: str) -> None:
    """
    Delete a wallpaper from history.
    
    Args:
        config: Configuration object
        timestamp: Timestamp of the wallpaper entry
    """
    logger = logging.getLogger(__name__)
    
    try:
        history = WallpaperHistory(config.history)
        success = history.delete_entry(timestamp)
        
        if not success:
            print(f"Wallpaper not found: {timestamp}")
            sys.exit(1)
        
        print(f"Wallpaper deleted: {timestamp}")
        
    except Exception as e:
        logger.error(f"Failed to delete wallpaper: {e}")
        sys.exit(1)


def gallery_stats(config: Config) -> None:
    """
    Show history statistics.
    
    Args:
        config: Configuration object
    """
    logger = logging.getLogger(__name__)
    
    try:
        history = WallpaperHistory(config.history)
        stats = history.get_stats()
        
        print(f"Wallpaper History Statistics:")
        print(f"  Total Entries: {stats['total_entries']}")
        print(f"  Total Size: {stats['total_size_mb']} MB")
        print(f"  Favorites: {stats['favorite_count']}")
        
        if stats['monitor_counts']:
            print()
            print(f"  By Monitor:")
            for monitor_index, count in sorted(stats['monitor_counts'].items()):
                print(f"    Monitor {monitor_index}: {count} wallpapers")
        
        if stats['oldest_entry']:
            oldest = datetime.fromisoformat(stats['oldest_entry']).strftime("%Y-%m-%d %H:%M")
            newest = datetime.fromisoformat(stats['newest_entry']).strftime("%Y-%m-%d %H:%M")
            print()
            print(f"  Time Range: {oldest} to {newest}")
        
        # History directory info
        history_dir = config.history.get_history_dir()
        print()
        print(f"  History Directory: {history_dir}")
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        sys.exit(1)


def gallery_cleanup(config: Config) -> None:
    """
    Run cleanup on wallpaper history.
    
    Args:
        config: Configuration object
    """
    logger = logging.getLogger(__name__)
    
    try:
        history = WallpaperHistory(config.history)
        deleted_count = history.cleanup()
        
        if deleted_count == 0:
            print("No wallpapers deleted by cleanup")
        else:
            print(f"Cleanup completed: deleted {deleted_count} wallpapers")
        
    except Exception as e:
        logger.error(f"Failed to run cleanup: {e}")
        sys.exit(1)
