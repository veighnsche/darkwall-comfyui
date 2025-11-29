"""
Configuration validation for DarkWall ComfyUI.
"""

import re
from pathlib import Path
from typing import Dict, Any

from ..exceptions import ConfigError


# URL validation regex
URL_PATTERN = re.compile(
    r'^https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
    r'localhost|'  # localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


def validate_toml_structure(config_dict: Dict[str, Any], config_file: Path) -> None:
    """
    Validate TOML structure before creating dataclasses.
    
    Checks for unknown sections and keys, providing helpful error messages.
    
    Args:
        config_dict: Loaded TOML configuration dictionary
        config_file: Path to config file for error messages
        
    Raises:
        ConfigError: If structure validation fails
    """
    # Define valid sections and their keys
    # NOTE: monitors section now uses [monitors.{name}] format (per-monitor config)
    # The old flat monitors keys are caught by check_deprecated_keys() first
    valid_structure = {
        'comfyui': {
            'base_url': str,
            'workflow_path': str,
            'timeout': int,
            'poll_interval': int,
            'headers': dict,  # Optional
        },
        'monitors': dict,  # Dynamic: [monitors.{name}] sections with per-monitor config
        'output': {
            'create_backup': bool,
        },
        'prompt': {
            'time_slot_minutes': int,
            'theme': str,
            'atoms_dir': str,
            'use_monitor_seed': bool,
            'default_template': str,  # Optional
            'variations_per_monitor': int,
        },
        'logging': {
            'level': str,
            'verbose': bool,
        },
        'history': {
            'enabled': bool,
            'history_dir': str,
            'max_entries': int,
            'cleanup_policy': dict,  # Optional
        },
        # TEAM_001: Theme definitions
        'themes': dict,  # Dynamic keys: theme names -> theme config
        # TEAM_002: Workflow definitions with optional prompt filtering
        'workflows': dict,  # Dynamic keys: workflow names -> workflow config
        # TEAM_003: Schedule configuration for theme switching
        # TEAM_006: Added day_themes/night_themes for weighted selection
        'schedule': {
            'latitude': float,
            'longitude': float,
            'day_theme': str,
            'night_theme': str,
            'day_themes': list,   # TEAM_006: Weighted theme list
            'night_themes': list,  # TEAM_006: Weighted theme list
            'nsfw_start': str,  # "HH:MM" format
            'nsfw_end': str,    # "HH:MM" format
            'blend_duration_minutes': int,
            'timezone': str,
        },
        # TEAM_004: Notifications configuration
        'notifications': {
            'enabled': bool,
            'show_preview': bool,
            'timeout_ms': int,
            'urgency': str,
        },
    }
    
    # Check for unknown sections
    for section in config_dict:
        if section not in valid_structure:
            raise ConfigError(
                f"Unknown config section '{section}' in {config_file}. "
                f"Valid sections: {list(valid_structure.keys())}"
            )
    
    # Check each section for unknown keys and type validation
    for section_name, section_config in config_dict.items():
        if not isinstance(section_config, dict):
            raise ConfigError(
                f"Section '{section_name}' must be a dictionary in {config_file}"
            )
        
        valid_keys = valid_structure[section_name]
        
        # Skip validation for dynamic sections (monitors, themes, workflows)
        # These use [section.{name}] format with arbitrary keys
        if valid_keys == dict:
            continue
        
        for key, value in section_config.items():
            if key not in valid_keys:
                raise ConfigError(
                    f"Unknown key '{key}' in section '{section_name}' in {config_file}. "
                    f"Valid keys: {list(valid_keys.keys())}"
                )
            
            # Basic type checking
            expected_type = valid_keys[key]
            if expected_type != dict and not isinstance(value, expected_type):
                raise ConfigError(
                    f"Key '{section_name}.{key}' must be of type {expected_type.__name__} "
                    f"in {config_file}, got {type(value).__name__}"
                )
