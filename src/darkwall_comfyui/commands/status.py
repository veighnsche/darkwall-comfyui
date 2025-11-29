"""Status command.

TEAM_004: REQ-MISC-003 - JSON status output for waybar/polybar.
"""

import json
import os
import stat
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..config import Config, NamedStateManager
from ..prompt_generator import PromptGenerator
from ..comfy import ComfyClient

# TEAM_006: ConfigV2 deleted - merged into Config


def _get_comfyui_status(config: Config) -> Dict[str, Any]:
    """Get ComfyUI health status."""
    client = ComfyClient(config.comfyui)
    health = client.detailed_health_check()
    
    return {
        "healthy": health.get("healthy", False),
        "url": health.get("url", config.comfyui.base_url),
        "response_time_ms": health.get("response_time_ms"),
        "error": health.get("error"),
        "devices": health.get("system_stats", {}).get("devices", []),
        "queue": health.get("system_stats", {}).get("queue_status", {}),
    }


def _get_schedule_status(config: Config) -> Optional[Dict[str, Any]]:
    """Get theme schedule status."""
    if not config.schedule:
        return None
    
    from ..schedule import ThemeScheduler
    scheduler = ThemeScheduler(config.schedule)
    return scheduler.to_json()


def _get_monitors_status(config: Config) -> Dict[str, Any]:
    """Get monitors status."""
    monitors = {}
    
    for name in config.monitors.get_monitor_names():
        monitor = config.monitors.get_monitor(name)
        if monitor:
            output_path = monitor.get_output_path()
            monitors[name] = {
                "workflow": monitor.workflow,
                "output": str(output_path),
                "exists": output_path.exists(),
                "size_kb": output_path.stat().st_size / 1024 if output_path.exists() else 0,
                "active": name in config.active_monitors,
            }
    
    return monitors


def get_status_json(config: Config) -> Dict[str, Any]:
    """
    Get full status as JSON-serializable dict.
    
    TEAM_004: REQ-MISC-003 - For waybar/polybar integration.
    """
    status = {
        "config_dir": str(Config.get_config_dir()),
        "comfyui": _get_comfyui_status(config),
        "monitors": _get_monitors_status(config),
        "active_monitors": config.active_monitors,
        "theme": config.prompt.theme,
        "time_slot_minutes": config.prompt.time_slot_minutes,
    }
    
    # Add schedule info if configured
    schedule = _get_schedule_status(config)
    if schedule:
        status["schedule"] = schedule
    
    # Add rotation state
    if config.active_monitors:
        state_mgr = NamedStateManager(config.active_monitors)
        status["rotation"] = {
            "next_monitor": state_mgr.peek_next_monitor(),
            "rotation_count": state_mgr.get_state().get("rotation_count", 0),
        }
    
    return status


def show_status(config: Config, json_output: bool = False) -> None:
    """
    Display current configuration and status.
    
    TEAM_006: Uses Config (ConfigV2 merged).
    
    Args:
        config: Config instance
        json_output: If True, output JSON instead of human-readable text
    """
    if json_output:
        status = get_status_json(config)
        print(json.dumps(status, indent=2))
        return
    
    print("DarkWall ComfyUI Status")
    print("=" * 40)
    
    # Config info
    print(f"\nConfiguration")
    print(f"  Config dir: {Config.get_config_dir()}")
    print(f"  ComfyUI:    {config.comfyui.base_url}")
    print(f"  Monitors:   {len(config.active_monitors)} active")
    print(f"  Theme:      {config.prompt.theme}")
    print(f"  Time slot:  {config.prompt.time_slot_minutes} min")
    
    # ComfyUI connectivity
    print(f"\nComfyUI Status")
    comfyui_status = _get_comfyui_status(config)
    
    if comfyui_status['healthy']:
        print(f"  Connection: ✓ OK")
        if comfyui_status['response_time_ms']:
            print(f"  Response:   {comfyui_status['response_time_ms']}ms")
        
        # Show devices
        devices = comfyui_status.get('devices', [])
        if devices:
            print(f"  Devices:    {len(devices)} detected")
            for device in devices[:2]:
                device_type = device.get('type', 'unknown')
                device_name = device.get('name', 'unknown')
                memory = device.get('vram_total_mb', 0)
                if memory:
                    print(f"    - {device_type}: {device_name} ({memory}MB VRAM)")
                else:
                    print(f"    - {device_type}: {device_name}")
        
        # Show queue
        queue = comfyui_status.get('queue', {})
        queue_running = queue.get('queue_running', 0)
        queue_pending = queue.get('queue_pending', 0)
        if queue_running > 0 or queue_pending > 0:
            print(f"  Queue:      {queue_running} running, {queue_pending} pending")
    else:
        print(f"  Connection: ✗ UNREACHABLE")
        if comfyui_status['error']:
            print(f"  Error:      {comfyui_status['error']}")
        print(f"  URL:        {comfyui_status['url']}")
    
    # Schedule status
    if config.schedule:
        print(f"\nTheme Schedule")
        schedule = _get_schedule_status(config)
        if schedule:
            print(f"  Current:    {schedule['current_theme']}")
            print(f"  Day theme:  {schedule['day_theme']}")
            print(f"  Night theme: {schedule['night_theme']}")
            if schedule.get('sunset_time'):
                print(f"  Sunset:     {schedule['sunset_time']}")
            if schedule.get('sunrise_time'):
                print(f"  Sunrise:    {schedule['sunrise_time']}")
            if schedule.get('is_blend_period'):
                print(f"  Blend:      {schedule['probability']*100:.0f}% probability")
    
    # Rotation state
    print(f"\nRotation State")
    if config.active_monitors:
        state_mgr = NamedStateManager(config.active_monitors)
        next_monitor = state_mgr.peek_next_monitor()
        state = state_mgr.get_state()
        count = state.get('rotation_count', 0)
        
        print(f"  Next:       {next_monitor}")
        print(f"  Rotations:  {count}")
    else:
        print(f"  No active monitors")
    
    # Monitors status
    print(f"\nMonitors")
    monitors_status = _get_monitors_status(config)
    for name, info in monitors_status.items():
        active = "✓" if info['active'] else "✗"
        if info['exists']:
            print(f"  {active} {name}: {info['size_kb']:.0f} KB")
        else:
            print(f"  {active} {name}: not generated")
    
    # Atom counts
    print(f"\nPrompt Atoms")
    try:
        prompt_gen = PromptGenerator(config.prompt, Config.get_config_dir())
        for pillar, atoms in prompt_gen.atoms.items():
            print(f"  {pillar:12} {len(atoms)} atoms")
    except FileNotFoundError as e:
        print(f"  ERROR: {e}")
