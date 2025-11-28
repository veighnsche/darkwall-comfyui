"""Wallpaper history and gallery management."""

from .manager import WallpaperHistory, HistoryEntry, HistoryConfig
from .exceptions import HistoryError

__all__ = ['WallpaperHistory', 'HistoryEntry', 'HistoryConfig', 'HistoryError']
