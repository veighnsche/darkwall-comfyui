# DarkWall ComfyUI - Project Alignment Questionnaire

> **Purpose**: Ensure we're aligned on all project requirements before continuing.
> Please answer each question or mark as N/A if not applicable.

---

## 1. ComfyUI Setup

### 1.1 ComfyUI Instance
- [ ] **Where is your ComfyUI running?**
  - URL: `_________________________________` (I assumed `https://comfyui.home.arpa`)
  - Is it local, remote, or containerized?
  - Does it require authentication? If so, what type?

### 1.2 Workflow
- [ ] **Do you have an existing ComfyUI workflow?**
  - If yes, where is it located?
  - What model/checkpoint does it use?
  - What resolution does it output? (I assumed 16:9 wallpaper aspect ratio)
  - Does it have specific nodes for prompt injection? (I assumed `CLIPTextEncode` with `text` field)

### 1.3 Generation Settings
- [ ] **What generation parameters do you need?**
  - Timeout for generation: `____` seconds (I assumed 300)
  - Poll interval: `____` seconds (I assumed 2)
  - Any specific sampler/scheduler preferences?

---

## 2. Multi-Monitor Setup

### 2.1 Monitor Configuration
- [ ] **How many monitors do you have?** `____` (I assumed 2-3)
- [ ] **What are their resolutions?**
  - Monitor 0: `____x____`
  - Monitor 1: `____x____`
  - Monitor 2: `____x____`
- [ ] **Do monitors need different wallpaper resolutions/aspect ratios?**

### 2.2 Monitor Naming
- [ ] **How does your system identify monitors?**
  - By index (0, 1, 2)?
  - By name (DP-1, HDMI-A-1, eDP-1)?
  - By custom names?

### 2.3 Rotation Behavior
- [ ] **How should rotation work?**
  - Generate for one monitor per invocation, cycling through? (current assumption)
  - Generate for all monitors at once?
  - Generate for specific monitor only?
- [ ] **Should each monitor have a different prompt/style?**

---

## 3. Desktop Environment & Wallpaper Setting

### 3.1 Desktop Environment
- [ ] **What desktop environment/compositor are you using?**
  - [ ] niri (Wayland)
  - [ ] Hyprland (Wayland)
  - [ ] Sway (Wayland)
  - [ ] GNOME (Wayland/X11)
  - [ ] KDE Plasma (Wayland/X11)
  - [ ] Other: `_________________________________`

### 3.2 Wallpaper Tool
- [ ] **What tool do you use to set wallpapers?**
  - [ ] swww (I assumed this based on your niri setup)
  - [ ] swaybg
  - [ ] hyprpaper
  - [ ] feh
  - [ ] nitrogen
  - [ ] Custom command: `_________________________________`

### 3.3 Wallpaper Command Details
- [ ] **What is the exact command to set a wallpaper?**
  - Example: `swww img /path/to/image.png --outputs DP-1`
  - Your command: `_________________________________`
- [ ] **Does it need monitor-specific arguments?**

---

## 4. File Paths & Storage

### 4.1 Output Location
- [ ] **Where should wallpapers be saved?**
  - Directory: `_________________________________` (I assumed `~/Pictures/wallpapers/`)
  - Filename pattern: `_________________________________` (I assumed `monitor_{index}.png`)

### 4.2 Backup Preferences
- [ ] **Do you want backups of previous wallpapers?**
  - [ ] Yes, keep backups
  - [ ] No, just overwrite
- [ ] **If yes, how many backups to keep?** `____`
- [ ] **Backup location?** `_________________________________`

### 4.3 Config Location
- [ ] **Where should config files live?**
  - [ ] `~/.config/darkwall-comfyui/` (current assumption)
  - [ ] Managed by NixOS/home-manager
  - [ ] Other: `_________________________________`

---

## 5. NixOS Integration

### 5.1 System Configuration
- [ ] **How do you manage your NixOS config?**
  - [ ] Flakes
  - [ ] Classic (channels)
  - [ ] home-manager standalone
  - [ ] home-manager as NixOS module

### 5.2 Systemd Integration
- [ ] **Where should systemd units be defined?**
  - [ ] In NixOS configuration (system-wide)
  - [ ] In home-manager (user-level)
  - [ ] Standalone files (current approach)
- [ ] **Should the service run as root or user?**

### 5.3 Package Installation
- [ ] **How should the package be installed?**
  - [ ] As a flake input to your NixOS config
  - [ ] Via overlay
  - [ ] Standalone `nix run`
  - [ ] Other: `_________________________________`

---

## 6. Scheduling & Automation

### 6.1 Generation Frequency
- [ ] **How often should wallpapers rotate?**
  - [ ] Every `____` minutes
  - [ ] Every `____` hours (I assumed hourly)
  - [ ] At specific times: `_________________________________`
  - [ ] On-demand only (no automatic rotation)

### 6.2 Trigger Conditions
- [ ] **Should generation happen on specific events?**
  - [ ] On login/session start
  - [ ] On wake from suspend
  - [ ] On monitor connect/disconnect
  - [ ] Only on timer

### 6.3 Failure Handling
- [ ] **What should happen if ComfyUI is unavailable?**
  - [ ] Retry with backoff
  - [ ] Skip and try next scheduled time
  - [ ] Send notification
  - [ ] Keep current wallpaper (silent fail)

---

## 7. Prompt Generation

### 7.1 Prompt Style
- [ ] **What kind of wallpapers do you want?**
  - [ ] Abstract/artistic
  - [ ] Nature/landscapes
  - [ ] Sci-fi/futuristic
  - [ ] Minimalist
  - [ ] Other: `_________________________________`

### 7.2 Dark Mode Requirements
- [ ] **How dark should wallpapers be?**
  - [ ] Very dark (OLED-friendly, mostly black)
  - [ ] Dark with some color
  - [ ] Moody/atmospheric
  - [ ] No specific darkness requirement

### 7.3 Prompt Customization
- [ ] **Do you want to customize the prompt atoms?**
  - [ ] Yes, I'll edit the atom files
  - [ ] No, use sensible defaults
- [ ] **Any specific themes/subjects to include or exclude?**

### 7.4 Determinism
- [ ] **How should prompt variation work?**
  - [ ] Time-based (same prompt for same time slot) - current assumption
  - [ ] Random each time
  - [ ] Sequential through a list
  - [ ] Other: `_________________________________`

---

## 8. Logging & Debugging

### 8.1 Log Level
- [ ] **What log level do you prefer?**
  - [ ] DEBUG (verbose)
  - [ ] INFO (normal) - current assumption
  - [ ] WARNING (quiet)
  - [ ] ERROR (minimal)

### 8.2 Log Location
- [ ] **Where should logs go?**
  - [ ] journald (systemd default)
  - [ ] File: `_________________________________`
  - [ ] stdout only

### 8.3 Notifications
- [ ] **Do you want desktop notifications?**
  - [ ] On success
  - [ ] On failure only
  - [ ] Never

---

## 9. Current Assumptions I Made (Please Verify)

### 9.1 Technical Assumptions
- [ ] ✅/❌ ComfyUI is at `https://comfyui.home.arpa`
- [ ] ✅/❌ You're using niri as your Wayland compositor
- [ ] ✅/❌ swww is your wallpaper setter
- [ ] ✅/❌ You have 2-3 monitors
- [ ] ✅/❌ Wallpapers should be 16:9 aspect ratio
- [ ] ✅/❌ PNG format is preferred

### 9.2 Behavioral Assumptions
- [ ] ✅/❌ Rotate through monitors one at a time
- [ ] ✅/❌ Keep backups of previous wallpapers
- [ ] ✅/❌ Time-based deterministic prompts (same time = same prompt)
- [ ] ✅/❌ Hourly rotation schedule
- [ ] ✅/❌ Dark mode friendly wallpapers

### 9.3 Integration Assumptions
- [ ] ✅/❌ User-level systemd service (not system-wide)
- [ ] ✅/❌ Config in `~/.config/darkwall-comfyui/`
- [ ] ✅/❌ home-manager for NixOS integration

---

## 10. Missing Features / Nice-to-Haves

### 10.1 Features You Want
- [ ] **What features are essential?**
  - [ ] Multi-monitor support
  - [ ] Automatic rotation
  - [ ] Backup system
  - [ ] Dry-run mode
  - [ ] Config validation
  - [ ] Other: `_________________________________`

### 10.2 Features You DON'T Want
- [ ] **Anything I should NOT implement?**
  - `_________________________________`

### 10.3 Future Considerations
- [ ] **Any future features to keep in mind?**
  - [ ] Web UI for configuration
  - [ ] Multiple themes/presets
  - [ ] Integration with other image generators
  - [ ] Other: `_________________________________`

---

## 11. Priority & Timeline

### 11.1 What's Most Important Right Now?
1. `_________________________________`
2. `_________________________________`
3. `_________________________________`

### 11.2 What Can Wait?
- `_________________________________`

### 11.3 Any Deadlines?
- `_________________________________`

---

## Notes / Additional Context

Please add any additional context, requirements, or preferences not covered above:

```
_________________________________
_________________________________
_________________________________
_________________________________
```

---

**After completing this questionnaire, I will:**
1. Update the TODO.md with accurate requirements
2. Fix any incorrect assumptions in the code
3. Prioritize work based on your actual needs
4. Create proper NixOS/home-manager integration
