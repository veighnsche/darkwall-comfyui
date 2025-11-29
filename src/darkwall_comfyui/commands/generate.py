"""Generation commands.

REQ-MONITOR-001: Auto-detection via compositor
REQ-MONITOR-002: Compositor names as identifiers  
REQ-MONITOR-008: Independent template selection per monitor
TEAM_002: REQ-WORKFLOW-002 - Optional prompt filtering per workflow

TEAM_003: Consolidated from generate_v2.py - single canonical implementation.
"""

import logging
import random
from pathlib import Path
from typing import List, Optional

from tqdm import tqdm

from ..config import (
    Config,
    ConfigV2,
    NamedStateManager,
    PerMonitorConfig,
)
from ..comfy import ComfyClient, WorkflowManager
from ..prompt_generator import PromptGenerator
from ..wallpaper import WallpaperTarget
from ..history import WallpaperHistory
from ..exceptions import ConfigError, WorkflowError, GenerationError, PromptError, CommandError

logger = logging.getLogger(__name__)

_progress_bars = {}


def _get_available_prompts(config: ConfigV2) -> List[str]:
    """
    Get list of available prompt templates from the theme.
    
    TEAM_002: Helper for REQ-WORKFLOW-002 prompt filtering.
    
    Returns:
        List of prompt filenames (e.g., ["default.prompt", "cinematic.prompt"])
    """
    config_dir = Config.get_config_dir()
    
    # Try theme-aware path first
    theme_name = config.prompt.theme
    if config.themes and theme_name in config.themes:
        theme = config.themes[theme_name]
        prompts_dir = config_dir / "themes" / theme_name / theme.prompts_dir
    else:
        # Legacy fallback
        prompts_dir = config_dir / "prompts"
    
    if not prompts_dir.exists():
        return [config.prompt.default_template]
    
    prompts = []
    for f in prompts_dir.iterdir():
        if f.is_file() and f.suffix == ".prompt":
            prompts.append(f.name)
    
    return prompts if prompts else [config.prompt.default_template]


def _select_template_for_workflow(
    config: ConfigV2,
    workflow_id: str,
    monitor_name: str,
    seed: int,
) -> str:
    """
    Select a template for a workflow, applying optional filtering.
    
    TEAM_002: REQ-WORKFLOW-002 - Optional prompt filtering per workflow.
    REQ-WORKFLOW-003 - Seeded random selection.
    
    Args:
        config: ConfigV2 instance
        workflow_id: Workflow ID (filename without .json)
        monitor_name: Monitor name for seed variation
        seed: Base seed for deterministic selection
        
    Returns:
        Selected template filename
    """
    available = _get_available_prompts(config)
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
    config: ConfigV2,
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
    
    Args:
        config: ConfigV2 instance
        monitor_name: Compositor output name (e.g., "DP-1")
        dry_run: If True, show what would be done without executing
        workflow_override: Optional workflow path override
        template_override: Optional template path override
    """
    monitor_config = config.get_monitor_config(monitor_name)
    if not monitor_config:
        raise ConfigError(f"Monitor '{monitor_name}' not configured")
    
    # Get paths
    output_path = monitor_config.get_output_path()
    workflow_path = workflow_override or str(monitor_config.get_workflow_path(Config.get_config_dir()))
    workflow_id = monitor_config.workflow  # TEAM_002: Get workflow ID for prompt filtering
    
    # TEAM_002: REQ-WORKFLOW-002 - Select template based on workflow config
    prompt_gen = PromptGenerator(config.prompt, Config.get_config_dir())
    monitor_seed_offset = hash(monitor_name) % 10000
    base_seed = prompt_gen.get_time_slot_seed(monitor_index=monitor_seed_offset)
    
    if template_override:
        template_path = template_override
    else:
        template_path = _select_template_for_workflow(config, workflow_id, monitor_name, base_seed)
    
    if dry_run:
        print(f"DRY RUN: Would generate wallpaper for monitor {monitor_name}")
        print(f"  Output path: {output_path}")
        print(f"  ComfyUI URL: {config.comfyui.base_url}")
        print(f"  Workflow: {workflow_path} (ID: {workflow_id})")
        print(f"  Template: {template_path}")
        
        # Show workflow prompt filtering info
        available = _get_available_prompts(config)
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
    
    # Save wallpaper (using legacy MonitorConfig wrapper for compatibility)
    from ..config import MonitorConfig, OutputConfig
    legacy_monitor_config = MonitorConfig(
        count=1,
        pattern=str(output_path),
        command=config.monitors.command,
    )
    target = WallpaperTarget(legacy_monitor_config, config.output)
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


def generate_next(config: ConfigV2, dry_run: bool = False) -> None:
    """
    Generate wallpaper for the next monitor in rotation.
    
    Uses NamedStateManager for name-based rotation.
    """
    active_monitors = config.get_active_monitor_names()
    if not active_monitors:
        raise ConfigError("No active monitors configured")
    
    state = NamedStateManager(active_monitors)
    
    if dry_run:
        next_monitor = state.peek_next_monitor()
        print(f"DRY RUN: Next monitor in rotation: {next_monitor}")
        generate_for_monitor(config, next_monitor, dry_run=True)
        return
    
    next_monitor = state.get_next_monitor()
    generate_for_monitor(config, next_monitor)


def generate_all(config: ConfigV2, dry_run: bool = False) -> None:
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
