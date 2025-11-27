"""Generation commands."""

import logging
import sys

from ..config import Config, StateManager
from ..comfy import ComfyClient, WorkflowManager
from ..prompt_generator import PromptGenerator
from ..wallpaper import WallpaperTarget


def generate_once(config: Config, dry_run: bool = False) -> None:
    """
    Generate wallpaper for the next monitor in rotation.
    
    Steps:
    1. Get next monitor index from rotation state
    2. Generate deterministic prompt
    3. Load and submit workflow to ComfyUI
    4. Download and save result
    5. Set wallpaper
    
    Args:
        config: Configuration object
        dry_run: If True, show what would be done without executing
    """
    logger = logging.getLogger(__name__)
    
    # Get next monitor (but don't update state in dry run)
    state = StateManager(config)
    if dry_run:
        # Just peek at next monitor without updating state
        current_state = state.get_state()
        last_index = current_state.get('last_monitor_index', -1)
        monitor_index = (last_index + 1) % config.monitors.count
    else:
        monitor_index = state.get_next_monitor_index()
    
    output_path = config.monitors.get_output_path(monitor_index)
    
    if dry_run:
        print(f"DRY RUN: Would generate wallpaper for monitor {monitor_index}")
        print(f"  Output path: {output_path}")
        print(f"  ComfyUI URL: {config.comfyui.base_url}")
        print(f"  Workflow: {config.comfyui.workflow_path}")
        
        # Show prompt that would be generated
        try:
            prompt_gen = PromptGenerator(config)
            prompt = prompt_gen.generate_prompt(monitor_index=monitor_index)
            print(f"  Prompt: {prompt[:100]}...")
        except Exception as e:
            print(f"  Prompt error: {e}")
        
        # Don't actually update state in dry run mode
        print("DRY RUN: No actual changes made")
        return
    
    logger.info(f"Generating wallpaper for monitor {monitor_index}")
    logger.info(f"Output: {output_path}")
    
    try:
        # Generate prompt
        prompt_gen = PromptGenerator(config)
        prompt = prompt_gen.generate_prompt(monitor_index=monitor_index)
        logger.info(f"Prompt: {prompt[:100]}...")
        
        # Load workflow
        workflow_mgr = WorkflowManager(config)
        workflow = workflow_mgr.load()
        
        # Validate workflow
        warnings = workflow_mgr.validate(workflow)
        for warning in warnings:
            logger.warning(f"Workflow: {warning}")
        
        # Generate image
        client = ComfyClient(config)
        
        if not client.health_check():
            logger.error(f"ComfyUI not reachable at {config.comfyui.base_url}")
            sys.exit(2)
        
        result = client.generate(workflow, prompt)
        logger.info(f"Generated: {result.filename}")
        
        # Save wallpaper
        target = WallpaperTarget(config)
        saved_path = target.save_wallpaper(result.image_data, output_path)
        
        # Set wallpaper
        if target.set_wallpaper(saved_path, monitor_index):
            logger.info(f"Wallpaper set for monitor {monitor_index}")
        else:
            logger.warning("Failed to set wallpaper (image saved successfully)")
        
        logger.info("Generation complete")
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        sys.exit(1)


def generate_all(config: Config, dry_run: bool = False) -> None:
    """
    Generate wallpapers for all monitors.
    
    Args:
        config: Configuration object
        dry_run: If True, show what would be done without executing
    """
    logger = logging.getLogger(__name__)
    
    if dry_run:
        print(f"DRY RUN: Would generate wallpapers for all {config.monitors.count} monitors")
        for i in range(config.monitors.count):
            output_path = config.monitors.get_output_path(i)
            print(f"  Monitor {i}: {output_path}")
            
            # Show prompt that would be generated
            try:
                prompt_gen = PromptGenerator(config)
                prompt = prompt_gen.generate_prompt(monitor_index=i)
                print(f"    Prompt: {prompt[:100]}...")
            except Exception as e:
                print(f"    Prompt error: {e}")
        
        print("DRY RUN: No actual changes made")
        return
    
    logger.info(f"Generating for all {config.monitors.count} monitors")
    
    # Load shared resources once
    prompt_gen = PromptGenerator(config)
    workflow_mgr = WorkflowManager(config)
    workflow = workflow_mgr.load()
    client = ComfyClient(config)
    target = WallpaperTarget(config)
    
    if not client.health_check():
        logger.error(f"ComfyUI not reachable at {config.comfyui.base_url}")
        sys.exit(2)
    
    success_count = 0
    
    for monitor_index in range(config.monitors.count):
        logger.info(f"--- Monitor {monitor_index} ---")
        
        try:
            prompt = prompt_gen.generate_prompt(monitor_index=monitor_index)
            result = client.generate(workflow, prompt)
            
            output_path = config.monitors.get_output_path(monitor_index)
            target.save_wallpaper(result.image_data, output_path)
            target.set_wallpaper(output_path, monitor_index)
            
            success_count += 1
            logger.info(f"Monitor {monitor_index}: OK")
            
        except Exception as e:
            logger.error(f"Monitor {monitor_index}: {e}")
    
    logger.info(f"Completed: {success_count}/{config.monitors.count} monitors")
    
    if success_count < config.monitors.count:
        sys.exit(1)
