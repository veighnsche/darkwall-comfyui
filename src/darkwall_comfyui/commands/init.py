"""Initialization and maintenance commands."""

import logging
import os
from pathlib import Path

from ..config import Config, StateManager
from ..prompt_generator import PromptGenerator
from ..comfy import ComfyClient


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


def validate_config(config: Config) -> None:
    """Validate configuration and report issues."""
    logger = logging.getLogger(__name__)
    errors = []
    warnings = []
    
    print("Validating configuration...")
    
    # Validate ComfyUI connectivity
    print("\nChecking ComfyUI connectivity...")
    try:
        client = ComfyClient(config.comfyui)
        if client.health_check():
            print("  ✓ ComfyUI is reachable")
        else:
            errors.append("ComfyUI is not reachable at configured URL")
            print("  ✗ ComfyUI is not reachable")
    except Exception as e:
        errors.append(f"ComfyUI client error: {e}")
        print(f"  ✗ ComfyUI client error: {e}")
    
    # Validate workflow file
    print("\nChecking workflow file...")
    try:
        from ..comfy import WorkflowManager
        workflow_mgr = WorkflowManager(config.comfyui)
        workflow = workflow_mgr.load()
        workflow_warnings = workflow_mgr.validate(workflow)
        warnings.extend([f"Workflow: {w}" for w in workflow_warnings])
        print(f"  ✓ Workflow loaded ({len(workflow)} nodes)")
        for warning in workflow_warnings:
            print(f"  ⚠ {warning}")
    except Exception as e:
        errors.append(f"Workflow error: {e}")
        print(f"  ✗ Workflow error: {e}")
    
    # Validate prompt atoms
    print("\nChecking prompt atoms...")
    try:
        prompt_gen = PromptGenerator(config.prompt, Config.get_config_dir())
        for pillar, atoms in prompt_gen.atoms.items():
            if not atoms:
                warnings.append(f"No atoms found for {pillar}")
                print(f"  ⚠ {pillar}: no atoms found")
            else:
                print(f"  ✓ {pillar}: {len(atoms)} atoms")
    except Exception as e:
        errors.append(f"Prompt atoms error: {e}")
        print(f"  ✗ Prompt atoms error: {e}")
    
    # Validate output directories
    print("\nChecking output directories...")
    for i in range(config.monitors.count):
        output_path = config.monitors.get_output_path(i)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if os.access(output_path.parent, os.W_OK):
                print(f"  ✓ Monitor {i}: {output_path.parent} is writable")
            else:
                errors.append(f"Monitor {i}: output directory is not writable")
                print(f"  ✗ Monitor {i}: {output_path.parent} is not writable")
        except Exception as e:
            errors.append(f"Monitor {i}: cannot create output directory: {e}")
            print(f"  ✗ Monitor {i}: cannot create output directory: {e}")
    
    # Validate wallpaper command
    print("\nChecking wallpaper command...")
    try:
        from ..wallpaper import get_setter
        setter = get_setter(config.monitors.command)
        print(f"  ✓ {config.monitors.command} setter is available")
    except Exception as e:
        errors.append(f"Wallpaper command error: {e}")
        print(f"  ✗ Wallpaper command error: {e}")
    
    # Summary
    print(f"\nValidation complete")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  ✗ {error}")
    
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  ⚠ {warning}")
    
    if errors:
        print(f"\nConfiguration validation FAILED with {len(errors)} errors")
        raise SystemExit(1)
    else:
        print("\nConfiguration validation PASSED")
