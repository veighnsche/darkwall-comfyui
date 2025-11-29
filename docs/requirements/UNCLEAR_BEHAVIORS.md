# Unclear Behaviors Discovered During BDD

> **Purpose**: Track behavior questions discovered while writing BDD scenarios.
> **Workflow**: Answer these → Convert to requirements → Remove from this list.

---

## Monitor Detection (REQ-MONITOR-001)

### Q-BDD-001: Compositor Not Running
**What happens if the compositor (niri/sway/hyprland) is not running?**

Options:
- [ ] Error with clear message
- [ ] Fall back to manual config
- [ ] Use cached previous detection

**Your answer**: _________________________________

---

### Q-BDD-002: Detection Command Failure
**What if `niri msg outputs` fails (permission denied, command not found, etc.)?**

Options:
- [ ] Error with the actual error message
- [ ] Suggest installing/configuring niri
- [ ] Try alternative compositor

**Your answer**: _________________________________

---

### Q-BDD-003: Cache Monitor Detection
**Should we cache monitor detection results?**

Options:
- [ ] No caching, detect every time
- [ ] Cache for session duration
- [ ] Cache until monitor change detected

**Your answer**: _________________________________

---

## Workflow System (REQ-WORKFLOW-001)

### Q-BDD-004: Missing Workflow File
**What if the workflow file doesn't exist?**

Options:
- [ ] Error with path that was tried
- [ ] List available workflows in error
- [ ] Create empty workflow template

**Your answer**: _________________________________

---

### Q-BDD-005: Workflow JSON Validation
**Should we validate workflow JSON structure?**

Options:
- [ ] Just check it's valid JSON
- [ ] Validate required placeholder exists
- [ ] Full schema validation

**Your answer**: _________________________________

---

## Theme System (REQ-THEME-005)

### Q-BDD-006: Default Theme Also Missing
**What if the "default" fallback theme also doesn't exist?**

Options:
- [ ] Hard error (nothing to fall back to)
- [ ] Create empty default theme
- [ ] Use hardcoded minimal prompts

**Your answer**: _________________________________

---

### Q-BDD-007: Create Theme Directories on Init
**Should `darkwall init` create theme directory structure?**

Options:
- [ ] Yes, create default theme with example atoms/prompts
- [ ] Yes, create empty structure only
- [ ] No, user creates manually

**Your answer**: _________________________________

---

## Scheduling (REQ-SCHED-002, REQ-SCHED-003)

### Q-BDD-008: Timezone for Manual Times
**What timezone should be used for manual nsfw_start/nsfw_end times?**

Options:
- [ ] System local timezone
- [ ] UTC
- [ ] Configurable timezone

**Your answer**: _________________________________

---

### Q-BDD-009: Blend Duration Configurable
**Should blend_duration_minutes be configurable?**

Options:
- [ ] Yes, in config.toml
- [ ] No, hardcode 30 minutes
- [ ] Yes, but with sensible default

**Your answer**: _________________________________

---

### Q-BDD-010: Daylight Saving Time
**How do we handle DST transitions?**

Options:
- [ ] Astral library handles it automatically
- [ ] Log warning during DST transition
- [ ] Skip blending during transition hour

**Your answer**: _________________________________

---

### Q-BDD-011: Astral Library Failure
**What if astral library fails to calculate sunset?**

Options:
- [ ] Error with message
- [ ] Fall back to manual times (if configured)
- [ ] Fall back to hardcoded default (e.g., 18:00-06:00)

**Your answer**: _________________________________

---

## Generation (REQ-CORE-002)

### Q-BDD-012: ComfyUI Queue Full
**What if ComfyUI queue is full?**

Options:
- [ ] Wait and retry (how long?)
- [ ] Error immediately
- [ ] Report queue position

**Your answer**: _________________________________

---

### Q-BDD-013: Wallpaper Setter Fails After Save
**What if wallpaper image is saved but setter command fails?**

Options:
- [ ] Report partial success
- [ ] Rollback (delete saved image)
- [ ] Keep image, log error

**Your answer**: _________________________________

---

## Config Breaking Changes (REQ-CONFIG-005)

### Q-BDD-014: Full Deprecated Keys List
**What is the complete list of deprecated config keys?**

Currently known:
- `monitors.count` (replaced by auto-detection)
- `monitors.pattern` (replaced by inline sections)
- `monitors.workflows` (array, replaced by per-monitor)
- `monitors.templates` (array, replaced by per-monitor)
- `monitors.paths` (array, replaced by per-monitor)

**Are there others?**: _________________________________

---

### Q-BDD-015: Migration Command
**Should we provide a migration command to convert old configs?**

Options:
- [ ] No, just error with instructions
- [ ] Yes, `darkwall migrate-config`
- [ ] Yes, automatic with backup

**Your answer**: _________________________________

---

## CLI Status (REQ-MISC-003)

### Q-BDD-016: Additional Status Info
**What other info should `darkwall status` show?**

Options (check all that apply):
- [ ] Last generation time per monitor
- [ ] Disk usage of history
- [ ] Current rotation position
- [ ] Queued generations
- [ ] Current prompt seed

**Your answer**: _________________________________

---

## Partial Generation

### Q-BDD-017: Partial Monitor Generation
**Should we allow generating for only configured monitors (ignoring unconfigured)?**

Options:
- [ ] No, all connected monitors must be configured (current)
- [ ] Yes, with `--skip-unconfigured` flag
- [ ] Yes, as default behavior with warning

**Your answer**: _________________________________

---

### Q-BDD-018: Disconnected Monitor After Config
**What if a configured monitor is disconnected?**

Options:
- [ ] Skip it silently
- [ ] Warn and skip
- [ ] Error

**Your answer**: _________________________________

---

*Last Updated: 2025-11-29*
