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
    
    # Preview command
    preview_parser = prompt_subparsers.add_parser(
        "preview",
        help="Preview prompt template without generating wallpaper"
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
    
    return parser


def handle_preview_command(args, config: Config) -> None:
    """Handle prompt preview command."""
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
    if args.prompt_command == "preview":
        handle_preview_command(args, config)
    elif args.prompt_command == "list":
        handle_list_command(args, config)
    else:
        print("❌ No prompt command specified. Use 'darkwall prompt --help' for usage.")
