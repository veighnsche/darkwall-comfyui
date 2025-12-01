# Theme Config Migration for Multi-Prompt System

## Overview

All themes using the 60/40 wallpaper layout (dark, light, uncannyvalley) need their `.prompt` files updated to use the new multi-section format with `$$environment$$` and `$$subject$$` sections.

## Design Principles

### 1. Environment Section (Left 60%)
- Background/scene description
- Atmospheric elements
- Lighting conditions
- Should NOT include focal subjects (people, characters)

### 2. Subject Section (Right 40%)
- Focal element positioned on right side of frame
- Character/person descriptions
- Pose and positioning
- Explicitly states "right side of frame" or similar

### 3. Negative Sections
- `$$environment:negative$$`: Scene/quality negatives
- `$$subject:negative$$`: Anatomy/character negatives

## Template Structure

```
# [Theme] [Style] Prompt
# [Description]

$$environment$$
[scene description], $$environment$$, $$lighting$$, $$mood$$, $$style$$,
cinematic composition, detailed background, [theme-specific modifiers]

$$environment:negative$$
[quality negatives], [unwanted scene elements]

$$subject$$
[character/focal element], positioned on right side of frame,
$$pose$$, $$expression$$, [theme-specific subject modifiers]

$$subject:negative$$
[anatomy negatives], [character-specific negatives]
```

## Theme-Specific Patterns

### Dark Theme
- **Environment**: Moody, atmospheric, noir, cyberpunk, gothic settings
- **Subject**: Silhouettes, mysterious figures, dramatic poses
- **Negatives**: Bright, sunny, cheerful elements

### Light Theme  
- **Environment**: Bright, airy, natural, serene landscapes
- **Subject**: Nature elements, architectural details, soft subjects
- **Negatives**: Dark, gloomy, night, nsfw content

### Uncanny Valley Theme
- **Environment**: Anime-style backgrounds, aesthetic settings
- **Subject**: Anime girl with specific outfit/pose, right side positioning
- **Negatives**: Bad anatomy, deformed, low quality

## Atom Usage

Atoms remain unchanged. They're referenced via `$$atom_name$$` wildcards:

| Atom | Used In |
|$$$$|$$$$---|
| `$$environment$$` | Environment section |
| `$$lighting$$` | Environment section |
| `$$mood$$` | Both sections |
| `$$style$$` | Both sections |
| `$$colors$$` | Both sections |
| `$$composition$$` | Environment section |
| `$$subject$$` | Subject section |
| `$$pose$$` | Subject section |
| `$$expression$$` | Subject section |
| `$$hair$$` | Subject section (uncannyvalley) |
| `$$outfit$$` | Subject section (uncannyvalley) |

## Migration Checklist

### Dark Theme Prompts ✅
- [x] default.prompt
- [x] artistic_boudoir.prompt
- [x] artistic_fantasy.prompt
- [x] artistic_nude.prompt
- [x] artistic_silhouette.prompt
- [x] cinematic.prompt
- [x] cosmic.prompt
- [x] cyberpunk.prompt
- [x] gothic.prompt
- [x] noir.prompt

### Light Theme Prompts ✅
- [x] default.prompt
- [x] abstract.prompt
- [x] landscape.prompt
- [x] minimal.prompt
- [x] nature.prompt

### Uncanny Valley Theme Prompts ✅
- [x] default.prompt
- [x] bikini.prompt
- [x] casual.prompt
- [x] elegant.prompt
- [x] lingerie.prompt
- [x] onsen.prompt
