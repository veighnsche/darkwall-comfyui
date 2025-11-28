# Example: Integrating DarkWall ComfyUI into classic NixOS configuration

## Option 1: Import via pkgs/darkwall-comfyui.nix (Recommended)

Add to your `/home/vince/nixos/home/default.nix`:

```nix
{ pkgs, ... }:
let
  # Import the darkwall-comfyui package from your local development
  darkwall-comfyui = pkgs.callPackage /home/vince/Projects/darkwall-comfyui/pkgs/darkwall-comfyui.nix { inherit pkgs; };
in
{
  home.packages = [
    darkwall-comfyui
  ];

  # Systemd user service for automatic wallpaper generation
  systemd.user.services.darkwall-comfyui = {
    Unit = {
      Description = "Generate dark-mode wallpaper using ComfyUI";
      After = [ "network-online.target" ];
    };
    
    Service = {
      Type = "oneshot";
      ExecStart = "${darkwall-comfyui}/bin/generate-wallpaper-once generate";
      Environment = {
        COMFYUI_BASE_URL = "https://comfyui.home.arpa";
        TIME_SLOT_MINUTES = "30";
        WALLPAPER_OUTPUT_PATH = "%h/Pictures/wallpapers/current.png";
        DARKWALL_LOG_LEVEL = "INFO";
      };
    };
  };

  # Timer for automatic generation every 30 minutes
  systemd.user.timers.darkwall-comfyui = {
    Unit = {
      Description = "Periodic wallpaper generation";
    };
    
    Timer = {
      OnCalendar = "*:0/30";  # Every 30 minutes
      Persistent = true;
    };
    
    Install.WantedBy = [ "timers.target" ];
  };
}
```

## Option 2: Direct flake import (if you enable flakes)

Add to your `/home/vince/nixos/home/default.nix`:

```nix
{ pkgs, ... }:
let
  flake = builtins.getFlake "/home/vince/Projects/darkwall-comfyui";
in
{
  home.packages = [
    flake.packages.${pkgs.system}.default
  ];

  # Same systemd configuration as above
  systemd.user.services.darkwall-comfyui = {
    # ... same service config ...
  };
}
```

## Option 3: Using Home Manager module

Add to your `/home/vince/nixos/home/default.nix`:

```nix
{ pkgs, ... }:
let
  flake = builtins.getFlake "/home/vince/Projects/darkwall-comfyui";
in
{
  imports = [
    flake.homeManagerModules.default
  ];

  services.darkwall-comfyui = {
    enable = true;
    environment = {
      COMFYUI_BASE_URL = "https://comfyui.home.arpa";
      TIME_SLOT_MINUTES = "30";
      WALLPAPER_OUTPUT_PATH = "%h/Pictures/wallpapers/current.png";
    };
    timer = {
      enable = true;
      onCalendar = "*:0/30";
    };
  };
}
```

## Usage Commands

After rebuilding your home-manager configuration:

```bash
# Initialize configuration
generate-wallpaper-once init

# Test single generation
generate-wallpaper-once --dry-run generate

# Enable automatic generation
systemctl --user enable --now darkwall-comfyui.timer

# Check status
systemctl --user status darkwall-comfyui.timer
systemctl --user status darkwall-comfyui.service

# View logs
journalctl --user -u darkwall-comfyui.service

# Generate for all monitors
generate-wallpaper-once generate-all

# Show status
generate-wallpaper-once status
```

## Configuration

Edit your config file after initialization:
```bash
nano ~/.config/darkwall-comfyui/config.toml
```

Example multi-monitor config:
```toml
[comfyui]
base_url = "https://comfyui.home.arpa"
workflow_path = "workflows/qwen_t2i.json"
timeout = 300
poll_interval = 5

[monitors]
count = 2
command = "swww"
pattern = "monitor_{index}.png"
backup_pattern = "monitor_{index}_{timestamp}.png"

[output]
directory = "~/Pictures/wallpapers"
create_backup = true

[prompt]
atoms_dir = "atoms"
time_slot_minutes = 30
default_template = "default.prompt"

[history]
enabled = true
max_entries = 1000

[logging]
level = "INFO"
```

## Development Workflow

For quick iteration during development:

```bash
cd /home/vince/Projects/darkwall-comfyui

# Build and install locally
nix build
nix profile install .

# Test changes
./result/bin/generate-wallpaper-once --dry-run generate

# When ready, rebuild home-manager to pick up changes
home-manager switch --flake .#vince
```
