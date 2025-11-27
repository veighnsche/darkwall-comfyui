#!/usr/bin/env python3
"""
Main CLI entry point for DarkWall ComfyUI.

This module provides the command-line interface for generating
deterministic dark-mode wallpapers using ComfyUI with multi-monitor support.
"""

import argparse
import logging
import sys
from pathlib import Path

from .config import Config, StateManager
from .prompt_generator import PromptGenerator
from .comfy_client import ComfyClient
from .wallpaper_target import WallpaperTarget


def setup_logging(config: Config) -> None:
    """Setup logging configuration."""
    level = getattr(logging, config.logging.level.upper())
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )


def generate_wallpaper_once(config: Config) -> None:
    """
    Generate a single wallpaper for one monitor and exit.
    
    This function:
    1. Determines which monitor to update using rotation state
    2. Builds a deterministic prompt using time-slot seed + monitor index
    3. Loads ComfyUI workflow from configured path
    4. Submits workflow to ComfyUI
    5. Polls for completion
    6. Downloads and saves wallpaper to monitor-specific path
    7. Sets the wallpaper using configured command
    """
    logger = logging.getLogger(__name__)
    
    # Initialize state manager for rotation
    state_manager = StateManager(config)
    
    # Get next monitor to update
    monitor_index = state_manager.get_next_monitor_index()
    output_path = config.monitors.get_output_path(monitor_index)
    
    logger.info(f"Starting wallpaper generation for monitor {monitor_index}")
    logger.info(f"Output path: {output_path}")
    
    try:
        # Step 1: Generate deterministic prompt for this monitor
        prompt_gen = PromptGenerator(config)
        prompt = prompt_gen.generate_prompt(monitor_index=monitor_index)
        logger.info(f"Generated prompt: {prompt}")
        
        # Step 2: Load and prepare ComfyUI workflow
        comfy_client = ComfyClient(config)
        workflow = comfy_client.load_workflow(config.comfyui.workflow_path)
        workflow_with_prompt = comfy_client.inject_prompt(workflow, prompt)
        
        # Step 3: Submit to ComfyUI and poll for result
        prompt_id = comfy_client.submit_workflow(workflow_with_prompt)
        logger.info(f"Submitted workflow with prompt ID: {prompt_id}")
        
        result = comfy_client.wait_for_result(prompt_id)
        if not result:
            logger.error("Workflow failed or timed out")
            sys.exit(3)
        
        # Step 4: Download and save wallpaper
        wallpaper_target = WallpaperTarget(config)
        saved_path = wallpaper_target.save_wallpaper(result.image_url, result.filename, output_path)
        
        logger.info(f"Wallpaper saved to: {saved_path}")
        
        # Step 5: Set wallpaper using configured command
        wallpaper_target.set_wallpaper(saved_path, monitor_index)
        
        logger.info(f"Wallpaper generation complete for monitor {monitor_index}")
        
    except Exception as e:
        logger.error(f"Failed to generate wallpaper for monitor {monitor_index}: {e}")
        # Don't revert state on failure - continue to next monitor next time
        sys.exit(1)


def generate_all_monitors(config: Config) -> None:
    """
    Generate wallpapers for all monitors at once.
    
    This is useful for initial setup or manual regeneration.
    """
    logger = logging.getLogger(__name__)
    
    logger.info(f"Generating wallpapers for all {config.monitors.count} monitors")
    
    for monitor_index in range(config.monitors.count):
        logger.info(f"Processing monitor {monitor_index}...")
        
        try:
            # Generate prompt for this monitor
            prompt_gen = PromptGenerator(config)
            prompt = prompt_gen.generate_prompt(monitor_index=monitor_index)
            
            # Generate wallpaper
            comfy_client = ComfyClient(config)
            workflow = comfy_client.load_workflow(config.comfyui.workflow_path)
            workflow_with_prompt = comfy_client.inject_prompt(workflow, prompt)
            
            prompt_id = comfy_client.submit_workflow(workflow_with_prompt)
            result = comfy_client.wait_for_result(prompt_id)
            
            if not result:
                logger.error(f"Failed to generate wallpaper for monitor {monitor_index}")
                continue
            
            # Save wallpaper
            wallpaper_target = WallpaperTarget(config)
            output_path = config.monitors.get_output_path(monitor_index)
            saved_path = wallpaper_target.save_wallpaper(result.image_url, result.filename, output_path)
            
            logger.info(f"Monitor {monitor_index}: {saved_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate wallpaper for monitor {monitor_index}: {e}")
            continue
    
    logger.info("All monitors processed")


def init_config(config: Config) -> None:
    """
    Initialize configuration directory with defaults.
    """
    logger = logging.getLogger(__name__)
    
    try:
        Config.initialize_config()
        logger.info(f"Configuration initialized at {Config.get_config_dir()}")
    except Exception as e:
        logger.error(f"Failed to initialize configuration: {e}")
        sys.exit(1)


def reset_rotation(config: Config) -> None:
    """
    Reset monitor rotation state.
    """
    logger = logging.getLogger(__name__)
    
    try:
        state_manager = StateManager(config)
        state_manager.reset_rotation()
        logger.info("Monitor rotation state reset")
    except Exception as e:
        logger.error(f"Failed to reset rotation state: {e}")
        sys.exit(1)


def show_status(config: Config) -> None:
    """
    Show current configuration and rotation status.
    """
    import os
    import stat
    
    print(f"DarkWall ComfyUI Status")
    print(f"======================")
    print(f"Config directory: {Config.get_config_dir()}")
    print(f"State file: {Config.get_state_file()}")
    print(f"Monitors: {config.monitors.count}")
    print(f"Command: {config.monitors.command}")
    print(f"Pattern: {config.monitors.pattern}")
    print(f"Time slot: {config.prompt.time_slot_minutes} minutes")
    print(f"Monitor seeds: {config.prompt.use_monitor_seed}")
    
    # Show rotation state
    state_manager = StateManager(config)
    state = state_manager.get_state()
    last_monitor = state.get('last_monitor_index', -1)
    rotation_count = state.get('rotation_count', 0)
    
    if last_monitor >= 0:
        next_monitor = (last_monitor + 1) % config.monitors.count
        print(f"Last updated: Monitor {last_monitor}")
        print(f"Next update: Monitor {next_monitor}")
    else:
        print(f"Next update: Monitor 0 (first run)")
    
    print(f"Total rotations: {rotation_count}")
    
    # Show atom counts
    prompt_gen = PromptGenerator(config)
    for pillar, atoms in prompt_gen.atoms.items():
        print(f"{pillar.capitalize()} atoms: {len(atoms)}")
    
    # Show file permissions
    print(f"\nFile Permissions")
    print(f"----------------")
    config_dir = Config.get_config_dir()
    atoms_dir = config_dir / "atoms"
    
    def perms_str(path: Path) -> str:
        """Get permission string for a file."""
        if not path.exists():
            return "MISSING"
        st = path.stat()
        mode = st.st_mode
        writable = os.access(path, os.W_OK)
        perms = stat.filemode(mode)
        status = "✓" if writable else "✗ READ-ONLY"
        return f"{perms} {status}"
    
    print(f"  config.toml: {perms_str(config_dir / 'config.toml')}")
    if atoms_dir.exists():
        for f in sorted(atoms_dir.iterdir()):
            if f.is_file():
                print(f"  atoms/{f.name}: {perms_str(f)}")
    else:
        print(f"  atoms/: MISSING")


def fix_permissions(config: Config) -> None:
    """
    Fix file permissions on config files.
    
    This is useful for recovering from read-only files left over
    from Nix store copies or other permission issues.
    """
    import os
    
    logger = logging.getLogger(__name__)
    config_dir = Config.get_config_dir()
    
    print(f"Fixing permissions in {config_dir}")
    
    fixed_count = 0
    error_count = 0
    
    for path in config_dir.rglob('*'):
        if path.is_file():
            if not os.access(path, os.W_OK):
                try:
                    # Try to change permissions directly
                    os.chmod(path, 0o644)
                    print(f"  Fixed: {path.relative_to(config_dir)}")
                    fixed_count += 1
                except PermissionError:
                    # If that fails, try to replace the file
                    try:
                        content = path.read_bytes()
                        path.unlink()
                        path.write_bytes(content)
                        os.chmod(path, 0o644)
                        print(f"  Replaced: {path.relative_to(config_dir)}")
                        fixed_count += 1
                    except Exception as e:
                        print(f"  ERROR: {path.relative_to(config_dir)}: {e}")
                        error_count += 1
        elif path.is_dir():
            try:
                os.chmod(path, 0o755)
            except Exception:
                pass  # Directories are less critical
    
    if fixed_count == 0 and error_count == 0:
        print("  All files already have correct permissions")
    else:
        print(f"\nFixed {fixed_count} files, {error_count} errors")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate deterministic dark-mode wallpapers using ComfyUI"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (optional, uses ~/.config/darkwall-comfyui/config.toml by default)"
    )
    parser.add_argument(
        "--no-init",
        action="store_true",
        help="Skip automatic configuration initialization"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Default generate command (no subcommand)
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate wallpaper for next monitor in rotation (default)"
    )
    
    # Generate all monitors
    generate_all_parser = subparsers.add_parser(
        "generate-all",
        help="Generate wallpapers for all monitors"
    )
    
    # Initialize config
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize configuration directory"
    )
    
    # Reset rotation
    reset_parser = subparsers.add_parser(
        "reset",
        help="Reset monitor rotation state"
    )
    
    # Show status
    status_parser = subparsers.add_parser(
        "status",
        help="Show current configuration and rotation status"
    )
    
    # Fix permissions
    fix_parser = subparsers.add_parser(
        "fix-permissions",
        help="Fix read-only config files (troubleshooting)"
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = Config.load(
            config_file=args.config,
            initialize=not args.no_init
        )
        
        # Setup logging
        setup_logging(config)
        
        # Handle commands
        if args.command == "init" or not args.command:
            if args.command == "init":
                init_config(config)
            else:
                # Default behavior: generate wallpaper for next monitor
                generate_wallpaper_once(config)
        
        elif args.command == "generate":
            generate_wallpaper_once(config)
        
        elif args.command == "generate-all":
            generate_all_monitors(config)
        
        elif args.command == "reset":
            reset_rotation(config)
        
        elif args.command == "status":
            show_status(config)
        
        elif args.command == "fix-permissions":
            fix_permissions(config)
        
        else:
            parser.print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        logging.getLogger(__name__).error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
