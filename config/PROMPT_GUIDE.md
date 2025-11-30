# DarkWall ComfyUI - Theme Creation Guide

> **For LLM Theme Creators**: This guide defines the **fixed structure** that themes must follow. Content examples are suggestions only—you define your theme's aesthetic, atom categories, and prompt content.

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

| Suggested Atom | Purpose |
|---------------|---------|
| `subject.txt` | Main subject/character |
| `environment.txt` | Location/setting |
| `lighting.txt` | Lighting conditions |
| `style.txt` | Artistic style |
| `pose.txt` | Character poses |
| `expression.txt` | Facial expressions |
| `outfit.txt` | Clothing/attire |
| `hair.txt` | Hair styles/colors |

**Example atom file** (`atoms/lighting.txt`):
```
dramatic side lighting with deep shadows
soft golden hour glow through window
harsh fluorescent overhead
neon signs reflecting off wet surfaces
```

---

## Prompt Files (prompts/*.prompt)

**Format**:
```
<positive prompt with __atoms__ and {variants}>
---negative---
<negative prompt>
```

### Placeholder Syntax

| Syntax | Function | Example |
|--------|----------|---------|
| `__atomname__` | Random line from `atoms/atomname.txt` | `__lighting__` |
| `{a\|b\|c}` | Random choice from inline options | `{red\|blue\|green}` |
| `{0.5::rare\|2::common}` | Weighted random choice | 0.5 weight vs 2.0 weight |

### Example Prompt File

```
masterpiece, best quality, __subject__, __environment__, __expression__, __lighting__
---negative---
lowres, blurry, deformed, ugly, extra limbs, bad anatomy, watermark, text
```

When resolved, each `__placeholder__` gets replaced with a random line from the corresponding atom file.

### Naming Prompts

Prompt filenames are arbitrary. Suggested patterns:
- Numbered: `01_scenario_name.prompt`, `02_another_scene.prompt`
- Descriptive: `office_scene.prompt`, `outdoor_night.prompt`
- Simple: `default.prompt`

---

## How Generation Works

1. System picks a random `.prompt` file from your theme's `prompts/` directory
2. For each `__atomname__` placeholder, picks a random line from `atoms/atomname.txt`
3. For each `{variant|syntax}`, picks a random option
4. Resolves all placeholders deterministically based on time-slot seed
5. Sends positive prompt and negative prompt to ComfyUI

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
# Example: Create subject atoms
cat > atoms/subject.txt << 'EOF'
your first subject option
your second subject option
your third subject option
EOF
```

### 3. Create Prompt Templates
Create `.prompt` files using your atoms:

```bash
cat > prompts/01_example.prompt << 'EOF'
best quality, __subject__, __environment__, __lighting__, __style__
---negative---
lowres, blurry, watermark, text
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
darkwall-comfyui generate --theme your_theme --dry-run
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
- **Quality tags**: Start with quality boosters (`masterpiece, best quality`)
- **Negative prompt**: Always include common artifacts to avoid
- **Balance specificity**: Too vague = generic; too specific = repetitive

### Practical Tips
- Start with 20-50 atoms per category
- Create 5-10 prompt templates for variety
- Test combinations before finalizing
- Use `{weighted|options}` for rare variations

---

## Reference: Existing Theme Structure

Example from an actual theme showing the flexibility of atom categories:

```
themes/example_theme/
├── atoms/
│   ├── environment.txt    # 54 location options
│   ├── expression.txt     # 40 expression options
│   ├── hair.txt           # 40 hair style options
│   ├── lighting.txt       # 51 lighting options
│   ├── outfit.txt         # 40 outfit options
│   ├── pose.txt           # 40 pose options
│   ├── style.txt          # 40 style options
│   └── subject.txt        # 40 subject options
└── prompts/
    ├── 01_scene_one.prompt
    ├── 02_scene_two.prompt
    └── ... (8 prompt templates)
```

**Key insight**: You choose what atoms exist. The system only requires:
1. `atoms/` directory with at least one `.txt` file
2. `prompts/` directory with at least one `.prompt` file
3. Prompts reference atoms that exist

---

## Quick Reference

| Component | Location | Format |
|-----------|----------|--------|
| Theme root | `~/.config/darkwall-comfyui/themes/<name>/` | Directory |
| Atoms | `themes/<name>/atoms/*.txt` | One per line |
| Prompts | `themes/<name>/prompts/*.prompt` | Positive + `---negative---` + Negative |

| Syntax | Meaning |
|--------|---------|
| `__name__` | Random from `atoms/name.txt` |
| `{a\|b}` | Random from inline list |
| `{0.5::a\|2::b}` | Weighted random |
| `---negative---` | Section separator |
| `# comment` | Ignored line (in atoms) |

---

## Workflow Integration

Themes can specify which ComfyUI workflow to use:

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

Workflow files live in `~/.config/darkwall-comfyui/workflows/` as `<prefix>-<resolution>.json`se a