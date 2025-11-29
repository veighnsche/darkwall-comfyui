# DarkWall ComfyUI — Open Questions Questionnaire

> **Purpose**: Track only design questions that need USER answers before implementation.
> **Format**: Answer inline, then I will convert to frozen requirements.
> **Preserved**: User answers from previous questionnaire are included.

---

## How to Answer

For each question:
1. Delete `[ ]` and write your answer inline
2. If a question has multiple options, pick one or specify custom
3. Add notes in the "Additional Context" section if needed

---

# Q-THEME: Theme System

## Q-THEME-001: Per-Monitor Theme Selection

Should each monitor be able to use a different theme independently?

**Options**:
- [ ] **A) Global theme only** — All monitors use the same theme (simpler)
- [ ] **B) Per-monitor theme** — Each monitor can specify its own theme in config
- [ ] **C) Override only** — Global default, but monitors can override

**If B or C, example config**:
```toml
[monitors.0]
theme = "nsfw"  # Override for this monitor

[monitors.1]
# Uses global default theme
```

**Your answer**: _________________________________

---

## Q-THEME-002: Theme Fallback Behavior

When a theme is specified but doesn't exist:

- [ ] **A) Error and exit** — Fail fast
- [ ] **B) Warn and use default** — Log warning, use "default" theme
- [ ] **C) Create empty theme** — Create the theme directory structure

**Your answer**: _________________________________

---

# Q-SCHED: Scheduling

## Q-SCHED-001: Sundown/Sunrise Priority

For automatic NSFW scheduling, which approach do you prefer?

- [ ] **A) Solar calculation** — Calculate based on lat/lon (more accurate)
- [ ] **B) Fixed times** — Manual start/end times (simpler)
- [ ] **C) Both** — Solar by default, times as override

**Note**: Solar requires `astral` dependency.

**Your answer**: _________________________________

---

## Q-SCHED-002: Schedule Granularity

How should theme transitions happen?

- [ ] **A) Next generation** — Theme changes on next wallpaper generation
- [ ] **B) Immediate regeneration** — Trigger regeneration when theme switches
- [ ] **C) Blend period** — Gradual transition over N generations

**Your answer**: _________________________________

---

## Q-SCHED-003: Schedule Status in CLI

What should `darkwall status` show for scheduling?

- [ ] **A) Current theme + next transition time**
- [ ] **B) Full schedule for next 24 hours**
- [ ] **C) Just current theme name**

**Your answer**: _________________________________

---

# Q-WORKFLOW: Workflow Management

## Q-WORKFLOW-001: Workflow-Centric Prompt Pools

*Preserved from previous questionnaire with your notes*

The current config has monitors reference workflows directly. Should we introduce a `[workflows]` table where each workflow declares its eligible prompt templates?

**Current approach**:
```toml
[monitors]
workflows = ["ultrawide.json", "portrait.json"]
templates = ["cinematic.prompt", "minimal.prompt"]
```

**Proposed approach**:
```toml
[workflows.ultrawide]
path = "ultrawide.json"
prompts = ["cinematic.prompt", "cyberpunk.prompt"]

[workflows.portrait]
path = "portrait.json"
prompts = ["minimal.prompt", "nature.prompt"]

[monitors.0]
workflow = "ultrawide"  # Uses that workflow's prompt pool
```

**Benefits**:
- Prompts belong to workflows, not monitors
- Workflow reusable across monitors
- Clear separation of concerns

**Your previous notes**: 
> "THE WORKFLOWS ARE JSON FILES!!! They're one-to-one.. why was that not obvious????"
> "CAN YOU MAKE THEM!?!??"

**Clarification needed**: 
1. Is the workflow ID = filename (e.g., `ultrawide` = `ultrawide.json`)?
2. Or do you want custom IDs that map to files?

**Your answer**: _________________________________

---

## Q-WORKFLOW-002: Template Selection Within Workflow

When a workflow has multiple prompts in its pool, how should they be selected?

- [ ] **A) Pseudo-round-robin** — Cycle through evenly over time
- [ ] **B) Random per generation** — Random choice each time (with seed)
- [ ] **C) Weighted** — Config specifies weights per template
- [ ] **D) Time-based** — Different templates for different times of day

**Your answer**: _________________________________

---

## Q-WORKFLOW-003: Shared Workflow, Shared Template?

If two monitors use the same workflow, should they:

- [ ] **A) Get same template** — Same time slot = same template on both
- [ ] **B) Independent selection** — Each monitor picks independently (different seed offset)

**Your answer**: _________________________________

---

# Q-MONITOR: Monitor Configuration

## Q-MONITOR-001: Monitor Detection

*Preserved from previous questionnaire*

Should the tool auto-detect monitors from the system?

- [ ] **A) Manual count only** — User specifies `monitors.count`
- [ ] **B) Auto-detect** — Query niri/sway/hyprland for monitor list
- [ ] **C) Hybrid** — Auto-detect but allow override

**Your previous note**:
> "PLEASE RUN niri msg outputs... because this is not preference question"

**Clarification**: You want me to detect your actual monitors? If so, which compositor:
- [ ] niri (`niri msg outputs`)
- [ ] sway (`swaymsg -t get_outputs`)
- [ ] hyprland (`hyprctl monitors`)

**Your answer**: _________________________________

---

## Q-MONITOR-002: Monitor Naming

How should monitors be identified?

- [ ] **A) Index only** — `0`, `1`, `2`
- [ ] **B) Name from compositor** — `DP-1`, `HDMI-A-1`
- [ ] **C) Custom names** — User-defined like `ultrawide`, `portrait`

**Your answer**: _________________________________

---

## Q-MONITOR-003: Monitor → Workflow Mapping

*Preserved from previous questionnaire*

For each monitor, how should the workflow be selected?

**Current**: `monitors.workflows = ["a.json", "b.json"]` — positional array

**Alternative A**: Named mapping:
```toml
[[monitors.map]]
index = 0
workflow = "ultrawide"

[[monitors.map]]
index = 1
workflow = "portrait"
```

**Alternative B**: Inline in monitor section:
```toml
[monitors.0]
workflow = "ultrawide"

[monitors.1]
workflow = "portrait"
```

**Your answer**: _________________________________

---

# Q-WALL: Wallpaper Setters

## Q-WALL-001: Additional Setter Priority

Which additional wallpaper setters should be prioritized?

**Rate 1-5 (1=not needed, 5=must have)**:
- [ ] `hyprpaper` (Hyprland): ___
- [ ] `wpaperd` (Wayland daemon): ___
- [ ] `wallutils` (cross-platform): ___
- [ ] `gnome-backgrounds`: ___
- [ ] `plasma-workspace` (KDE): ___

**Or**: None needed, current setters are sufficient: [ ]

---

# Q-CONFIG: Configuration

## Q-CONFIG-001: Breaking Changes Migration

*Preserved from previous questionnaire*

When introducing breaking config changes, should the tool:

- [ ] **A) Fail hard** — Error if old keys present, show migration guide
- [ ] **B) Auto-migrate** — Transform old format to new, save backup
- [ ] **C) Warn and ignore** — Log warning, use new format only

**Your previous note**:
> "PLEASE MAKE BREAKING CHANGES"

**Confirmed**: You prefer option A (fail hard, break code)?

**Your answer**: _________________________________

---

## Q-CONFIG-002: Named Profiles

*Preserved from previous questionnaire*

Do you need named profiles (e.g., `work`, `gaming`) that switch entire config at once?

- [ ] **A) No** — Environment variables are enough
- [ ] **B) Yes, file-based** — Separate config files: `config.work.toml`, `config.gaming.toml`
- [ ] **C) Yes, in-file** — Profiles within single config.toml

**Your answer**: _________________________________

---

## Q-CONFIG-003: Per-Host Configuration

Do you need different configs for different hosts (laptop vs desktop)?

- [ ] **A) No** — NixOS configuration handles this
- [ ] **B) Yes, host detection** — Auto-detect hostname and load different settings
- [ ] **C) Yes, explicit flag** — `--host laptop` or env var

**Your answer**: _________________________________

---

# Q-MISC: Miscellaneous

## Q-MISC-001: Desktop Notifications

Should wallpaper changes trigger desktop notifications?

- [ ] **A) No** — Silent operation preferred
- [ ] **B) Yes, optional** — `notifications.enabled = true` in config
- [ ] **C) Yes, always** — Every generation sends notification

**Your answer**: _________________________________

---

## Q-MISC-002: Lock Screen Integration

Should the tool also set lock screen wallpaper?

- [ ] **A) No** — Desktop only
- [ ] **B) Same as desktop** — Lock screen = current wallpaper
- [ ] **C) Separate config** — Different wallpaper for lock screen

**If yes, which lock screen tool?**:
- [ ] swaylock
- [ ] hyprlock
- [ ] Other: _________________________________

**Your answer**: _________________________________

---

## Q-MISC-003: Waybar/Polybar Integration

Do you want status bar integration?

- [ ] **A) No** — Not needed
- [ ] **B) Status script** — `darkwall status --json` for parsing
- [ ] **C) Custom module** — Dedicated Waybar module

**Your answer**: _________________________________

---

# Additional Context

Please add any other requirements, preferences, or context not covered above:

```
_________________________________
_________________________________
_________________________________
_________________________________
_________________________________
```

---

## After Completing This Questionnaire

1. Save this file with your answers
2. I will convert answers to frozen requirements in `REQUIREMENTS.md`
3. Open questions will be removed from this file once answered
4. Implementation will follow TDD against the requirements

---

*Last Updated: 2025-11-29*
