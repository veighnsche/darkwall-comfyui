"""
State management for DarkWall ComfyUI.

TEAM_007: Split from monolithic config.py for better organization.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..exceptions import ConfigError, StateError


class NamedStateManager:
    """
    Manages persistent state for named monitor rotation.
    
    REQ-MONITOR-002: Uses compositor output names instead of indices.
    """
    
    def __init__(self, monitor_names: List[str]) -> None:
        """
        Initialize with list of monitor names.
        
        Args:
            monitor_names: List of compositor output names (e.g., ["DP-1", "HDMI-A-1"])
        """
        self.monitor_names = monitor_names
        # Import here to avoid circular import
        from .main import Config
        self.state_file = Config.get_state_file()
        self.logger = logging.getLogger(__name__)
    
    def get_state(self) -> Dict[str, Any]:
        """Load current state."""
        if not self.state_file.exists():
            return {
                'last_monitor': None,
                'rotation_count': 0,
                'monitor_order': self.monitor_names,
            }
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                # Ensure monitor_order is up to date
                state['monitor_order'] = self.monitor_names
                return state
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            self.logger.warning(f"Failed to load state file: {e}")
            return {
                'last_monitor': None,
                'rotation_count': 0,
                'monitor_order': self.monitor_names,
            }
    
    def save_state(self, state: Dict[str, Any]) -> None:
        """Save current state."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except (OSError, PermissionError) as e:
            raise StateError(f"Failed to save state file {self.state_file}: {e}")
    
    def get_next_monitor(self) -> str:
        """
        Get the next monitor name in rotation.
        
        Returns:
            Monitor name (e.g., "DP-1")
        """
        if not self.monitor_names:
            raise ConfigError("No monitors configured")
        
        state = self.get_state()
        last_monitor = state.get('last_monitor')
        
        # Find next monitor in rotation
        if last_monitor is None or last_monitor not in self.monitor_names:
            next_monitor = self.monitor_names[0]
        else:
            current_idx = self.monitor_names.index(last_monitor)
            next_idx = (current_idx + 1) % len(self.monitor_names)
            next_monitor = self.monitor_names[next_idx]
        
        # Update state
        state['last_monitor'] = next_monitor
        state['rotation_count'] = state.get('rotation_count', 0) + 1
        self.save_state(state)
        
        self.logger.info(f"Rotating to monitor {next_monitor} (rotation #{state['rotation_count']})")
        return next_monitor
    
    def peek_next_monitor(self) -> str:
        """Get next monitor without advancing rotation."""
        if not self.monitor_names:
            raise ConfigError("No monitors configured")
        
        state = self.get_state()
        last_monitor = state.get('last_monitor')
        
        if last_monitor is None or last_monitor not in self.monitor_names:
            return self.monitor_names[0]
        
        current_idx = self.monitor_names.index(last_monitor)
        next_idx = (current_idx + 1) % len(self.monitor_names)
        return self.monitor_names[next_idx]
    
    def reset_rotation(self) -> None:
        """Reset rotation state."""
        self.save_state({
            'last_monitor': None,
            'rotation_count': 0,
            'monitor_order': self.monitor_names,
        })
        self.logger.info("Reset monitor rotation state")
    
    def save_last_generation(
        self,
        monitor_name: str,
        theme_name: str,
        workflow_id: str,
        template: str,
        prompts: Dict[str, str],
        negatives: Dict[str, str],
        seed: int,
        output_path: str,
        history_path: Optional[str] = None,
    ) -> None:
        """
        Save details of the last generation for retry functionality.
        
        TEAM_006: Enables retry with same prompt but different seed.
        TEAM_007: Updated to store full prompts/negatives dicts for multi-prompt support.
        """
        state = self.get_state()
        state['last_generation'] = {
            'monitor_name': monitor_name,
            'theme_name': theme_name,
            'workflow_id': workflow_id,
            'template': template,
            'prompts': prompts,
            'negatives': negatives,
            'seed': seed,
            'output_path': output_path,
            'history_path': history_path,
            'timestamp': datetime.now().isoformat(),
        }
        self.save_state(state)
        self.logger.debug(f"Saved last generation state for {monitor_name}")
    
    def get_last_generation(self) -> Optional[Dict[str, Any]]:
        """
        Get details of the last generation.
        
        Returns:
            Dict with generation details or None if no previous generation.
        """
        state = self.get_state()
        return state.get('last_generation')
    
    def clear_last_generation(self) -> None:
        """Clear the last generation state."""
        state = self.get_state()
        if 'last_generation' in state:
            del state['last_generation']
            self.save_state(state)
            self.logger.debug("Cleared last generation state")
