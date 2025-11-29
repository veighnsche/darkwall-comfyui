"""Prompt management commands."""

import argparse
import logging
from pathlib import Path
from typing import Optional

from ..config import Config
from ..prompt_generator import PromptGenerator, PromptResult
from ..exceptions import PromptError


def add_parser(subparsers) -> argparse.ArgumentParser:
    """Add prompt command parser to subparsers."""
    parser = subparsers.add_parser(
        "prompt",
        help="Manage and preview prompt templates",
        description="Preview prompt templates and test wildcard resolution"
    )
    
    prompt_subparsers = parser.add_subparsers(dest="prompt_command", help="Prompt commands")
    
    # Generate command - clean output for copy-paste
    generate_parser = prompt_subparsers.add_parser(
        "generate",
        help="Generate a prompt ready to copy-paste into ComfyUI"
    )
    generate_parser.add_argument(
        "-t", "--template",
        help="Template file to use (default: default.prompt)",
        default=None
    )
    generate_parser.add_argument(
        "-T", "--theme",
        help="Theme to use (light/dark, default: from schedule or config)",
        default=None
    )
    generate_parser.add_argument(
        "-s", "--seed",
        type=int,
        help="Specific seed (default: time-based)",
        default=None
    )
    generate_parser.add_argument(
        "-m", "--monitor",
        type=int,
        help="Monitor index for seed variation (default: 0)",
        default=0
    )
    generate_parser.add_argument(
        "--raw",
        action="store_true",
        help="Output raw prompts only (no formatting, for scripting)"
    )
    generate_parser.add_argument(
        "--positive-only",
        action="store_true",
        help="Output only the positive prompt"
    )
    generate_parser.add_argument(
        "--negative-only",
        action="store_true",
        help="Output only the negative prompt"
    )
    
    # Preview command (legacy, same as generate but with more info)
    preview_parser = prompt_subparsers.add_parser(
        "preview",
        help="Preview prompt template with metadata"
    )
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
    
    # List command
    list_parser = prompt_subparsers.add_parser(
        "list",
        help="List available templates and atom files"
    )
    list_parser.add_argument(
        "--atoms",
        action="store_true",
        help="List atom files instead of templates"
    )
    list_parser.add_argument(
        "-T", "--theme",
        help="Theme to list templates/atoms for (default: current)",
        default=None
    )
    
    return parser


def handle_generate_command(args, config: Optional[Config]) -> None:
    """
    Handle prompt generate command.
    
    Outputs clean, copy-paste ready prompts for ComfyUI.
    Works even without a full config - just needs theme files.
    """
    logger = logging.getLogger(__name__)
    
    try:
        from ..config import ThemeConfig, PromptConfig, Config as ConfigClass
        
        # Get config directory
        config_dir = ConfigClass.get_config_dir()
        
        # Determine theme
        theme_name = args.theme
        if theme_name is None:
            # Try to get from schedule if config available
            if config and hasattr(config, 'schedule') and config.schedule:
                try:
                    from ..schedule import ThemeScheduler
                    scheduler = ThemeScheduler(config.schedule)
                    theme_result = scheduler.get_current_theme()
                    theme_name = theme_result.theme
                except Exception:
                    pass
            
            # Fall back to config default or 'dark'
            if theme_name is None:
                if config and hasattr(config, 'prompt'):
                    theme_name = getattr(config.prompt, 'theme', 'dark')
                else:
                    theme_name = 'dark'
        
        # Get theme config - try config.themes first, then create default
        theme_config = None
        if config and hasattr(config, 'themes') and config.themes and theme_name in config.themes:
            theme_config = config.themes[theme_name]
        else:
            # Create theme config directly from theme name
            theme_config = ThemeConfig(
                name=theme_name,
                atoms_dir="atoms",
                prompts_dir="prompts",
                default_template="default.prompt"
            )
        
        # Get template name
        template_name = args.template or theme_config.default_template
        
        # Create prompt config (use from config if available, else defaults)
        prompt_config = config.prompt if config else PromptConfig()
        
        # Get theme paths
        atoms_dir = theme_config.get_atoms_path(config_dir)
        prompts_dir = theme_config.get_prompts_path(config_dir)
        
        # Create prompt generator with theme paths
        prompt_gen = PromptGenerator(prompt_config, config_dir, atoms_dir=atoms_dir, prompts_dir=prompts_dir)
        
        # Generate seed
        if args.seed is not None:
            seed = args.seed
        else:
            seed = prompt_gen.get_time_slot_seed(monitor_index=args.monitor)
        
        # Generate prompt pair
        result = prompt_gen.generate_prompt_pair(
            monitor_index=args.monitor,
            template_path=template_name,
            seed=seed
        )
        
        # Output based on flags
        if args.raw:
            # Raw output for scripting
            if args.positive_only:
                print(result.positive)
            elif args.negative_only:
                print(result.negative)
            else:
                print(result.positive)
                print("---")
                print(result.negative)
        else:
            # Formatted output for humans
            if args.positive_only:
                print(result.positive)
            elif args.negative_only:
                print(result.negative)
            else:
                print()
                print("=" * 60)
                print("POSITIVE PROMPT (copy this):")
                print("=" * 60)
                print()
                print(result.positive)
                print()
                print("=" * 60)
                print("NEGATIVE PROMPT (copy this):")
                print("=" * 60)
                print()
                print(result.negative)
                print()
                print("-" * 60)
                print(f"Theme: {theme_name} | Template: {template_name} | Seed: {seed}")
                print("-" * 60)
        
    except PromptError as e:
        logger.error(f"Prompt error: {e}")
        print(f"❌ Error: {e}", file=__import__('sys').stderr)
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}", file=__import__('sys').stderr)
        raise SystemExit(1)


def handle_preview_command(args, config: Config) -> None:
    """Handle prompt preview command (legacy, with metadata)."""
    logger = logging.getLogger(__name__)
    
    try:
        # Get template name
        template_name = args.template or config.prompt.default_template
        
        # Create prompt generator
        prompt_gen = PromptGenerator(config.prompt, config.get_config_dir())
        
        # Generate seed
        if args.seed is not None:
            seed = args.seed
        else:
            seed = prompt_gen.get_time_slot_seed(monitor_index=args.monitor)
        
        # Generate prompt pair
        result = prompt_gen.generate_prompt_pair(
            monitor_index=args.monitor,
            template_path=template_name,
            seed=seed
        )
        
        # Display results
        print(f"\n📝 Template: {template_name}")
        print(f"🎲 Seed: {seed}")
        print(f"🖥️  Monitor: {args.monitor}")
        print("\n✨ Positive Prompt:")
        print(f"   {result.positive}")
        print("\n🚫 Negative Prompt:")
        print(f"   {result.negative}")
        
    except PromptError as e:
        logger.error(f"Prompt error: {e}")
        print(f"❌ Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")


def handle_list_command(args, config: Config) -> None:
    """Handle prompt list command."""
    config_dir = config.get_config_dir()
    
    if args.atoms:
        # List atom files
        atoms_dir = config_dir / "atoms"
        print(f"\n📁 Atom files in {atoms_dir}/:")
        
        if atoms_dir.exists():
            for atom_file in sorted(atoms_dir.glob("*.txt")):
                # Count lines (excluding comments and empty)
                try:
                    with open(atom_file, 'r', encoding='utf-8') as f:
                        count = sum(1 for line in f if line.strip() and not line.strip().startswith('#'))
                    print(f"   📄 {atom_file.stem} ({count} atoms)")
                except Exception as e:
                    print(f"   ❌ {atom_file.stem} (error reading: {e})")
        else:
            print("   (no atoms directory)")
    else:
        # List templates
        prompts_dir = config_dir / "prompts"
        print(f"\n📝 Templates in {prompts_dir}/:")
        
        if prompts_dir.exists():
            for template_file in sorted(prompts_dir.glob("*.prompt")):
                print(f"   📄 {template_file.name}")
        else:
            print("   (no prompts directory)")
    
    print()


def execute(args, config: Config) -> None:
    """Execute prompt command."""
    if args.prompt_command == "generate":
        handle_generate_command(args, config)
    elif args.prompt_command == "preview":
        handle_preview_command(args, config)
    elif args.prompt_command == "list":
        handle_list_command(args, config)
    else:
        # Default to generate if no subcommand specified
        print("Usage: darkwall prompt <command>")
        print()
        print("Commands:")
        print("  generate  Generate a prompt ready to copy-paste into ComfyUI")
        print("  preview   Preview prompt template with metadata")
        print("  list      List available templates and atom files")
        print()
        print("Run 'darkwall prompt generate --help' for more options.")
