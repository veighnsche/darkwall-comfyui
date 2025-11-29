"""Generation commands.

REQ-MONITOR-001: Auto-detection via compositor
REQ-MONITOR-002: Compositor names as identifiers  
REQ-MONITOR-008: Independent template selection per monitor
TEAM_002: REQ-WORKFLOW-002 - Optional prompt filtering per workflow

TEAM_003: Consolidated from generate_v2.py - single canonical implementation.
"""

import logging
import random
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from tqdm import tqdm

from ..config import (
    Config,
    NamedStateManager,
    PerMonitorConfig,
    ThemeConfig,
)
# TEAM_006: ConfigV2 deleted - merged into Config
from ..comfy import ComfyClient, WorkflowManager
from ..prompt_generator import PromptGenerator
from ..wallpaper import WallpaperTarget
from ..history import WallpaperHistory
from ..schedule import ThemeScheduler
from ..exceptions import ConfigError, WorkflowError, GenerationError, PromptError, CommandError

logger = logging.getLogger(__name__)

_progress_bars = {}


def _get_available_prompts(config: Config, theme_name: Optional[str] = None) -> List[str]:
    """
    Get list of available prompt templates from the theme.
    
    TEAM_002: Helper for REQ-WORKFLOW-002 prompt filtering.
    TEAM_006: Added theme_name parameter for scheduler-selected themes.
    
    Args:
        config: Config instance
        theme_name: Optional theme name override (from scheduler)
    
    Returns:
        List of prompt filenames (e.g., ["default.prompt", "cinematic.prompt"])
    """
    config_dir = Config.get_config_dir()
    
    # Use provided theme or fall back to config default
    effective_theme = theme_name or config.prompt.theme
    
    # Try theme-aware path first
    if config.themes and effective_theme in config.themes:
        theme = config.themes[effective_theme]
        prompts_dir = config_dir / "themes" / effective_theme / theme.prompts_dir
    else:
        # Legacy fallback
        prompts_dir = config_dir / "prompts"
    
    if not prompts_dir.exists():
        logger.warning(f"Prompts directory not found: {prompts_dir}")
        return [config.prompt.default_template]
    
    prompts = []
    for f in prompts_dir.iterdir():
        if f.is_file() and f.suffix == ".prompt":
            prompts.append(f.name)
    
    logger.debug(f"Found {len(prompts)} prompts in {prompts_dir}: {prompts}")
    return prompts if prompts else [config.prompt.default_template]


def _select_template_for_workflow(
    config: Config,
    workflow_id: str,
    monitor_name: str,
    seed: int,
    theme_name: Optional[str] = None,
) -> str:
    """
    Select a template for a workflow, applying optional filtering.
    
    TEAM_006: Added theme_name for scheduler-selected themes.
    """
    available = _get_available_prompts(config, theme_name)
    eligible = config.get_eligible_prompts_for_workflow(workflow_id, available)
    
    if not eligible:
        logger.warning(f"No eligible prompts for workflow '{workflow_id}', using default")
        return config.prompt.default_template
    
    # REQ-WORKFLOW-003: Seeded random selection
    combined_seed = seed + hash(monitor_name) % 10000
    rng = random.Random(combined_seed)
    selected = rng.choice(eligible)
    
    logger.debug(f"Selected template '{selected}' for workflow '{workflow_id}' (from {len(eligible)} eligible)")
    return selected


def _proxy_ws_event_to_stdout(event: object) -> None:
    """Forward ComfyUI websocket events to stdout."""
    try:
        if isinstance(event, dict):
            event_type = event.get("type")
            data = event.get("data", {})

            if event_type == "executing" and isinstance(data, dict):
                prompt_id = data.get("prompt_id")
                node = data.get("node")

                if node is None:
                    bar = _progress_bars.pop(prompt_id, None)
                    if bar is not None:
                        bar.close()
                    msg = f"[comfy] done prompt_id={prompt_id}"
                else:
                    msg = f"[comfy] executing node={node} prompt_id={prompt_id}"

                print(msg, flush=True)
                return

            if event_type == "progress" and isinstance(data, dict):
                prompt_id = data.get("prompt_id")
                node = data.get("node")
                value = data.get("value")
                max_value = data.get("max")

                if prompt_id and isinstance(value, (int, float)) and isinstance(max_value, (int, float)):
                    bar = _progress_bars.get(prompt_id)
                    if bar is None or bar.total != max_value:
                        if bar is not None:
                            bar.close()
                        bar = tqdm(total=max_value, desc=f"comfy {node}", leave=False)
                        _progress_bars[prompt_id] = bar

                    if value < bar.n:
                        bar.close()
                        bar = tqdm(total=max_value, desc=f"comfy {node}", leave=False)
                        _progress_bars[prompt_id] = bar

                    delta = value - bar.n
                    if delta > 0:
                        bar.update(delta)
                return
    except Exception:
        pass


def generate_for_monitor(
    config: Config,
    monitor_name: str,
    dry_run: bool = False,
    workflow_override: Optional[str] = None,
    template_override: Optional[str] = None,
) -> None:
    """
    Generate wallpaper for a specific monitor by name.
    
    REQ-MONITOR-002: Uses compositor output name.
    REQ-MONITOR-008: Independent template selection.
    TEAM_002: REQ-WORKFLOW-002 - Optional prompt filtering per workflow.
    TEAM_006: Uses ThemeScheduler to determine current theme and workflow.
    
    Args:
        config: Config instance
        monitor_name: Compositor output name (e.g., "DP-1")
        dry_run: If True, show what would be done without executing
        workflow_override: Optional workflow path override
        template_override: Optional template path override
    """
    monitor_config = config.get_monitor_config(monitor_name)
    if not monitor_config:
        raise ConfigError(f"Monitor '{monitor_name}' not configured")
    
    # TEAM_006: Get current theme from scheduler
    current_theme_name = config.prompt.theme  # Default
    current_theme: Optional[ThemeConfig] = None
    
    if config.schedule:
        scheduler = ThemeScheduler(config.schedule)
        theme_result = scheduler.get_current_theme()
        current_theme_name = theme_result.theme
        
        # TEAM_006: Determine if night by checking if theme is in night_themes list
        night_theme_names = [t.name for t in config.schedule.get_night_themes()]
        day_theme_names = [t.name for t in config.schedule.get_day_themes()]
        
        if current_theme_name in night_theme_names:
            period = "night"
            themes = config.schedule.get_night_themes()
        else:
            period = "day"
            themes = config.schedule.get_day_themes()
        
        # Find the weight of the selected theme
        theme_weight = next((t.weight for t in themes if t.name == current_theme_name), 1.0)
        total_weight = sum(t.weight for t in themes)
        theme_pct = (theme_weight / total_weight) * 100 if total_weight > 0 else 100
        
        logger.info(f"Theme scheduler: {current_theme_name} ({period}, weight: {theme_pct:.0f}%)")
    
    # Get theme config if available
    selected_workflow_prefix = None
    if config.themes and current_theme_name in config.themes:
        current_theme = config.themes[current_theme_name]
        # TEAM_006: Use weighted workflow selection if configured
        if current_theme.workflows:
            selected_workflow_prefix = current_theme.select_workflow_prefix()
            logger.info(f"Using theme '{current_theme_name}' with workflow: {selected_workflow_prefix} (from: {current_theme.get_workflow_weights_display()})")
        else:
            selected_workflow_prefix = current_theme.workflow_prefix
            logger.info(f"Using theme '{current_theme_name}' with workflow_prefix: {selected_workflow_prefix}")
    
    # Get paths - use theme's workflow_prefix if available
    output_path = monitor_config.get_output_path()
    
    if workflow_override:
        workflow_path = workflow_override
        workflow_id = Path(workflow_override).stem
    elif selected_workflow_prefix and monitor_config.resolution:
        # TEAM_006: Build workflow from selected prefix + monitor resolution
        workflow_id = f"{selected_workflow_prefix}-{monitor_config.resolution}"
        workflow_path = str(Config.get_config_dir() / "workflows" / f"{workflow_id}.json")
        logger.info(f"Theme-based workflow: {workflow_id}")
    else:
        # Fallback to monitor's configured workflow
        workflow_path = str(monitor_config.get_workflow_path(Config.get_config_dir()))
        workflow_id = monitor_config.workflow
    
    # TEAM_006: Use theme-aware PromptGenerator
    if current_theme_name and config.themes and current_theme_name in config.themes:
        # Use theme-aware paths for atoms and prompts
        prompt_gen = PromptGenerator.from_config(config, current_theme_name)
        logger.info(f"Using theme-aware prompt generator for '{current_theme_name}'")
    else:
        # Fallback to default paths
        prompt_gen = PromptGenerator(config.prompt, Config.get_config_dir())
    monitor_seed_offset = hash(monitor_name) % 10000
    base_seed = prompt_gen.get_time_slot_seed(monitor_index=monitor_seed_offset)
    
    if template_override:
        template_path = template_override
    else:
        # TEAM_006: Pass current theme to get theme-specific prompts
        template_path = _select_template_for_workflow(config, workflow_id, monitor_name, base_seed, current_theme_name)
    
    if dry_run:
        print(f"DRY RUN: Would generate wallpaper for monitor {monitor_name}")
        print(f"  Theme: {current_theme_name}")
        if current_theme and current_theme.workflow_prefix:
            print(f"  Theme workflow_prefix: {current_theme.workflow_prefix}")
        print(f"  Output path: {output_path}")
        print(f"  ComfyUI URL: {config.comfyui.base_url}")
        print(f"  Workflow: {workflow_path} (ID: {workflow_id})")
        print(f"  Template: {template_path}")
        
        # Show workflow prompt filtering info
        available = _get_available_prompts(config, current_theme_name)
        eligible = config.get_eligible_prompts_for_workflow(workflow_id, available)
        if len(eligible) < len(available):
            print(f"  Eligible prompts: {eligible} (filtered from {len(available)} available)")
        
        try:
            prompt = prompt_gen.generate_prompt(
                monitor_index=monitor_seed_offset,
                template_path=template_path,
            )
            print(f"  Prompt: {prompt[:100]}...")
        except PromptError as e:
            print(f"  Prompt error: {e}")
        
        print("DRY RUN: No actual changes made")
        return
    
    logger.info(f"Generating wallpaper for monitor {monitor_name}")
    logger.info(f"Output: {output_path}")
    logger.info(f"Workflow: {workflow_path} (ID: {workflow_id})")
    logger.info(f"Template: {template_path}")
    
    # Generate prompt with monitor-specific seed
    prompts = prompt_gen.generate_prompt_pair(
        monitor_index=monitor_seed_offset,
        template_path=template_path,
    )
    logger.info(f"Prompt: {prompts.positive[:100]}...")
    if prompts.negative:
        logger.info(f"Negative: {prompts.negative[:100]}...")
    
    # Load workflow
    workflow_mgr = WorkflowManager(config.comfyui)
    workflow = workflow_mgr.load(Path(workflow_path), Config.get_config_dir())
    
    # Generate image
    client = ComfyClient(config.comfyui)
    if not client.health_check():
        raise GenerationError(f"ComfyUI not reachable at {config.comfyui.base_url}")
    
    result = client.generate(workflow, prompts, on_event=_proxy_ws_event_to_stdout)
    logger.info(f"Generated: {result.filename}")
    
    # TEAM_006: Use MonitorsConfig directly (no legacy wrapper)
    target = WallpaperTarget(config.monitors, config.output)
    saved_path = target.save_wallpaper(result.image_data, output_path)
    
    # Save to history
    history = WallpaperHistory(config.history if hasattr(config, 'history') else None)
    history_entry = history.save_wallpaper(
        image_data=result.image_data,
        generation_result=result,
        prompt_result=prompts,
        monitor_index=monitor_seed_offset,
        template=template_path,
        workflow=workflow_path,
        seed=getattr(prompts, "seed", None),
    )
    logger.info(f"Saved to history: {history_entry.filename}")
    
    # Set wallpaper
    if target.set_wallpaper_by_name(saved_path, monitor_name):
        logger.info(f"Wallpaper set for monitor {monitor_name}")
    else:
        logger.warning("Failed to set wallpaper (image saved successfully)")
    
    # TEAM_006: Save generation state for retry functionality
    active_monitors = config.get_active_monitor_names()
    state_mgr = NamedStateManager(active_monitors)
    state_mgr.save_last_generation(
        monitor_name=monitor_name,
        theme_name=current_theme_name,
        workflow_id=workflow_id,
        template=template_path,
        prompt=prompts.positive,
        negative_prompt=prompts.negative,
        seed=base_seed,
        output_path=str(saved_path),
        history_path=str(history_entry.path) if history_entry else None,
    )
    
    # TEAM_004: Send notification if enabled
    if config.notifications:
        from ..notifications import NotificationSender
        notifier = NotificationSender(config.notifications)
        notifier.notify_wallpaper_changed(
            monitor_name=monitor_name,
            image_path=saved_path,
            prompt=prompts.positive[:100] if prompts.positive else None,
        )
    
    logger.info("Generation complete")


def generate_next(
    config: Config,
    dry_run: bool = False,
    workflow_path: Optional[str] = None,
    template_path: Optional[str] = None,
) -> None:
    """
    Generate wallpaper for the next monitor in rotation.
    
    Uses NamedStateManager for name-based rotation.
    
    Args:
        config: Config instance
        dry_run: If True, show what would be done without executing
        workflow_path: Optional workflow path override
        template_path: Optional template path override
    """
    active_monitors = config.get_active_monitor_names()
    if not active_monitors:
        raise ConfigError("No active monitors configured")
    
    state = NamedStateManager(active_monitors)
    
    if dry_run:
        next_monitor = state.peek_next_monitor()
        print(f"DRY RUN: Next monitor in rotation: {next_monitor}")
        generate_for_monitor(config, next_monitor, dry_run=True, 
                           workflow_override=workflow_path, template_override=template_path)
        return
    
    next_monitor = state.get_next_monitor()
    generate_for_monitor(config, next_monitor, 
                        workflow_override=workflow_path, template_override=template_path)


def generate_all(config: Config, dry_run: bool = False) -> None:
    """
    Generate wallpapers for all active monitors.
    
    REQ-MONITOR-008: Each monitor gets independent template selection.
    """
    active_monitors = config.get_active_monitor_names()
    if not active_monitors:
        raise ConfigError("No active monitors configured")
    
    if dry_run:
        print(f"DRY RUN: Would generate wallpapers for {len(active_monitors)} monitors:")
        for name in active_monitors:
            print(f"\n--- Monitor: {name} ---")
            generate_for_monitor(config, name, dry_run=True)
        print("\nDRY RUN: No actual changes made")
        return
    
    logger.info(f"Generating for all {len(active_monitors)} monitors")
    
    success_count = 0
    errors = []
    
    for monitor_name in active_monitors:
        logger.info(f"--- Monitor: {monitor_name} ---")
        
        try:
            generate_for_monitor(config, monitor_name)
            success_count += 1
            logger.info(f"Monitor {monitor_name}: OK")
        except (ConfigError, GenerationError, WorkflowError, PromptError, CommandError) as e:
            error_msg = f"Monitor {monitor_name}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Monitor {monitor_name}: Unexpected error: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    logger.info(f"Completed: {success_count}/{len(active_monitors)} monitors")
    
    if success_count < len(active_monitors):
        error_summary = f"Failed to generate {len(errors)}/{len(active_monitors)} wallpapers"
        if errors:
            error_summary += ". Errors: " + "; ".join(errors[:3])
            if len(errors) > 3:
                error_summary += f" (and {len(errors) - 3} more)"
        raise GenerationError(error_summary)


# TEAM_003: Alias for CLI compatibility
generate_once = generate_next


def retry_last(
    config: Config,
    dry_run: bool = False,
    delete_failed: bool = True,
) -> None:
    """
    Retry the last generation with a new seed but same prompt.
    
    TEAM_006: For fixing failed generations (4 arms, bad anatomy, etc.)
    
    Args:
        config: Config instance
        dry_run: If True, show what would be done without executing
        delete_failed: If True, delete the failed wallpaper before regenerating
    """
    active_monitors = config.get_active_monitor_names()
    if not active_monitors:
        raise ConfigError("No active monitors configured")
    
    state_mgr = NamedStateManager(active_monitors)
    last_gen = state_mgr.get_last_generation()
    
    if not last_gen:
        raise CommandError("No previous generation found to retry")
    
    monitor_name = last_gen['monitor_name']
    theme_name = last_gen['theme_name']
    workflow_id = last_gen['workflow_id']
    template = last_gen['template']
    prompt = last_gen['prompt']
    negative_prompt = last_gen.get('negative_prompt')
    old_seed = last_gen['seed']
    output_path = last_gen['output_path']
    history_path = last_gen.get('history_path')
    
    # Generate new seed (different from old)
    new_seed = random.randint(0, 2**32 - 1)
    while new_seed == old_seed:
        new_seed = random.randint(0, 2**32 - 1)
    
    if dry_run:
        print(f"DRY RUN: Would retry last generation")
        print(f"  Monitor: {monitor_name}")
        print(f"  Theme: {theme_name}")
        print(f"  Workflow: {workflow_id}")
        print(f"  Template: {template}")
        print(f"  Prompt: {prompt[:100]}...")
        if negative_prompt:
            print(f"  Negative: {negative_prompt[:80]}...")
        print(f"  Old seed: {old_seed}")
        print(f"  New seed: {new_seed}")
        if delete_failed:
            print(f"  Would delete: {output_path}")
            if history_path:
                print(f"  Would delete history: {history_path}")
        print("DRY RUN: No actual changes made")
        return
    
    logger.info(f"Retrying last generation for {monitor_name}")
    logger.info(f"Old seed: {old_seed} -> New seed: {new_seed}")
    
    # Delete failed wallpaper if requested
    if delete_failed:
        output_file = Path(output_path)
        if output_file.exists():
            output_file.unlink()
            logger.info(f"Deleted failed wallpaper: {output_path}")
        
        if history_path:
            history_file = Path(history_path)
            if history_file.exists():
                history_file.unlink()
                logger.info(f"Deleted from history: {history_path}")
    
    # Get monitor config
    monitor_config = config.get_monitor_config(monitor_name)
    if not monitor_config:
        raise ConfigError(f"Monitor '{monitor_name}' not configured")
    
    # Build workflow path
    workflow_path = str(Config.get_config_dir() / "workflows" / f"{workflow_id}.json")
    
    # Create prompt result with the same prompt but new seed
    from ..prompt_generator import PromptResult
    prompts = PromptResult(
        positive=prompt,
        negative=negative_prompt,
        seed=new_seed,
    )
    
    logger.info(f"Generating with same prompt, new seed {new_seed}")
    logger.info(f"Workflow: {workflow_path}")
    logger.info(f"Prompt: {prompt[:100]}...")
    
    # Load workflow
    workflow_mgr = WorkflowManager(config.comfyui)
    workflow = workflow_mgr.load(Path(workflow_path), Config.get_config_dir())
    
    # Generate image
    client = ComfyClient(config.comfyui)
    if not client.health_check():
        raise GenerationError(f"ComfyUI not reachable at {config.comfyui.base_url}")
    
    result = client.generate(workflow, prompts, on_event=_proxy_ws_event_to_stdout)
    logger.info(f"Generated: {result.filename}")
    
    # Save wallpaper
    target = WallpaperTarget(config.monitors, config.output)
    saved_path = target.save_wallpaper(result.image_data, output_path)
    
    # Save to history
    history = WallpaperHistory(config.history if hasattr(config, 'history') else None)
    history_entry = history.save_wallpaper(
        image_data=result.image_data,
        generation_result=result,
        prompt_result=prompts,
        monitor_index=hash(monitor_name) % 10000,
        template=template,
        workflow=workflow_path,
        seed=new_seed,
    )
    logger.info(f"Saved to history: {history_entry.filename}")
    
    # Set wallpaper
    if target.set_wallpaper_by_name(saved_path, monitor_name):
        logger.info(f"Wallpaper set for monitor {monitor_name}")
    else:
        logger.warning("Failed to set wallpaper (image saved successfully)")
    
    # Update generation state with new seed
    state_mgr.save_last_generation(
        monitor_name=monitor_name,
        theme_name=theme_name,
        workflow_id=workflow_id,
        template=template,
        prompt=prompt,
        negative_prompt=negative_prompt,
        seed=new_seed,
        output_path=str(saved_path),
        history_path=str(history_entry.path) if history_entry else None,
    )
    
    logger.info(f"Retry complete (seed {old_seed} -> {new_seed})")
