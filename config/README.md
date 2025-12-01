# DarkWall ComfyUI - Configuration & Theme Guide

This guide covers:
1. **Configuration Setup** — How to configure `config.toml`
2. **Theme Creation** — How to create themes with atoms and prompts

---

# Part 1: Configuration Setup

The main configuration file is `~/.config/darkwall-comfyui/config.toml`.

## Minimal Configuration

```toml
[comfyui]
base_url = "http://localhost:8188"

[monitors.DP-1]
resolution = "1920x1080"
output = "~/Pictures/wallpapers/monitor_DP-1.png"

[themes.dark]
workflow_prefix = "my-workflow"
default_template = "default.prompt"
```

This requires:
- A ComfyUI server running at the specified URL
- A workflow file at `~/.config/darkwall-comfyui/workflows/my-workflow-1920x1080.json`
- A theme directory at `~/.config/darkwall-comfyui/themes/dark/`

---

## Configuration Sections

### [comfyui] — Server Connection

```toml
[comfyui]
base_url = "http://192.168.178.29:8188"  # ComfyUI server URL
timeout = 300                             # Request timeout in seconds
poll_interval = 5                         # Status polling interval
```

| Key | Default | Description |
|-----|---------|-------------|
| `base_url` | `http://localhost:8188` | ComfyUI API endpoint |
| `timeout` | `300` | Max seconds to wait for generation |
| `poll_interval` | `5` | Seconds between status checks |

---

### [monitors.*] — Per-Monitor Setup

Each monitor uses its **compositor output name** (e.g., `DP-1`, `HDMI-A-1`).

```toml
[monitors.DP-1]
resolution = "2560x1440"
output = "~/Pictures/wallpapers/monitor_DP-1.png"
command = "swaybg"

[monitors.HDMI-A-1]
resolution = "1920x1080"
output = "~/Pictures/wallpapers/monitor_HDMI-A-1.png"
command = "swaybg"
```

| Key | Required | Description |
|-----|----------|-------------|
| `resolution` | Yes | Used to select workflow: `{theme.workflow_prefix}-{resolution}.json` |
| `output` | Yes | Where to save the generated wallpaper |
| `command` | No | Wallpaper setter (`swaybg`, `swww`, etc.) |
| `templates` | No | Restrict to specific prompt templates |

**Finding monitor names:**
```bash
# Wayland (wlr-randr)
wlr-randr | grep -E "^[A-Z]"

# Hyprland
hyprctl monitors | grep Monitor

# Sway
swaymsg -t get_outputs | jq '.[].name'
```

---

### [themes.*] — Theme Definitions

Each theme maps to a workflow and prompt templates.

```toml
[themes.dark]
workflow_prefix = "z-image-turbo"
default_template = "default.prompt"

[themes.light]
workflow_prefix = "wan2_5"
default_template = "default.prompt"

[themes.anime]
workflow_prefix = "uncannyvalley"
default_template = "default.prompt"
```

| Key | Required | Description |
|-----|----------|-------------|
| `workflow_prefix` | Yes | Workflow filename prefix (without resolution) |
| `default_template` | No | Default prompt template to use |

**Workflow resolution:** Theme + monitor resolution determines workflow file:
- Theme `dark` with `workflow_prefix = "z-image-turbo"`
- Monitor with `resolution = "1920x1080"`
- Uses workflow: `workflows/z-image-turbo-1920x1080.json`

---

### [workflows.*] — Workflow Definitions

Optional: restrict which prompts a workflow can use.

```toml
[workflows.z-image-turbo-1920x1080]
prompts = ["*"]  # All prompts allowed

[workflows.special-workflow-1920x1080]
prompts = ["cinematic", "noir"]  # Only these templates
```

---

### [schedule] — Solar-Based Theme Scheduling

Automatically switch themes based on sunrise/sunset.

```toml
[schedule]
latitude = 52.3676
longitude = 4.9041
timezone = "Europe/Amsterdam"

# Day themes (after sunrise)
day_themes = [
    { name = "light", weight = 1.0 }
]

# Night themes (after sunset)
night_themes = [
    { name = "dark", weight = 0.7 },
    { name = "anime", weight = 0.3 }
]

# Transition duration
blend_duration_minutes = 30
```

| Key | Required | Description |
|-----|----------|-------------|
| `latitude` | Yes | Location latitude for solar calculation |
| `longitude` | Yes | Location longitude |
| `timezone` | Yes | IANA timezone (e.g., `Europe/Amsterdam`) |
| `day_themes` | Yes | Themes used during daytime (weighted list) |
| `night_themes` | Yes | Themes used during nighttime (weighted list) |
| `blend_duration_minutes` | No | Transition period around sunrise/sunset |

**Manual time override:**
```toml
[schedule]
# ... location settings ...
sunrise_time = "07:00"  # Override calculated sunrise
sunset_time = "19:00"   # Override calculated sunset
```

---

### [prompt] — Prompt Generation Settings

```toml
[prompt]
time_slot_minutes = 30   # How often to generate new prompts
use_monitor_seed = true  # Different seed per monitor
```

| Key | Default | Description |
|-----|---------|-------------|
| `time_slot_minutes` | `30` | Minutes between prompt regeneration |
| `use_monitor_seed` | `true` | Each monitor gets unique prompts |

---

### [logging] — Log Settings

```toml
[logging]
level = "INFO"    # DEBUG, INFO, WARNING, ERROR
verbose = false
```

---

### [notifications] — Desktop Notifications

```toml
[notifications]
enabled = true
show_preview = true
timeout_ms = 5000
urgency = "normal"  # low, normal, critical
```

---

### [history] — Wallpaper History

```toml
[history]
enabled = true
max_entries = 500
history_dir = "~/Pictures/wallpapers/history"

[history.cleanup_policy]
max_days = 90
max_size_mb = 5000
```

---

## Complete Example

```toml
# DarkWall ComfyUI Configuration

[comfyui]
base_url = "http://192.168.178.29:8188"
timeout = 300
poll_interval = 5

# Monitors
[monitors.DP-1]
resolution = "2560x1440"
output = "~/Pictures/wallpapers/monitor_DP-1.png"
command = "swaybg"

[monitors.HDMI-A-1]
resolution = "1920x1080"
output = "~/Pictures/wallpapers/monitor_HDMI-A-1.png"
command = "swaybg"

# Themes
[themes.light]
workflow_prefix = "wan2_5"
default_template = "default.prompt"

[themes.dark]
workflow_prefix = "z-image-turbo"
default_template = "default.prompt"

# Schedule
[schedule]
latitude = 52.3676
longitude = 4.9041
timezone = "Europe/Amsterdam"
day_themes = [{ name = "light", weight = 1.0 }]
night_themes = [{ name = "dark", weight = 1.0 }]
blend_duration_minutes = 30

[prompt]
time_slot_minutes = 30

[logging]
level = "INFO"

[notifications]
enabled = true

[history]
enabled = true
max_entries = 500
```

---

## Environment Variable Overrides

Override any config value with environment variables:

```bash
export DARKWALL_COMFYUI_BASE_URL="http://localhost:8188"
export DARKWALL_COMFYUI_TIMEOUT="600"
export DARKWALL_HISTORY_ENABLED="false"
```

Pattern: `DARKWALL_[SECTION]_[KEY]` (uppercase, underscores).

---

# Part 2: Theme Creation

> **For LLM Theme Creators**: This section defines the **fixed structure** that themes must follow. Content examples are suggestions only—you define your theme's aesthetic, atom categories, and prompt content.

---

## Wallpaper Concept: Subject-Based Composition

DarkWall generates **subject-based wallpapers** with a two-layer composition:

1. **Environment** (background): The scene, setting, atmosphere, lighting
2. **Subject** (foreground): A character, figure, or focal element positioned on the right side

This design works with tiling window managers (like Niri) where windows occupy the left portion of the screen, leaving the subject visible on the right.

**All prompt templates MUST define both `$$environment$$` and `$$subject$$` sections.**

---

## Theme Directory Structure (REQUIRED)

Every theme lives under `~/.config/darkwall-comfyui/themes/<theme_name>/`:

```
themes/<your_theme_name>/
├── atoms/           # REQUIRED: Atom files for random substitution
│   └── *.txt        # One atom per line, filename = atom name
└── prompts/         # REQUIRED: Complete prompt templates
    └── *.prompt     # Prompt files with placeholders
```

### Atoms Directory
- Each `.txt` file in `atoms/` becomes a substitutable atom
- Filename (without extension) = atom name used in prompts
- One option per line (blank lines and `#` comments ignored)

### Prompts Directory  
- Each `.prompt` file is a complete generation template
- System randomly selects from available prompts
- Prompts use atoms via `__atomname__` syntax

---

## Atom Files (atoms/*.txt)

**Format**: One option per line. Blank lines ignored. `#` comments optional.

**Naming**: The filename determines the placeholder name:
- `subject.txt` → use as `__subject__` in prompts
- `lighting.txt` → use as `__lighting__` in prompts
- `my_custom_category.txt` → use as `__my_custom_category__` in prompts

**You define what atoms your theme needs.** Common patterns:

| Atom | Purpose | Required? |
|------|---------|----------|
| `subject.txt` | Main subject/character/figure | **Yes** |
| `environment.txt` | Location/setting/scene | **Yes** |
| `lighting.txt` | Lighting conditions | Recommended |
| `style.txt` | Artistic style | Recommended |
| `mood.txt` | Mood/atmosphere | Optional |
| `colors.txt` | Color palette | Optional |
| `composition.txt` | Composition style | Optional |

**Example atom file** (`atoms/lighting.txt`):
```
dramatic side lighting with deep shadows
soft golden hour glow through window
harsh fluorescent overhead
neon signs reflecting off wet surfaces
```

---

## Prompt Files (prompts/*.prompt)

Prompt files define the **environment** and **subject** sections that make up each wallpaper.

### Required Sections

Every prompt template **MUST** include these four sections:

| Section | Purpose |
|---------|----------|
| `$$environment$$` | Background scene, setting, atmosphere, lighting |
| `$$environment:negative$$` | What to avoid in the environment |
| `$$subject$$` | Foreground character/figure, positioned on right side |
| `$$subject:negative$$` | What to avoid in the subject |

### Section Syntax

Sections are marked with `$$name$$` on their own line:

```
$$environment$$
background content here

$$environment:negative$$
negative content for background

$$subject$$
subject content here (should include "positioned on right side of frame")

$$subject:negative$$
negative content for subject
```

### Placeholder Syntax

| Syntax | Meaning |
|--------|---------|
| `__name__` | Random from `atoms/name.txt` |
| `{a\|b}` | Random from inline list |
| `{0.5::a\|2::b}` | Weighted random |
| `$$environment$$` | Start environment (background) section |
| `$$subject$$` | Start subject (foreground) section |
| `$$section:negative$$` | Start negative for section |
| `# comment` | Ignored line |

### Example Prompt File

```
# Dark Theme - Cinematic Scene
# Environment fills the background, subject on right side of frame

$$environment$$
__environment__, __lighting__, __style__, __mood__, __colors__,
cinematic __composition__, dark mode wallpaper, moody atmosphere,
detailed background, atmospheric depth, high quality

$$environment:negative$$
bright, sunny, daylight, cheerful, happy, colorful rainbow, oversaturated,
low quality, blurry, watermark, signature, text, logo, banner

$$subject$$
__subject__, positioned on right side of frame,
dramatic silhouette, mysterious presence, __mood__,
detailed, cinematic lighting, high quality

$$subject:negative$$
cropped, out of frame, ugly, duplicate, poorly drawn,
bad anatomy, deformed, mutated, extra limbs
```

**Key points:**
- Environment describes the scene/background
- Subject includes "positioned on right side of frame" for proper composition
- Each section has its own negative prompt for targeted quality control

When resolved, each `__placeholder__` gets replaced with a random line from the corresponding atom file.

### Naming Prompts

Prompt filenames are arbitrary. Suggested patterns:
- Descriptive: `cinematic.prompt`, `cyberpunk.prompt`, `noir.prompt`
- Default: `default.prompt` (used when no specific template requested)

---

## How Generation Works

1. System picks a random `.prompt` file from your theme's `prompts/` directory
2. Parses the template into named sections (`$$environment$$`, `$$subject$$`, etc.)
3. For each `__atomname__` placeholder, picks a random line from `atoms/atomname.txt`
4. For each `{variant|syntax}`, picks a random option
5. Resolves all placeholders deterministically based on time-slot seed
6. Returns all sections for workflow injection

**Determinism**: Same time slot + same monitor = same prompt (until atoms/prompts change).

---

## Creating a New Theme

### 1. Create Theme Directory
```bash
mkdir -p ~/.config/darkwall-comfyui/themes/<your_theme>/atoms
mkdir -p ~/.config/darkwall-comfyui/themes/<your_theme>/prompts
```

### 2. Define Your Atoms
Create `.txt` files in `atoms/` for each category your theme needs:

```bash
# Example: Create environment atoms
cat > atoms/environment.txt << 'EOF'
abandoned industrial warehouse
neon-lit cyberpunk alley
misty forest at twilight
EOF
```

### 3. Create Prompt Templates
Create `.prompt` files using your atoms:

```bash
cat > prompts/default.prompt << 'EOF'
# Your Theme - Default Prompt

$$environment$$
__environment__, __lighting__, __style__,
cinematic composition, high quality

$$environment:negative$$
low quality, blurry, watermark, text

$$subject$$
__subject__, positioned on right side of frame,
detailed, cinematic lighting

$$subject:negative$$
bad anatomy, deformed, extra limbs
EOF
```

### 4. Register in config.toml
```toml
[themes.your_theme]
workflow_prefix = "your-workflow"
default_template = "default.prompt"
```

### 5. Test
```bash
darkwall prompt generate --theme your_theme
darkwall prompt interactive  # Interactive mode with theme selection
```

---

## Design Guidelines (Suggestions)

These are recommendations, not requirements:

### Atom Guidelines
- **Consistent length**: Keep atoms in a file similar in complexity
- **Self-contained**: Each atom should work independently
- **Theme-coherent**: All atoms should fit your theme's aesthetic
- **Variety**: More atoms = more variation in outputs

### Prompt Guidelines
- **Quality tags**: Include quality boosters in each section
- **Negative prompts**: Always include common artifacts to avoid per section
- **Balance specificity**: Too vague = generic; too specific = repetitive
- **Subject positioning**: Always include "positioned on right side of frame" in subject section
- **Environment focus**: Environment should describe the full scene/atmosphere

### Practical Tips
- Start with 20-50 atoms per category
- Create 5-10 prompt templates for variety
- Test combinations with `darkwall prompt generate`
- Use `{weighted|options}` for rare variations

---

## Reference: Existing Theme Structure

Example from the `dark` theme:

```
themes/dark/
├── atoms/
│   ├── colors.txt         # Color palette options
│   ├── composition.txt    # Composition styles
│   ├── environment.txt    # Location/setting options
│   ├── lighting.txt       # Lighting conditions
│   ├── mood.txt           # Mood/atmosphere
│   ├── style.txt          # Artistic styles
│   └── subject.txt        # Subject descriptions
└── prompts/
    ├── default.prompt     # Default multi-section template
    ├── cinematic.prompt   # Cinematic style
    ├── cyberpunk.prompt   # Cyberpunk aesthetic
    ├── gothic.prompt      # Gothic atmosphere
    ├── noir.prompt        # Film noir style
    └── ...
```

**Requirements:**
1. `atoms/` directory with at least `subject.txt` and `environment.txt`
2. `prompts/` directory with at least one `.prompt` file
3. Each prompt MUST have `$$environment$$`, `$$environment:negative$$`, `$$subject$$`, `$$subject:negative$$` sections
4. Subject section should include "positioned on right side of frame" for proper composition

---

## Quick Reference

| Component | Location | Format |
|-----------|----------|--------|
| Theme root | `~/.config/darkwall-comfyui/themes/<name>/` | Directory |
| Atoms | `themes/<name>/atoms/*.txt` | One per line |
| Prompts | `themes/<name>/prompts/*.prompt` | Multi-section with `$$section$$` markers |

| Syntax | Meaning |
|--------|--------|
| `__name__` | Random from `atoms/name.txt` |
| `{a\|b}` | Random from inline list |
| `{0.5::a\|2::b}` | Weighted random |
| `$$environment$$` | Start environment (background) section |
| `$$subject$$` | Start subject (foreground) section |
| `$$section:negative$$` | Start negative for section |
| `# comment` | Ignored line |

---

## CLI Commands

```bash
# Generate a prompt (copy-paste ready)
darkwall prompt generate --theme dark

# Interactive mode with theme/template selection
darkwall prompt interactive

# Preview with metadata
darkwall prompt preview --template cinematic

# List available templates and atoms
darkwall prompt list
darkwall prompt list --atoms --theme dark
```

---

## Workflow Integration

Themes specify which ComfyUI workflow to use:

```toml
[themes.your_theme]
# Single workflow
workflow_prefix = "your-workflow"

# OR weighted multiple workflows
workflows = [
    { prefix = "workflow-a", weight = 0.7 },
    { prefix = "workflow-b", weight = 0.3 }
]
```

Workflow files live in `~/.config/darkwall-comfyui/workflows/` as `<prefix>-<resolution>.json`

Multi-section prompts (environment/subject) are injected into corresponding workflow nodes.