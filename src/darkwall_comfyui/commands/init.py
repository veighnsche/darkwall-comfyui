"""Initialization and maintenance commands."""

import logging
import os
from pathlib import Path

from ..config import Config, StateManager


def init_config(config: Config) -> None:
    """Initialize configuration directory with defaults."""
    logger = logging.getLogger(__name__)
    
    try:
        Config.initialize_config()
        print(f"Configuration initialized at {Config.get_config_dir()}")
        
        # Show what was created
        config_dir = Config.get_config_dir()
        for item in sorted(config_dir.rglob('*')):
            if item.is_file():
                rel = item.relative_to(config_dir)
                print(f"  {rel}")
                
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        raise


def fix_permissions(config: Config) -> None:
    """Fix read-only permissions on config files."""
    config_dir = Config.get_config_dir()
    
    print(f"Fixing permissions in {config_dir}")
    
    fixed = 0
    errors = 0
    
    for path in config_dir.rglob('*'):
        if path.is_file() and not os.access(path, os.W_OK):
            try:
                os.chmod(path, 0o644)
                print(f"  Fixed: {path.relative_to(config_dir)}")
                fixed += 1
            except PermissionError:
                try:
                    # Replace the file
                    content = path.read_bytes()
                    path.unlink()
                    path.write_bytes(content)
                    os.chmod(path, 0o644)
                    print(f"  Replaced: {path.relative_to(config_dir)}")
                    fixed += 1
                except Exception as e:
                    print(f"  ERROR: {path.relative_to(config_dir)}: {e}")
                    errors += 1
        elif path.is_dir():
            try:
                os.chmod(path, 0o755)
            except Exception:
                pass
    
    if fixed == 0 and errors == 0:
        print("  All files have correct permissions")
    else:
        print(f"\nFixed {fixed} files, {errors} errors")


def reset_rotation(config: Config) -> None:
    """Reset monitor rotation state."""
    state_mgr = StateManager(config)
    state_mgr.reset_rotation()
    print("Rotation state reset")
