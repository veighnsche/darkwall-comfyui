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
    validate_config,
)
from .commands.prompt import execute as prompt_command
from .commands.gallery import (
    gallery_list,
    gallery_info,
    gallery_favorite,
    gallery_delete,
    gallery_stats,
    gallery_cleanup,
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without actually doing it"
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration and exit"
    )
    parser.add_argument(
        "--workflow",
        type=str,
        help="Override workflow path for generate command (per-monitor workflows still apply to generate-all)"
    )
    parser.add_argument(
        "--template",
        type=str,
        help="Override template file for generate command (per-monitor templates still apply to generate-all)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    subparsers.add_parser("generate", help="Generate for next monitor (default)")
    subparsers.add_parser("generate-all", help="Generate for all monitors")
    subparsers.add_parser("status", help="Show status")
    subparsers.add_parser("init", help="Initialize config")
    subparsers.add_parser("reset", help="Reset rotation")
    subparsers.add_parser("fix-permissions", help="Fix config permissions")
    subparsers.add_parser("validate", help="Validate configuration")
    
    # Add prompt subcommand with its own subparsers
    prompt_parser = subparsers.add_parser("prompt", help="Manage prompt templates")
    prompt_subparsers = prompt_parser.add_subparsers(dest="prompt_command", help="Prompt commands")
    
    # Prompt preview
    preview_parser = prompt_subparsers.add_parser("preview", help="Preview prompt template")
    preview_parser.add_argument(
        "--template",
        help="Template file to preview (default: default.prompt)",
        default=None
    )
    preview_parser.add_argument(
        "--monitor",
        type=int,
        help="Monitor index for seed variation (default: 0)",
        default=0
    )
    preview_parser.add_argument(
        "--seed",
        type=int,
        help="Specific seed to use (default: time-based)",
        default=None
    )
    
    # Prompt list
    list_parser = prompt_subparsers.add_parser("list", help="List available templates and atoms")
    list_parser.add_argument(
        "--atoms",
        action="store_true",
        help="List atom files instead of templates"
    )
    
    # Add gallery subcommand with its own subparsers
    gallery_parser = subparsers.add_parser("gallery", help="Browse wallpaper history")
    gallery_subparsers = gallery_parser.add_subparsers(dest="gallery_command", help="Gallery commands")
    
    # Gallery list
    list_parser = gallery_subparsers.add_parser("list", help="List wallpapers in history")
    list_parser.add_argument("--monitor", type=int, help="Filter by monitor index")
    list_parser.add_argument("--favorites", action="store_true", help="Only show favorites")
    list_parser.add_argument("--limit", type=int, help="Maximum number of entries")
    list_parser.add_argument("--format", choices=["table", "json"], default="table", help="Output format")
    
    # Gallery info
    info_parser = gallery_subparsers.add_parser("info", help="Show wallpaper details")
    info_parser.add_argument("timestamp", help="Timestamp of wallpaper entry")
    
    # Gallery favorite
    favorite_parser = gallery_subparsers.add_parser("favorite", help="Mark wallpaper as favorite")
    favorite_parser.add_argument("timestamp", help="Timestamp of wallpaper entry")
    favorite_parser.add_argument("--unfavorite", action="store_true", help="Remove favorite status")
    
    # Gallery delete
    delete_parser = gallery_subparsers.add_parser("delete", help="Delete wallpaper from history")
    delete_parser.add_argument("timestamp", help="Timestamp of wallpaper entry")
    
    # Gallery stats
    gallery_subparsers.add_parser("stats", help="Show history statistics")
    
    # Gallery cleanup
    gallery_subparsers.add_parser("cleanup", help="Run history cleanup")
    
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
        
        # Handle config validation flag
        if args.validate_config:
            validate_config(config)
            return 0
        
        # Dispatch command
        command = args.command or "generate"
        
        if command == "generate":
            generate_once(config, dry_run=args.dry_run, workflow_path=args.workflow, template_path=args.template)
        elif command == "generate-all":
            generate_all(config, dry_run=args.dry_run)
        elif command == "status":
            show_status(config)
        elif command == "init":
            init_config(config)
        elif command == "reset":
            reset_rotation(config)
        elif command == "fix-permissions":
            fix_permissions(config)
        elif command == "validate":
            validate_config(config)
        elif command == "prompt":
            prompt_command(args, config)
        elif command == "gallery":
            gallery_cmd = args.gallery_command
            if gallery_cmd == "list":
                gallery_list(config, monitor_index=args.monitor, favorites_only=args.favorites, 
                            limit=args.limit, format_output=args.format)
            elif gallery_cmd == "info":
                gallery_info(config, args.timestamp)
            elif gallery_cmd == "favorite":
                gallery_favorite(config, args.timestamp, favorite=not args.unfavorite)
            elif gallery_cmd == "delete":
                gallery_delete(config, args.timestamp)
            elif gallery_cmd == "stats":
                gallery_stats(config)
            elif gallery_cmd == "cleanup":
                gallery_cleanup(config)
            else:
                gallery_parser.print_help()
                return 1
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
