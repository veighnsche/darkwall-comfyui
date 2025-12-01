# New `.prompt` File Format

## Section Syntax

Sections are marked with `$$name$$` on their own line:

```
$$section_name$$
content for this section

$$another_section$$
content for another section

$$section_name:negative$$
negative content for section_name
```

### Section Name Rules

- Lowercase alphanumeric + underscores: `[a-z0-9_]+`
- Negative sections use `:negative` suffix
- First section without a marker is implicitly `$$positive$$`

## Full Example

```
# Multi-prompt template for Niri compositor layout
# Environment on left, subject on right 40% of screen

$$environment$$
__environment__, __lighting__, __weather__, 
cinematic composition, detailed background,
{morning light|golden hour|blue hour|night scene}

$$environment:negative$$
ugly, blurry, low quality, watermark, text, logo

$$subject$$
__character__, standing on right side of frame,
__pose__, __expression__, __clothing__,
looking at viewer, detailed face

$$subject:negative$$
bad anatomy, extra limbs, deformed, mutated,
poorly drawn face, extra fingers
```

Note: `$$section$$` marks section boundaries, `__wildcard__` references atom files.

## Backwards Compatibility

### Old Format (Still Works)

```
some positive prompt here

$$negative$$
some negative prompt here
```

This is parsed as:

| Section | Content |
|$$$$---|$$$$---|
| `positive` | "some positive prompt here" |
| `positive:negative` | "some negative prompt here" |

### No Sections (Still Works)

```
just a prompt with no sections
```

This is parsed as:

| Section | Content |
|$$$$---|$$$$---|
| `positive` | "just a prompt with no sections" |

## Parsing Algorithm

```python
def _parse_template_sections(self, template: str) -> dict[str, str]:
    sections = {}
    current_section = "positive"  # Default section
    current_content = []
    
    for line in template.split('\n'):
        stripped = line.strip()
        
        # Skip comments
        if stripped.startswith('#'):
            continue
        
        # Check for section marker
        if stripped.startswith('---') and stripped.endswith('---'):
            # Save previous section
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            
            # Start new section
            current_section = stripped[3:-3]  # Remove ---
            current_content = []
        else:
            current_content.append(line)
    
    # Save final section
    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections
```

## Section Naming Convention

| Workflow Need | Prompt Section | Negative Section |
|$$____$$---|$$____$$----|$$________$$|
| Main prompt | `positive` | `positive:negative` or `negative` |
| Environment/background | `environment` | `environment:negative` |
| Subject/foreground | `subject` | `subject:negative` |
| Style modifiers | `style` | `style:negative` |
| Custom | `{name}` | `{name}:negative` |

## Wildcard Resolution

Each section is resolved independently with the same seed base but different variation offsets:

```python
for section_name, template in sections.items():
    # Use section name to create unique variation offset
    section_offset = hash(section_name) % 10000
    resolved = self._resolve_template(template, seed + section_offset)
    result[section_name] = resolved
```

This ensures:
- Same seed = reproducible results
- Different sections get different random choices
- Same section across runs with same seed = same output
