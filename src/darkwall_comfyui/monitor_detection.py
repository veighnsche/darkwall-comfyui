"""
Monitor detection from Wayland compositors.

REQ-MONITOR-001: Auto-Detection via Compositor
REQ-MONITOR-002: Compositor Names as Identifiers
REQ-MONITOR-010: Compositor Error Handling
REQ-MONITOR-011: Monitor Detection Caching
"""

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .exceptions import (
    MonitorDetectionError,
    CompositorNotFoundError,
    CompositorCommunicationError,
    NoMonitorsDetectedError,
)

logger = logging.getLogger(__name__)


@dataclass
class Monitor:
    """Detected monitor information."""
    name: str  # Compositor output name (e.g., "DP-1", "HDMI-A-1")
    resolution: str  # Resolution string (e.g., "2560x1440")
    logical_size: Optional[str] = None  # Logical size if different
    model: Optional[str] = None  # Monitor model name
    
    def __repr__(self) -> str:
        return f"Monitor({self.name}, {self.resolution})"


class MonitorDetector:
    """
    Detect monitors from Wayland compositors.
    
    Supports:
    - niri (primary)
    - sway (planned)
    - hyprland (planned)
    """
    
    def __init__(self) -> None:
        self._cache: Optional[List[Monitor]] = None
        self._compositor: Optional[str] = None
    
    def detect(self, force_refresh: bool = False) -> List[Monitor]:
        """
        Detect connected monitors from the compositor.
        
        REQ-MONITOR-011: Results are cached until force_refresh=True.
        
        Args:
            force_refresh: Force re-detection even if cached
            
        Returns:
            List of detected Monitor objects
            
        Raises:
            ConfigError: If compositor not running or detection fails
        """
        if self._cache is not None and not force_refresh:
            logger.debug("Using cached monitor detection results")
            return self._cache
        
        # Detect compositor type
        compositor = self._detect_compositor()
        self._compositor = compositor
        
        # Detect monitors based on compositor
        if compositor == "niri":
            monitors = self._detect_niri()
        elif compositor == "sway":
            monitors = self._detect_sway()
        elif compositor == "hyprland":
            monitors = self._detect_hyprland()
        else:
            raise ConfigError(
                f"Unsupported compositor: {compositor}. "
                "Supported: niri, sway, hyprland"
            )
        
        self._cache = monitors
        logger.info(f"Detected {len(monitors)} monitors via {compositor}")
        return monitors
    
    def invalidate_cache(self) -> None:
        """Clear cached detection results."""
        self._cache = None
    
    @property
    def compositor(self) -> Optional[str]:
        """Get detected compositor name."""
        return self._compositor
    
    def _detect_compositor(self) -> str:
        """
        Detect which compositor is running.
        
        REQ-MONITOR-010: Error with clear message if no compositor found.
        """
        # Check for niri first (user's compositor)
        if self._is_running("niri"):
            return "niri"
        
        # Check for sway
        if self._is_running("sway"):
            return "sway"
        
        # Check for hyprland
        if self._is_running("hyprland") or self._is_running("Hyprland"):
            return "hyprland"
        
        raise CompositorNotFoundError(
            "Could not detect monitors: No supported compositor running.\n"
            "Supported compositors: niri, sway, hyprland.\n"
            "Make sure your compositor is running before using darkwall."
        )
    
    def _is_running(self, process_name: str) -> bool:
        """Check if a process is running."""
        try:
            result = subprocess.run(
                ["pgrep", "-x", process_name],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _detect_niri(self) -> List[Monitor]:
        """
        Detect monitors from niri compositor.
        
        Uses: niri msg outputs
        
        REQ-MONITOR-010: Shows actual error message on failure.
        """
        try:
            result = subprocess.run(
                ["niri", "msg", "outputs"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                raise CompositorCommunicationError(
                    f"Failed to detect monitors from niri: {error_msg}\n"
                    "Make sure niri is running and 'niri msg outputs' works."
                )
            
            return self._parse_niri_output(result.stdout)
            
        except subprocess.TimeoutExpired as e:
            raise CompositorCommunicationError(
                f"Timeout detecting monitors from niri after {e.timeout}s.\n"
                "'niri msg outputs' took too long to respond."
            ) from e
        except FileNotFoundError as e:
            raise CompositorNotFoundError(
                "Could not find 'niri' command.\n"
                "Make sure niri is installed and in PATH."
            ) from e
    
    def _parse_niri_output(self, output: str) -> List[Monitor]:
        """
        Parse niri msg outputs format.
        
        Example output:
        Output "HP Inc. OMEN by HP 27 CNK724200N" (DP-1)
          Current mode: 2560x1440 @ 59.951 Hz
          Logical size: 2327x1309
        """
        monitors = []
        
        # Pattern: Output "Model Name" (OUTPUT-NAME)
        output_pattern = re.compile(
            r'Output "([^"]*)" \((\S+)\)'
        )
        
        # Pattern: Current mode: WIDTHxHEIGHT
        mode_pattern = re.compile(
            r'Current mode: (\d+x\d+)'
        )
        
        # Pattern: Logical size: WIDTHxHEIGHT
        logical_pattern = re.compile(
            r'Logical size: (\d+x\d+)'
        )
        
        # Split by "Output" to process each monitor
        sections = output.split("Output ")
        
        for section in sections:
            if not section.strip():
                continue
            
            # Prepend "Output " for matching
            section = "Output " + section
            
            output_match = output_pattern.search(section)
            mode_match = mode_pattern.search(section)
            
            if output_match and mode_match:
                model = output_match.group(1)
                name = output_match.group(2)
                resolution = mode_match.group(1)
                
                logical_match = logical_pattern.search(section)
                logical_size = logical_match.group(1) if logical_match else None
                
                monitors.append(Monitor(
                    name=name,
                    resolution=resolution,
                    logical_size=logical_size,
                    model=model,
                ))
        
        if not monitors:
            raise NoMonitorsDetectedError(
                "No monitors detected from niri output.\n"
                "Make sure at least one monitor is connected."
            )
        
        return monitors
    
    def _detect_sway(self) -> List[Monitor]:
        """
        Detect monitors from sway compositor.
        
        Uses: swaymsg -t get_outputs (JSON output)
        """
        try:
            result = subprocess.run(
                ["swaymsg", "-t", "get_outputs"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                raise CompositorCommunicationError(
                    f"Failed to detect monitors from sway: {error_msg}\n"
                    "Make sure sway is running and 'swaymsg -t get_outputs' works."
                )
            
            return self._parse_sway_output(result.stdout)
            
        except subprocess.TimeoutExpired as e:
            raise CompositorCommunicationError(
                f"Timeout detecting monitors from sway after {e.timeout}s.\n"
                "'swaymsg -t get_outputs' took too long to respond."
            ) from e
        except FileNotFoundError as e:
            raise CompositorNotFoundError(
                "Could not find 'swaymsg' command.\n"
                "Make sure sway is installed and in PATH."
            ) from e
    
    def _parse_sway_output(self, output: str) -> List[Monitor]:
        """
        Parse swaymsg -t get_outputs JSON format.
        
        Example output:
        [
          {
            "name": "DP-1",
            "make": "HP Inc.",
            "model": "OMEN by HP 27",
            "current_mode": {
              "width": 2560,
              "height": 1440,
              "refresh": 59951
            },
            ...
          }
        ]
        """
        import json
        
        try:
            outputs = json.loads(output)
        except json.JSONDecodeError as e:
            raise CompositorCommunicationError(
                f"Failed to parse sway JSON output: {e}\n"
                "The compositor returned invalid JSON. This may indicate a version mismatch."
            ) from e
        
        monitors = []
        for output_info in outputs:
            if not output_info.get("active", True):
                continue  # Skip inactive outputs
            
            name = output_info.get("name")
            if not name:
                continue
            
            current_mode = output_info.get("current_mode", {})
            width = current_mode.get("width", 0)
            height = current_mode.get("height", 0)
            resolution = f"{width}x{height}" if width and height else "unknown"
            
            model = output_info.get("model", "")
            make = output_info.get("make", "")
            full_model = f"{make} {model}".strip() if make or model else None
            
            monitors.append(Monitor(
                name=name,
                resolution=resolution,
                model=full_model,
            ))
        
        if not monitors:
            raise NoMonitorsDetectedError(
                "No monitors detected from sway output.\n"
                "Make sure at least one monitor is connected."
            )
        
        return monitors
    
    def _detect_hyprland(self) -> List[Monitor]:
        """
        Detect monitors from hyprland compositor.
        
        Uses: hyprctl monitors -j (JSON output)
        """
        try:
            result = subprocess.run(
                ["hyprctl", "monitors", "-j"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                raise CompositorCommunicationError(
                    f"Failed to detect monitors from hyprland: {error_msg}\n"
                    "Make sure hyprland is running and 'hyprctl monitors -j' works."
                )
            
            return self._parse_hyprland_output(result.stdout)
            
        except subprocess.TimeoutExpired as e:
            raise CompositorCommunicationError(
                f"Timeout detecting monitors from hyprland after {e.timeout}s.\n"
                "'hyprctl monitors -j' took too long to respond."
            ) from e
        except FileNotFoundError as e:
            raise CompositorNotFoundError(
                "Could not find 'hyprctl' command.\n"
                "Make sure hyprland is installed and in PATH."
            ) from e
    
    def _parse_hyprland_output(self, output: str) -> List[Monitor]:
        """
        Parse hyprctl monitors -j JSON format.
        
        Example output:
        [
          {
            "name": "DP-1",
            "description": "HP Inc. OMEN by HP 27",
            "width": 2560,
            "height": 1440,
            ...
          }
        ]
        """
        import json
        
        try:
            monitors_data = json.loads(output)
        except json.JSONDecodeError as e:
            raise CompositorCommunicationError(
                f"Failed to parse hyprland JSON output: {e}\n"
                "The compositor returned invalid JSON. This may indicate a version mismatch."
            ) from e
        
        monitors = []
        for monitor_info in monitors_data:
            name = monitor_info.get("name")
            if not name:
                continue
            
            width = monitor_info.get("width", 0)
            height = monitor_info.get("height", 0)
            resolution = f"{width}x{height}" if width and height else "unknown"
            
            model = monitor_info.get("description", "")
            
            monitors.append(Monitor(
                name=name,
                resolution=resolution,
                model=model if model else None,
            ))
        
        if not monitors:
            raise NoMonitorsDetectedError(
                "No monitors detected from hyprland output.\n"
                "Make sure at least one monitor is connected."
            )
        
        return monitors


# Global detector instance for caching
_detector: Optional[MonitorDetector] = None


def get_detector() -> MonitorDetector:
    """Get or create the global monitor detector."""
    global _detector
    if _detector is None:
        _detector = MonitorDetector()
    return _detector


def detect_monitors(force_refresh: bool = False) -> List[Monitor]:
    """
    Convenience function to detect monitors.
    
    Args:
        force_refresh: Force re-detection
        
    Returns:
        List of detected Monitor objects
    """
    return get_detector().detect(force_refresh)


def get_monitor_names() -> List[str]:
    """Get list of detected monitor names."""
    return [m.name for m in detect_monitors()]
