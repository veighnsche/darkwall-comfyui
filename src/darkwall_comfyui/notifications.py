"""
Desktop notifications for wallpaper changes.

TEAM_004: REQ-MISC-001 - Optional desktop notifications.

Uses notify-send (libnotify) for cross-desktop compatibility.
"""

import logging
import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """
    Configuration for desktop notifications.
    
    TEAM_004: REQ-MISC-001
    """
    enabled: bool = False
    show_preview: bool = True  # Show wallpaper thumbnail in notification
    timeout_ms: int = 5000  # Notification timeout in milliseconds
    urgency: str = "normal"  # low, normal, critical


class NotificationSender:
    """
    Send desktop notifications for wallpaper events.
    
    TEAM_004: REQ-MISC-001
    """
    
    def __init__(self, config: Optional[NotificationConfig] = None) -> None:
        self.config = config or NotificationConfig()
        self._notify_send_path: Optional[str] = None
        
        if self.config.enabled:
            self._notify_send_path = shutil.which("notify-send")
            if not self._notify_send_path:
                logger.warning("notify-send not found, notifications disabled")
                self.config.enabled = False
    
    def is_available(self) -> bool:
        """Check if notifications are available."""
        return self.config.enabled and self._notify_send_path is not None
    
    def notify_wallpaper_changed(
        self,
        monitor_name: str,
        image_path: Optional[Path] = None,
        prompt: Optional[str] = None,
    ) -> bool:
        """
        Send notification when wallpaper changes.
        
        Args:
            monitor_name: Name of the monitor that changed
            image_path: Path to the new wallpaper image
            prompt: The prompt used to generate the wallpaper
            
        Returns:
            True if notification was sent successfully
        """
        if not self.is_available():
            return False
        
        title = f"🎨 Wallpaper Updated"
        body = f"Monitor: {monitor_name}"
        
        if prompt:
            # Truncate long prompts
            short_prompt = prompt[:100] + "..." if len(prompt) > 100 else prompt
            body += f"\n{short_prompt}"
        
        return self._send_notification(
            title=title,
            body=body,
            icon=str(image_path) if image_path and self.config.show_preview else None,
        )
    
    def notify_generation_started(self, monitor_name: str) -> bool:
        """
        Send notification when generation starts.
        
        Args:
            monitor_name: Name of the monitor being generated
            
        Returns:
            True if notification was sent successfully
        """
        if not self.is_available():
            return False
        
        return self._send_notification(
            title="🖼️ Generating Wallpaper",
            body=f"Creating new wallpaper for {monitor_name}...",
            urgency="low",
        )
    
    def notify_error(self, message: str, details: Optional[str] = None) -> bool:
        """
        Send notification for errors.
        
        Args:
            message: Error message
            details: Optional error details
            
        Returns:
            True if notification was sent successfully
        """
        if not self.is_available():
            return False
        
        body = message
        if details:
            body += f"\n{details[:200]}"
        
        return self._send_notification(
            title="❌ DarkWall Error",
            body=body,
            urgency="critical",
        )
    
    def _send_notification(
        self,
        title: str,
        body: str,
        icon: Optional[str] = None,
        urgency: Optional[str] = None,
    ) -> bool:
        """
        Send a notification using notify-send.
        
        Args:
            title: Notification title
            body: Notification body text
            icon: Optional icon path or name
            urgency: Urgency level (low, normal, critical)
            
        Returns:
            True if notification was sent successfully
        """
        if not self._notify_send_path:
            return False
        
        cmd = [
            self._notify_send_path,
            "--app-name=DarkWall",
            f"--expire-time={self.config.timeout_ms}",
            f"--urgency={urgency or self.config.urgency}",
        ]
        
        if icon:
            cmd.append(f"--icon={icon}")
        
        cmd.extend([title, body])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=5,
            )
            
            if result.returncode != 0:
                logger.warning(f"notify-send failed: {result.stderr.decode()}")
                return False
            
            logger.debug(f"Notification sent: {title}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.warning("notify-send timed out")
            return False
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")
            return False
