# Usage Examples and Workflows

Practical examples for common DarkWall ComfyUI use cases and workflows.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Multi-Monitor Setups](#multi-monitor-setups)
- [Custom Workflows](#custom-workflows)
- [Prompt Templates](#prompt-templates)
- [History Management](#history-management)
- [Automation and Scripting](#automation-and-scripting)
- [Advanced Configurations](#advanced-configurations)

## Basic Usage

### Quick Start

Generate your first wallpaper:
```bash
# Initialize configuration (first time only)
darkwall init

# Generate wallpaper for next monitor
darkwall generate

# Generate for all monitors
darkwall generate-all

# Check status
darkwall status
```

### Preview Before Generation

Preview prompts without running generation:
```bash
# Preview default prompt
darkwall prompt preview

# Preview with custom template
darkwall prompt preview --template cinematic.prompt

# Preview for specific monitor with seed
darkwall prompt preview --monitor 1 --seed 12345
```

### Dry Run Testing

Test configuration without actual generation:
```bash
# Show what would be generated
darkwall --dry-run generate

# Test all monitors
darkwall --dry-run generate-all

# Test with custom workflow/template
darkwall --dry-run generate --workflow custom.json --template dark.prompt
```

## Multi-Monitor Setups

### Dual Monitor Configuration

Configure for dual monitor setup with different resolutions:

```toml
# ~/.config/darkwall-comfyui/config.toml
[monitors]
count = 2
paths = [
    "~/Pictures/wallpapers/ultrawide.png",    # Monitor 0: 3440x1440
    "~/Pictures/wallpapers/portrait.png"      # Monitor 1: 1080x1920
]
workflows = [
    "ultrawide_workflow.json",
    "portrait_workflow.json"
]
templates = [
    "ultrawide.prompt",
    "portrait.prompt"
]
```

### Triple Monitor Setup

Configure three monitors with per-monitor templates:

```toml
[monitors]
count = 3
pattern = "~/Pictures/wallpapers/monitor_{index}.png"
templates = [
    "cinematic.prompt",    # Monitor 0: Main display
    "minimal.prompt",      # Monitor 1: Side display
    "abstract.prompt"      # Monitor 2: Side display
]
```

Generate with rotation:
```bash
# Generate for next monitor in rotation
darkwall generate

# Generate all at once (uses per-monitor templates)
darkwall generate-all
```

### Different Wallpaper Setters

Use different wallpaper tools per setup:

```toml
# Sway/Wlroots (recommended)
[monitors]
command = "swaybg"

# Simple Fast Wallpaper Switcher
[monitors]
command = "swww"

# X11 with feh
[monitors]
command = "feh"

# X11 with nitrogen
[monitors]
command = "nitrogen"

# Custom command
[monitors]
command = "custom:wallpaper-setter --image {path} --monitor {index}"
```

## Custom Workflows

### High Resolution Workflow

Create workflow for 4K wallpapers:

```json
{
  "1": {
    "inputs": {
      "width": 3840,
      "height": 2160,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage"
  },
  "2": {
    "inputs": {
      "text": "__subjects/abstract__, __styles/photorealistic__",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  }
}
```

Configure per-monitor:
```toml
[monitors]
workflows = [
    "4k_workflow.json",      # Monitor 0: 4K display
    "1080p_workflow.json",   # Monitor 1: 1080p display
    "portrait_workflow.json" # Monitor 2: Portrait display
]
```

### Art Style Workflow

Create workflow for specific art style:

```bash
# Use custom workflow for generation
darkwall generate --workflow artistic_style.json

# Override template for specific mood
darkwall generate --template melancholic.prompt
```

### Workflow with Negative Prompts

Workflow supporting negative prompts:

```json
{
  "positive_prompt": {
    "inputs": {
      "text": "__subjects/nature__, __styles/artistic__",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "negative_prompt": {
    "inputs": {
      "text": "__negative/quality__, __negative/artifacts__",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode"
  }
}
```

## Prompt Templates

### Cinematic Template

Create cinematic style prompts:

```prompt
# ~/.config/darkwall-comfyui/prompts/cinematic.prompt
__subjects/characters__, __environments/cinematic__, {dramatic|epic|moody} lighting
{masterpiece|high quality|cinematic shot}, detailed, {8k|4k} resolution

---negative---
__negative/quality__, __negative/artifacts__, blurry, low quality
```

Use with preview:
```bash
darkwall prompt preview --template cinematic.prompt
```

### Minimal Template

Create minimal, clean prompts:

```prompt
# ~/.config/darkwall-comfyui/prompts/minimal.prompt
__subjects/abstract__, __styles/minimal__, clean, simple
{geometric|organic|fluid} shapes, {monochromatic|duotone} palette

---negative---
__negative/quality__, clutter, complex, detailed
```

### Cyberpunk Template

Create cyberpunk-themed prompts:

```prompt
# ~/.config/darkwall-comfyui/prompts/cyberpunk.prompt
__subjects/technology__, __environments/cyberpunk__, {neon|synthetic|digital}
{cyberpunk city|futuristic skyline|holographic displays}, {glowing|vibrant} colors

---negative---
__negative/quality__, natural, organic, daylight
```

### Template with Variants

Use variant syntax for variety:

```prompt
# Weighted variants
{0.7::masterpiece|0.2::high quality|0.1::experimental}, 
{cinematic|dramatic|moody} lighting

# Unweighted variants
{abstract|geometric|organic} shapes, {monochromatic|duotone|vibrant} palette
```

### Custom Atoms

Create custom atom categories:

```bash
# Create custom atoms directory
mkdir -p ~/.config/darkwall-comfyui/atoms/custom

# Add custom subjects
echo -e "glowing crystals\nholographic trees\ndigital waterfalls" > ~/.config/darkwall-comfyui/atoms/custom/subjects.txt

# Add custom styles
echo -e "vaporwave\nsynthwave\ncyberpunk" > ~/.config/darkwall-comfyui/atoms/custom/styles.txt

# Use in template
echo -e "__custom/subjects__, __custom/styles__, neon lighting" > ~/.config/darkwall-comfyui/prompts/custom.prompt
```

## History Management

### Browse History

List and filter wallpapers:

```bash
# List recent wallpapers
darkwall gallery list

# List favorites only
darkwall gallery list --favorites

# List specific monitor
darkwall gallery list --monitor 0

# List with limit
darkwall gallery list --limit 20

# JSON output for scripting
darkwall gallery list --format json
```

### Manage Favorites

Mark and manage favorite wallpapers:

```bash
# Get wallpaper timestamp from list
darkwall gallery list --limit 5

# Mark as favorite
darkwall gallery favorite 2025-01-28T12:00:00

# Show favorites
darkwall gallery list --favorites

# Unfavorite
darkwall gallery favorite 2025-01-28T12:00:00 --unfavorite
```

### Wallpaper Details

View detailed information:

```bash
# Show full details
darkwall gallery info 2025-01-28T12:00:00

# View prompt used
darkwall gallery info 2025-01-28T12:00:00 | grep "Positive Prompt"

# Check file location
darkwall gallery info 2025-01-28T12:00:00 | grep "Full Path"
```

### History Cleanup

Configure and run cleanup:

```toml
# ~/.config/darkwall-comfyui/config.toml
[history.cleanup_policy]
max_count = 500           # Keep max 500 wallpapers
max_days = 90            # Keep newer than 90 days
min_favorites = 10       # Always keep 10 favorites
max_size_mb = 5000       # Keep under 5GB
```

Run cleanup:
```bash
# Manual cleanup
darkwall gallery cleanup

# Check stats before/after
darkwall gallery stats
```

### Manual History Management

```bash
# Delete specific wallpaper
darkwall gallery delete 2025-01-28T12:00:00

# Batch delete old wallpapers (find + darkwall)
darkwall gallery list --format json | jq '.[] | select(.timestamp < "2025-01-01") | .timestamp' | xargs -I {} darkwall gallery delete {}
```

## Automation and Scripting

### Systemd Timer

Automatic wallpaper generation:

```ini
# ~/.config/systemd/user/darkwall.timer
[Unit]
Description=Generate wallpaper every 30 minutes

[Timer]
OnCalendar=*:0/30
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# ~/.config/systemd/user/darkwall.service
[Unit]
Description=DarkWall ComfyUI wallpaper generation

[Service]
Type=oneshot
ExecStart=/usr/bin/darkwall generate
```

Enable and start:
```bash
systemctl --user enable --now darkwall.timer
systemctl --user list-timers
```

### Cron Job

Traditional cron automation:

```bash
# Edit crontab
crontab -e

# Add line for every 30 minutes
*/30 * * * * /usr/bin/darkwall generate

# Or every hour at different times
0 * * * * /usr/bin/darkwall generate
30 * * * * /usr/bin/dashall generate --template cinematic.prompt
```

### Bash Scripts

Create custom generation scripts:

```bash
#!/bin/bash
# ~/.local/bin/darkwall-morning.sh

# Morning theme generation
darkwall generate --template morning.prompt
darkwall gallery favorite $(darkwall gallery list --limit 1 --format json | jq -r '.[0].timestamp')
```

```bash
#!/bin/bash
# ~/.local/bin/darkwall-cycle.sh

# Cycle through all templates
templates=("cinematic.prompt" "minimal.prompt" "cyberpunk.prompt")
current_template=$(cat ~/.config/darkwall-comfyui/last_template.txt || echo "0")

next_index=$(( (current_template + 1) % ${#templates[@]} ))
next_template=${templates[$next_index]}

darkwall generate --template "$next_template"
echo $next_index > ~/.config/darkwall-comfyui/last_template.txt
```

### Python Automation

Python script for advanced automation:

```python
#!/usr/bin/env python3
# darkwall_auto.py

import subprocess
import json
from datetime import datetime

def run_darkwall_command(cmd):
    """Run darkwall command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr

def get_latest_wallpaper():
    """Get latest wallpaper from history."""
    stdout, _ = run_darkwall_command("darkwall gallery list --limit 1 --format json")
    if stdout.strip():
        data = json.loads(stdout)
        return data[0]
    return None

def auto_favorite_high_quality():
    """Automatically favorite high-quality wallpapers."""
    wallpaper = get_latest_wallpaper()
    if wallpaper and wallpaper.get('file_size_mb', 0) > 2.0:  # Larger than 2MB
        run_darkwall_command(f"darkwall gallery favorite {wallpaper['timestamp']}")

def main():
    # Generate wallpaper
    run_darkwall_command("darkwall generate")
    
    # Auto-favorite if high quality
    auto_favorite_high_quality()
    
    # Cleanup if needed
    run_darkwall_command("darkwall gallery cleanup")

if __name__ == "__main__":
    main()
```

## Advanced Configurations

### Environment-Specific Configs

Different configs for different environments:

```bash
# Development environment
export DARKWALL_COMFYUI_BASE_URL="http://localhost:8188"
export DARKWALL_LOGGING_LEVEL="DEBUG"
export DARKWALL_HISTORY_ENABLED="false"

# Production environment
export DARKWALL_COMFYUI_BASE_URL="https://comfyui.production.com"
export DARKWALL_HISTORY_ENABLED="true"
export DARKWALL_HISTORY_MAX_ENTRIES="2000"
```

### Conditional Generation

Script for conditional wallpaper generation:

```bash
#!/bin/bash
# conditional_wallpaper.sh

HOUR=$(date +%H)

case $HOUR in
    6-11)
        # Morning: bright, energetic themes
        darkwall generate --template morning.prompt
        ;;
    12-17)
        # Afternoon: nature, outdoor themes
        darkwall generate --template nature.prompt
        ;;
    18-23)
        # Evening: dark, cinematic themes
        darkwall generate --template cinematic.prompt
        ;;
    *)
        # Night: minimal, abstract themes
        darkwall generate --template minimal.prompt
        ;;
esac
```

### Multi-User Setup

Shared system configuration with user overrides:

```toml
# /etc/darkwall-comfyui/config.toml (system-wide)
[comfyui]
base_url = "https://comfyui.company.com"

[monitors]
command = "swaybg"

[history]
history_dir = "/shared/wallpapers/history"
```

```bash
# User-specific override
export DARKWALL_MONITORS_COUNT="2"
export DARKWALL_HISTORY_ENABLED="true"
```

### Performance Optimization

Optimize for performance:

```toml
[comfyui]
timeout = 600          # Longer timeout for complex workflows
poll_interval = 10     # Less frequent polling

[history]
max_entries = 500      # Smaller history for faster operations

[history.cleanup_policy]
max_count = 300        # Aggressive cleanup
max_days = 30
max_size_mb = 2000
```

Batch generation script:
```bash
#!/bin/bash
# Generate multiple wallpapers in batch

for i in {1..5}; do
    darkwall generate --template batch_$i.prompt &
done

wait  # Wait for all to complete
echo "Batch generation complete"
```

## Troubleshooting Examples

### Debug Generation Issues

Debug workflow problems:
```bash
# Enable verbose logging
darkwall --verbose generate

# Test with dry run
darkwall --dry-run generate --workflow problematic.json

# Check ComfyUI connection
curl -v $DARKWALL_COMFYUI_BASE_URL/system_stats

# Validate workflow
darkwall --dry-run generate-all | grep "Warning"
```

### Recover from Failures

Recovery procedures:
```bash
# Fix permissions
darkwall fix-permissions

# Reset state if stuck
darkwall reset

# Clear corrupted history
rm ~/Pictures/wallpapers/history/index.json
darkwall gallery stats  # Will rebuild index

# Reinitialize config
mv ~/.config/darkwall-comfyui/config.toml ~/.config/darkwall-comfyui/config.toml.backup
darkwall init
```

### Monitor Configuration Issues

Debug monitor setup:
```bash
# Check monitor detection
darkwall status

# Test individual monitor
darkwall --dry-run generate  # Shows which monitor would be updated

# Test wallpaper setter manually
swaybg --output DP-1 --image test.png --mode fill &

# Verify monitor patterns
ls -la ~/Pictures/wallpapers/
```

These examples cover the most common use cases and workflows for DarkWall ComfyUI, from basic usage to advanced automation and troubleshooting.
