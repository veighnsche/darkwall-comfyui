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
    client = ComfyClient(config)
    if client.health_check():
        print(f"  Connection: ✓ OK")
    else:
        print(f"  Connection: ✗ UNREACHABLE")
    
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
        prompt_gen = PromptGenerator(config)
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
