"""
Command-line interface for DarkWall ComfyUI.

Usage:
    generate-wallpaper-once [command] [options]
    
Commands:
    generate      Generate wallpaper for next monitor (default)
    generate-all  Generate wallpapers for all monitors
    status        Show configuration and status
    init          Initialize config directory
    reset         Reset rotation state
    fix-permissions  Fix read-only config files
"""

import argparse
import logging
import sys
from pathlib import Path

from .config import Config
from .commands import (
    generate_once,
    generate_all,
    show_status,
    init_config,
    fix_permissions,
    reset_rotation,
)


def setup_logging(level: str = "INFO") -> None:
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="generate-wallpaper-once",
        description="Deterministic dark-mode wallpaper generator using ComfyUI"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "-c", "--config",
        type=Path,
        help="Path to config file"
    )
    parser.add_argument(
        "--no-init",
        action="store_true",
        help="Skip auto-initialization of config"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    subparsers.add_parser("generate", help="Generate for next monitor (default)")
    subparsers.add_parser("generate-all", help="Generate for all monitors")
    subparsers.add_parser("status", help="Show status")
    subparsers.add_parser("init", help="Initialize config")
    subparsers.add_parser("reset", help="Reset rotation")
    subparsers.add_parser("fix-permissions", help="Fix config permissions")
    
    args = parser.parse_args()
    
    try:
        # Load config
        config = Config.load(
            config_file=args.config,
            initialize=not args.no_init
        )
        
        # Setup logging
        level = "DEBUG" if args.verbose else config.logging.level
        setup_logging(level)
        
        # Dispatch command
        command = args.command or "generate"
        
        if command == "generate":
            generate_once(config)
        elif command == "generate-all":
            generate_all(config)
        elif command == "status":
            show_status(config)
        elif command == "init":
            init_config(config)
        elif command == "reset":
            reset_rotation(config)
        elif command == "fix-permissions":
            fix_permissions(config)
        else:
            parser.print_help()
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\nCancelled", file=sys.stderr)
        return 130
    except Exception as e:
        logging.getLogger(__name__).error(str(e))
        if args.verbose:
            raise
        return 1


if __name__ == "__main__":
    sys.exit(main())
