"""Generation commands."""

import logging
import sys
from pathlib import Path

from ..config import Config, StateManager, MonitorConfig, OutputConfig, ComfyUIConfig, PromptConfig
from ..comfy import ComfyClient, WorkflowManager
from ..prompt_generator import PromptGenerator
from ..wallpaper import WallpaperTarget
from ..history import WallpaperHistory


def generate_once(config: Config, dry_run: bool = False, workflow_path: str = None, template_path: str = None) -> None:
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
        workflow_path: Optional workflow path override for this run
        
    Raises:
        ConfigError: If configuration is invalid
        GenerationError: If wallpaper generation fails
        WorkflowError: If workflow loading/validation fails
        PromptError: If prompt generation fails
        CommandError: If wallpaper setting fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Get next monitor (but don't update state in dry run)
        state = StateManager(config.monitors)
        if dry_run:
            # Just peek at next monitor without updating state
            current_state = state.get_state()
            last_index = current_state.get('last_monitor_index', -1)
            monitor_index = (last_index + 1) % config.monitors.count
        else:
            monitor_index = state.get_next_monitor_index()
        
        output_path = config.monitors.get_output_path(monitor_index)
        
        # Get workflow path for this monitor (or use override)
        if workflow_path:
            actual_workflow_path = workflow_path
        else:
            actual_workflow_path = config.monitors.get_workflow_path(monitor_index, str(config.comfyui.workflow_path))
        
        if dry_run:
            print(f"DRY RUN: Would generate wallpaper for monitor {monitor_index}")
            print(f"  Output path: {output_path}")
            print(f"  ComfyUI URL: {config.comfyui.base_url}")
            print(f"  Workflow: {actual_workflow_path}")
            
            # Show prompt that would be generated
            try:
                if template_path:
                    actual_template_path = template_path
                else:
                    actual_template_path = config.monitors.get_template_path(monitor_index, config.prompt.default_template)
                
                prompt_gen = PromptGenerator(config.prompt, Config.get_config_dir())
                prompt = prompt_gen.generate_prompt(monitor_index=monitor_index, template_path=actual_template_path)
                print(f"  Template: {actual_template_path}")
                print(f"  Prompt: {prompt[:100]}...")
            except PromptError as e:
                print(f"  Prompt error: {e}")
            except Exception as e:
                print(f"  Unexpected prompt error: {e}")
            
            # Don't actually update state in dry run mode
            print("DRY RUN: No actual changes made")
            return
        
        logger.info(f"Generating wallpaper for monitor {monitor_index}")
        logger.info(f"Output: {output_path}")
        logger.info(f"Workflow: {actual_workflow_path}")
        
        # Generate prompt with per-monitor template (or override)
        if template_path:
            actual_template_path = template_path
        else:
            actual_template_path = config.monitors.get_template_path(monitor_index, config.prompt.default_template)
        
        prompt_gen = PromptGenerator(config.prompt, Config.get_config_dir())
        prompts = prompt_gen.generate_prompt_pair(monitor_index=monitor_index, template_path=actual_template_path)
        logger.info(f"Prompt: {prompts.positive[:100]}...")
        if prompts.negative:
            logger.info(f"Negative: {prompts.negative[:100]}...")
        
        # Load workflow
        workflow_mgr = WorkflowManager(config.comfyui)
        workflow = workflow_mgr.load(Path(actual_workflow_path), Config.get_config_dir())
        
        # Validate workflow
        warnings = workflow_mgr.validate(workflow)
        for warning in warnings:
            logger.warning(f"Workflow: {warning}")
        
        # Generate image
        client = ComfyClient(config.comfyui)
        
        if not client.health_check():
            raise GenerationError(f"ComfyUI not reachable at {config.comfyui.base_url}")
        
        result = client.generate(workflow, prompts)
        logger.info(f"Generated: {result.filename}")
        
        # Save wallpaper
        target = WallpaperTarget(config.monitors, config.output)
        saved_path = target.save_wallpaper(result.image_data, output_path)
        
        # Save to history
        history = WallpaperHistory(config.history)
        history_entry = history.save_wallpaper(
            image_data=result.image_data,
            generation_result=result,
            prompt_result=prompts,
            monitor_index=monitor_index,
            template=actual_template_path,
            workflow=actual_workflow_path
        )
        logger.info(f"Saved to history: {history_entry.filename}")
        
        # Set wallpaper
        if target.set_wallpaper(saved_path, monitor_index):
            logger.info(f"Wallpaper set for monitor {monitor_index}")
        else:
            logger.warning("Failed to set wallpaper (image saved successfully)")
        
        logger.info("Generation complete")
        
    except (ConfigError, GenerationError, WorkflowError, PromptError, CommandError):
        # Re-raise our specific exceptions
        raise
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise GenerationError(f"Generation failed: {e}")


def generate_all(config: Config, dry_run: bool = False) -> None:
    """
    Generate wallpapers for all monitors.
    
    Args:
        config: Configuration object
        dry_run: If True, show what would be done without executing
        
    Raises:
        ConfigError: If configuration is invalid
        GenerationError: If wallpaper generation fails
        WorkflowError: If workflow loading/validation fails
        PromptError: If prompt generation fails
        CommandError: If wallpaper setting fails
    """
    logger = logging.getLogger(__name__)
    
    if dry_run:
        print(f"DRY RUN: Would generate wallpapers for all {config.monitors.count} monitors")
        for i in range(config.monitors.count):
            output_path = config.monitors.get_output_path(i)
            workflow_path = config.monitors.get_workflow_path(i, str(config.comfyui.workflow_path))
            print(f"  Monitor {i}: {output_path}")
            print(f"    Workflow: {workflow_path}")
            
            # Show prompt that would be generated
            try:
                template_path = config.monitors.get_template_path(i, config.prompt.default_template)
                prompt_gen = PromptGenerator(config.prompt, Config.get_config_dir())
                prompt = prompt_gen.generate_prompt(monitor_index=i, template_path=template_path)
                print(f"    Template: {template_path}")
                print(f"    Prompt: {prompt[:100]}...")
                
                # Show workflow validation warnings
                workflow_mgr = WorkflowManager(config.comfyui)
                try:
                    workflow = workflow_mgr.load(Path(workflow_path), Config.get_config_dir())
                    warnings = workflow_mgr.validate(workflow)
                    for warning in warnings:
                        print(f"    Warning: {warning}")
                except WorkflowError as e:
                    print(f"    Workflow error: {e}")
                except Exception as e:
                    print(f"    Unexpected workflow error: {e}")
                    
            except PromptError as e:
                print(f"    Prompt error: {e}")
            except Exception as e:
                print(f"    Unexpected prompt error: {e}")
        
        print("DRY RUN: No actual changes made")
        return
    
    logger.info(f"Generating for all {config.monitors.count} monitors")
    
    # Load shared resources once
    prompt_gen = PromptGenerator(config.prompt, Config.get_config_dir())
    workflow_mgr = WorkflowManager(config.comfyui)
    client = ComfyClient(config.comfyui)
    target = WallpaperTarget(config.monitors, config.output)
    history = WallpaperHistory(config.history)
    
    if not client.health_check():
        raise GenerationError(f"ComfyUI not reachable at {config.comfyui.base_url}")
    
    success_count = 0
    errors = []
    
    for monitor_index in range(config.monitors.count):
        logger.info(f"--- Monitor {monitor_index} ---")
        
        # Get workflow path for this monitor
        workflow_path = config.monitors.get_workflow_path(monitor_index, str(config.comfyui.workflow_path))
        logger.info(f"Using workflow: {workflow_path}")
        
        try:
            # Load workflow for this monitor
            workflow = workflow_mgr.load(Path(workflow_path), Config.get_config_dir())
            
            # Validate workflow
            warnings = workflow_mgr.validate(workflow)
            for warning in warnings:
                logger.warning(f"Workflow: {warning}")
            
            # Generate prompt with per-monitor template
            template_path = config.monitors.get_template_path(monitor_index, config.prompt.default_template)
            prompts = prompt_gen.generate_prompt_pair(monitor_index=monitor_index, template_path=template_path)
            result = client.generate(workflow, prompts)
            
            output_path = config.monitors.get_output_path(monitor_index)
            target.save_wallpaper(result.image_data, output_path)
            
            # Save to history
            history_entry = history.save_wallpaper(
                image_data=result.image_data,
                generation_result=result,
                prompt_result=prompts,
                monitor_index=monitor_index,
                template=template_path,
                workflow=workflow_path
            )
            logger.info(f"Saved to history: {history_entry.filename}")
            
            target.set_wallpaper(output_path, monitor_index)
            
            success_count += 1
            logger.info(f"Monitor {monitor_index}: OK")
            
        except (ConfigError, GenerationError, WorkflowError, PromptError, CommandError) as e:
            error_msg = f"Monitor {monitor_index}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Monitor {monitor_index}: Unexpected error: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    logger.info(f"Completed: {success_count}/{config.monitors.count} monitors")
    
    if success_count < config.monitors.count:
        error_summary = f"Failed to generate {len(errors)}/{config.monitors.count} wallpapers"
        if errors:
            error_summary += ". Errors: " + "; ".join(errors[:3])  # Show first 3 errors
            if len(errors) > 3:
                error_summary += f" (and {len(errors) - 3} more)"
        raise GenerationError(error_summary)
