"""Status command."""

import os
import stat
from pathlib import Path

from ..config import Config, StateManager
from ..prompt_generator import PromptGenerator
from ..comfy import ComfyClient


def show_status(config: Config) -> None:
    """Display current configuration and status."""
    
    print("DarkWall ComfyUI Status")
    print("=" * 40)
    
    # Config info
    print(f"\nConfiguration")
    print(f"  Config dir: {Config.get_config_dir()}")
    print(f"  ComfyUI:    {config.comfyui.base_url}")
    print(f"  Monitors:   {config.monitors.count}")
    print(f"  Command:    {config.monitors.command}")
    print(f"  Pattern:    {config.monitors.pattern}")
    print(f"  Time slot:  {config.prompt.time_slot_minutes} min")
    
    # ComfyUI connectivity
    print(f"\nComfyUI Status")
    client = ComfyClient(config.comfyui)
    health = client.detailed_health_check()
    
    if health['healthy']:
        print(f"  Connection: ✓ OK")
        if health['response_time_ms']:
            print(f"  Response:   {health['response_time_ms']}ms")
        
        # Show system stats if available
        if health['system_stats']:
            stats = health['system_stats']
            if 'devices' in stats:
                devices = stats['devices']
                if devices:
                    print(f"  Devices:    {len(devices)} detected")
                    for device in devices[:2]:  # Show first 2 devices
                        device_type = device.get('type', 'unknown')
                        device_name = device.get('name', 'unknown')
                        memory = device.get('vram_total_mb', 0)
                        if memory:
                            print(f"    - {device_type}: {device_name} ({memory}MB VRAM)")
                        else:
                            print(f"    - {device_type}: {device_name}")
            if 'queue_status' in stats:
                queue = stats['queue_status']
                queue_running = queue.get('queue_running', 0)
                queue_pending = queue.get('queue_pending', 0)
                if queue_running > 0 or queue_pending > 0:
                    print(f"  Queue:      {queue_running} running, {queue_pending} pending")
    else:
        print(f"  Connection: ✗ UNREACHABLE")
        if health['error']:
            print(f"  Error:      {health['error']}")
        print(f"  URL:        {health['url']}")
    
    # Rotation state
    print(f"\nRotation State")
    state_mgr = StateManager(config)
    state = state_mgr.get_state()
    last = state.get('last_monitor_index', -1)
    count = state.get('rotation_count', 0)
    
    if last >= 0:
        next_idx = (last + 1) % config.monitors.count
        print(f"  Last:       Monitor {last}")
        print(f"  Next:       Monitor {next_idx}")
    else:
        print(f"  Next:       Monitor 0 (first run)")
    print(f"  Rotations:  {count}")
    
    # Atom counts
    print(f"\nPrompt Atoms")
    try:
        prompt_gen = PromptGenerator(config.prompt, Config.get_config_dir())
        for pillar, atoms in prompt_gen.atoms.items():
            print(f"  {pillar:12} {len(atoms)} atoms")
    except FileNotFoundError as e:
        print(f"  ERROR: {e}")
    
    # File permissions
    print(f"\nFile Permissions")
    config_dir = Config.get_config_dir()
    
    def check_file(path: Path) -> str:
        if not path.exists():
            return "MISSING"
        writable = os.access(path, os.W_OK)
        perms = stat.filemode(path.stat().st_mode)
        return f"{perms} {'✓' if writable else '✗ READ-ONLY'}"
    
    print(f"  config.toml: {check_file(config_dir / 'config.toml')}")
    
    atoms_dir = config_dir / "atoms"
    if atoms_dir.exists():
        for f in sorted(atoms_dir.iterdir()):
            if f.is_file():
                print(f"  atoms/{f.name}: {check_file(f)}")
    else:
        print(f"  atoms/: MISSING")
    
    # Wallpaper status
    print(f"\nWallpapers")
    for i in range(config.monitors.count):
        path = config.monitors.get_output_path(i)
        if path.exists():
            size_kb = path.stat().st_size / 1024
            print(f"  Monitor {i}: {path.name} ({size_kb:.0f} KB)")
        else:
            print(f"  Monitor {i}: not generated")
