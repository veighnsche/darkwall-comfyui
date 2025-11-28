# Troubleshooting Guide

This guide covers common issues and solutions when using DarkWall ComfyUI.

## Table of Contents

- [ComfyUI Connection Issues](#comfyui-connection-issues)
- [Permission Problems](#permission-problems)
- [Wallpaper Setting Issues](#wallpaper-setting-issues)
- [Configuration Problems](#configuration-problems)
- [Performance Issues](#performance-issues)
- [History and Gallery Issues](#history-and-gallery-issues)

## ComfyUI Connection Issues

### ComfyUI not reachable

**Symptoms:**
```
ERROR: ComfyUI not reachable at https://comfyui.home.arpa
```

**Solutions:**

1. **Check ComfyUI is running**
   ```bash
   curl -f https://comfyui.home.arpa/system_stats
   ```

2. **Verify URL in config**
   ```bash
   darkwall status
   # Check the ComfyUI URL shown
   ```

3. **Update configuration**
   ```toml
   [comfyui]
   base_url = "http://localhost:8188"  # or your ComfyUI URL
   ```

4. **Check network connectivity**
   ```bash
   ping comfyui.home.arpa
   # or test with specific IP
   ping 192.168.1.100
   ```

### Generation timeout

**Symptoms:**
```
ERROR: Generation timed out after 300s
```

**Solutions:**

1. **Increase timeout in config**
   ```toml
   [comfyui]
   timeout = 600  # 10 minutes
   ```

2. **Check ComfyUI queue**
   - Open ComfyUI web interface
   - Check if other jobs are running
   - Clear queue if necessary

3. **Reduce workflow complexity**
   - Use simpler models
   - Reduce resolution
   - Disable unnecessary steps

### Invalid workflow

**Symptoms:**
```
WARNING: Workflow: No prompt field found in workflow
ERROR: Invalid workflow submitted to ComfyUI
```

**Solutions:**

1. **Validate workflow structure**
   ```bash
   darkwall generate --dry-run
   # Look for workflow validation warnings
   ```

2. **Check workflow file exists**
   ```bash
   ls ~/.config/darkwall-comfyui/workflows/
   ```

3. **Use default workflow**
   ```bash
   darkwall generate --workflow workflow.json
   ```

## Permission Problems

### Config directory read-only

**Symptoms:**
```
ERROR: Output directory is not writable
ERROR: Failed to create wallpaper file
```

**Solutions:**

1. **Fix permissions automatically**
   ```bash
   darkwall fix-permissions
   ```

2. **Manual permission fix**
   ```bash
   chmod -R u+w ~/.config/darkwall-comfyui/
   ```

3. **Check ownership**
   ```bash
   ls -la ~/.config/darkwall-comfyui/
   # Should be owned by your user
   ```

### History directory not writable

**Symptoms:**
```
ERROR: History directory is not writable: ~/Pictures/wallpapers/history
```

**Solutions:**

1. **Create directory with proper permissions**
   ```bash
   mkdir -p ~/Pictures/wallpapers/history
   chmod u+w ~/Pictures/wallpapers/history
   ```

2. **Check parent directory permissions**
   ```bash
   ls -la ~/Pictures/
   ```

3. **Use alternative history directory**
   ```toml
   [history]
   history_dir = "~/.local/share/darkwall-comfyui/history"
   ```

## Wallpaper Setting Issues

### swaybg conflicts

**Symptoms:**
```
WARNING: Failed to set wallpaper (image saved successfully)
```

**Solutions:**

1. **Kill existing swaybg processes**
   ```bash
   pkill -f swaybg
   darkwall generate
   ```

2. **Check swaybg is installed**
   ```bash
   which swaybg
   # Should show path to swaybg
   ```

3. **Verify monitor configuration**
   ```bash
   darkwall status
   # Check monitor count and outputs
   ```

### swww not working

**Symptoms:**
```
ERROR: swww command failed
```

**Solutions:**

1. **Start swww daemon**
   ```bash
   swww-daemon &
   darkwall generate
   ```

2. **Check swww installation**
   ```bash
   which swww
   swww --help
   ```

3. **Verify display environment**
   ```bash
   echo $WAYLAND_DISPLAY
   echo $DISPLAY
   ```

### Custom command fails

**Symptoms:**
```
ERROR: Custom command failed with exit code 1
```

**Solutions:**

1. **Test command manually**
   ```bash
   # Replace {path} and {index} with actual values
   your-command --image /path/to/wallpaper.png --monitor 0
   ```

2. **Check command syntax in config**
   ```toml
   [monitors]
   command = "custom:your-command --image {path} --monitor {index}"
   ```

3. **Use absolute paths**
   ```toml
   command = "custom:/usr/bin/your-command --image {path}"
   ```

## Configuration Problems

### Invalid TOML syntax

**Symptoms:**
```
ERROR: Failed to parse config file: Invalid TOML
```

**Solutions:**

1. **Validate TOML syntax**
   ```bash
   # Install toml-cli or use online validator
   python -c "import tomli; tomli.load(open('~/.config/darkwall-comfyui/config.toml'))"
   ```

2. **Check common syntax errors**
   - Missing quotes around string values
   - Invalid characters in keys
   - Mismatched brackets/quotes

3. **Reset to default config**
   ```bash
   mv ~/.config/darkwall-comfyui/config.toml ~/.config/darkwall-comfyui/config.toml.backup
   darkwall init
   ```

### Unknown configuration sections

**Symptoms:**
```
ERROR: Unknown config section 'invalid_section' in config.toml
```

**Solutions:**

1. **Check valid sections** in the man page or configuration reference

2. **Remove or rename invalid sections**

3. **Use validate command**
   ```bash
   darkwall validate
   ```

### Environment variable overrides not working

**Symptoms:**
Environment variables not affecting configuration

**Solutions:**

1. **Use correct variable format**
   ```bash
   export DARKWALL_COMFYUI_BASE_URL="http://localhost:8188"
   export DARKWALL_MONITORS_COUNT="2"
   ```

2. **Check variable names**
   - Sections become uppercase: `[comfyui]` → `DARKWALL_COMFYUI_`
   - Keys become uppercase: `base_url` → `BASE_URL`
   - Nested sections use double underscores

3. **Verify with status command**
   ```bash
   darkwall status
   # Shows effective configuration after env var overrides
   ```

## Performance Issues

### Slow generation

**Symptoms:**
Generation taking longer than expected

**Solutions:**

1. **Optimize workflow**
   - Use faster models
   - Reduce image dimensions
   - Decrease steps/denoising

2. **Check ComfyUI performance**
   - Monitor GPU usage
   - Check VRAM availability
   - Optimize batch size

3. **Adjust timeouts**
   ```toml
   [comfyui]
   timeout = 900  # 15 minutes for complex workflows
   ```

### High disk usage

**Symptoms:**
History directory growing too large

**Solutions:**

1. **Run cleanup**
   ```bash
   darkwall gallery cleanup
   ```

2. **Configure cleanup policy**
   ```toml
   [history.cleanup_policy]
   max_count = 500
   max_days = 90
   max_size_mb = 5000
   ```

3. **Manual cleanup**
   ```bash
   # Delete old wallpapers manually
   find ~/Pictures/wallpapers/history -name "*.png" -mtime +30 -delete
   ```

## History and Gallery Issues

### History not saving

**Symptoms:**
Generated wallpapers not appearing in history

**Solutions:**

1. **Check history is enabled**
   ```toml
   [history]
   enabled = true
   ```

2. **Verify history directory permissions**
   ```bash
   ls -la ~/Pictures/wallpapers/history/
   ```

3. **Check disk space**
   ```bash
   df -h ~/Pictures/
   ```

### Gallery command not found

**Symptoms:**
```
ERROR: Invalid command: gallery
```

**Solutions:**

1. **Update to latest version**
   ```bash
   # If using Nix
   nix flake update
   nix build .#darkwall-comfyui
   ```

2. **Check installation**
   ```bash
   darkwall --help
   # Should show gallery in command list
   ```

### Corrupted history index

**Symptoms:**
```
WARNING: Invalid history index file, starting fresh
```

**Solutions:**

1. **History will automatically recover**
   - Old index is backed up
   - New index created from existing files

2. **Manual recovery**
   ```bash
   # Back up current index
   mv ~/Pictures/wallpapers/history/index.json ~/Pictures/wallpapers/history/index.json.backup
   
   # DarkWall will rebuild index automatically
   darkwall gallery stats
   ```

## Getting Help

### Enable debug logging

```bash
darkwall --verbose generate
# or
DARKWALL_LOGGING_LEVEL=DEBUG darkwall generate
```

### Check system status

```bash
darkwall status
# Shows comprehensive system information
```

### Report issues

When reporting bugs, include:

1. **Configuration** (sanitized):
   ```bash
   darkwall status > debug-info.txt
   ```

2. **Logs**:
   ```bash
   darkwall --verbose generate 2>&1 > generation.log
   ```

3. **System info**:
   ```bash
   uname -a
   python --version
   which swaybg swww feh nitrogen
   ```

### Common debug commands

```bash
# Test ComfyUI connection
curl -v https://comfyui.home.arpa/system_stats

# Check configuration
darkwall validate

# Test wallpaper setter
swaybg --output eDP-1 --image ~/Pictures/wallpapers/monitor_0.png &

# Check history
darkwall gallery stats

# Test prompt generation
darkwall prompt preview --verbose
```

## Advanced Troubleshooting

### Manual wallpaper setting

If automatic wallpaper setting fails, set manually:

```bash
# swaybg
swaybg --output DP-1 --image ~/Pictures/wallpapers/monitor_0.png --mode fill &
swaybg --output DP-2 --image ~/Pictures/wallpapers/monitor_1.png --mode fill &

# swww
swww img ~/Pictures/wallpapers/monitor_0.png --outputs DP-1
swww img ~/Pictures/wallpapers/monitor_1.png --outputs DP-2

# feh
feh --bg-fill ~/Pictures/wallpapers/monitor_0.png ~/Pictures/wallpapers/monitor_1.png

# nitrogen
nitrogen --set-scaled --output DP-1 ~/Pictures/wallpapers/monitor_0.png
nitrogen --set-scaled --output DP-2 ~/Pictures/wallpapers/monitor_1.png
```

### Configuration reset

```bash
# Backup current config
cp ~/.config/darkwall-comfyui/config.toml ~/.config/darkwall-comfyui/config.toml.backup

# Reset to defaults
rm -rf ~/.config/darkwall-comfyui/
darkwall init

# Restore customizations selectively
# Edit config.toml manually
```

### State file issues

```bash
# Reset rotation state
darkwall reset

# Or delete state file manually
rm ~/.config/darkwall-comfyui/state.json
```
