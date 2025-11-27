# DarkWall ComfyUI - Prompt Atom Guide

This guide explains how to create and modify prompt atoms for each of the four pillars that generate deterministic dark-mode wallpapers.

## Overview

The prompt generator combines one atom from each of the four numbered files to create a complete wallpaper prompt. Each file serves a specific purpose in the composition:

- **1_subject.txt** - The main focal point
- **2_environment.txt** - The surrounding context  
- **3_lighting.txt** - The illumination and color scheme
- **4_style.txt** - The artistic approach and composition

---

## 1_subject.txt - Main Focal Point

**Purpose**: Defines the primary visual element that anchors your wallpaper composition.

### Design Principles
- **Single focal point**: Each atom should describe one main subject, not multiple elements
- **Silhouette-friendly**: Subjects should work well as dark shapes against darker backgrounds
- **Scalable**: Must look good at wallpaper resolutions without becoming pixelated or losing impact
- **Dark-mode compatible**: Avoid subjects that require bright, sunny environments to make sense

### Good Examples
```
lone city skyline at dusk
solitary mountain peak
twisted tree with glowing leaves
abandoned lighthouse
```

### What to Avoid
- ❌ "happy family picnic" (requires bright, cheerful lighting)
- ❌ "busy market street" (too many focal points)
- ❌ "colorful flower garden" (inherently bright and cheerful)

### Tips for New Atoms
- Think about what looks striking in silhouette or low light
- Consider architectural elements, natural formations, or mystical objects
- Keep descriptions concise but evocative
- Focus on solitary or isolated elements

---

## 2_environment.txt - Surrounding Context

**Purpose**: Provides the setting and atmosphere that complements your subject.

### Design Principles
- **Naturally dark**: Environments should inherently support dark-mode aesthetics
- **Negative space**: Provide room for desktop icons and UI elements
- **Depth creation**: Add sense of scale and distance to the composition
- **Subject compatibility**: Must work well with the subjects from 1_subject.txt

### Good Examples
```
above a dark ocean
in a misty valley
against star-filled sky
within canyon walls
```

### What to Avoid
- ❌ "sunny beach paradise" (bright, cheerful environment)
- ❌ "colorful flower meadow" (inherently bright setting)
- ❌ "bustling city square" (too busy, no negative space)

### Tips for New Atoms
- Think about locations that are naturally dark or can be rendered darkly
- Consider atmospheric conditions (fog, mist, night, space)
- Include spatial relationships (above, within, beside, through)
- Ensure environments don't compete with subjects for attention

---

## 3_lighting.txt - Illumination & Color

**Purpose**: Defines the lighting scheme and color palette for dark-mode compatibility.

### Design Principles
- **Dark dominance**: >70% of the image should be dark areas
- **Limited accents**: Small amounts of bright color for visual interest
- **Cool temperature**: Prefer blues, purples, and cool tones over warm yellows
- **High contrast**: Ensure sufficient contrast for UI element visibility

### Good Examples
```
low-key lighting
navy and charcoal palette
moonlit blues
neon blue accents
dramatic contrast
```

### What to Avoid
- ❌ "bright sunny day" (completely opposite of dark mode)
- ❌ "rainbow colors everywhere" (too many bright colors)
- ❌ "pastel pink and yellow" (warm, cheerful palette)

### Tips for New Atoms
- Focus on lighting techniques (low-key, backlighting, rim lighting)
- Describe color palettes rather than specific colors
- Include contrast and atmosphere descriptors
- Think about how lighting affects mood and usability

---

## 4_style.txt - Artistic Approach & Composition

**Purpose**: Defines the artistic style and compositional guidelines for wallpaper use.

### Design Principles
- **Wallpaper optimization**: Explicit references to 16:9 format and wallpaper use
- **Icon space**: Provide negative space for desktop elements
- **High quality**: Emphasize detail and resolution suitable for wallpapers
- **No text**: Explicitly avoid watermarks, signatures, or text elements

### Good Examples
```
cinematic 16:9 wide shot
lots of negative space for icons
minimalist composition
high contrast edges
professional photography style
```

### What to Avoid
- ❌ "portrait orientation" (wrong aspect ratio for wallpapers)
- ❌ "text overlay with title" (interferes with desktop use)
- ❌ "busy detailed background" (no room for icons)

### Tips for New Atoms
- Include aspect ratio references (16:9, wide shot, cinematic)
- Mention negative space or composition explicitly
- Focus on artistic styles that scale well to high resolutions
- Consider photography vs digital art aesthetics

---

## Creating New Atoms

### File Format
- Each line in the numbered files is a separate atom
- Empty lines are ignored
- Lines starting with # are treated as comments (optional)
- Use simple, descriptive text without complex punctuation

### Adding New Atoms
1. Open the appropriate numbered file (1-4) in `config/atoms/`
2. Add your new atom on a new line
3. Ensure it follows the design principles for that pillar
4. Save the file
5. Test the new combination by running the generator

### Testing New Atoms
```bash
# Test with verbose output to see the generated prompt
./result/bin/generate-wallpaper-once --verbose

# The output will show you exactly how your new atom combines with others
```

### Theme Variations
You can create theme-specific atom directories:
```
config/atoms/
├── 1_subject.txt
├── 2_environment.txt  
├── 3_lighting.txt
├── 4_style.txt
└── themes/
    ├── cyberpunk/
    │   ├── 1_subject.txt
    │   ├── 2_environment.txt
    │   ├── 3_lighting.txt
    │   └── 4_style.txt
    └── nature/
        ├── 1_subject.txt
        ├── 2_environment.txt
        ├── 3_lighting.txt
        └── 4_style.txt
```

Then specify the theme in `config.toml`:
```toml
[prompt]
theme = "cyberpunk"
```

## Best Practices

1. **Consistency**: Keep atom descriptions similar in length and complexity within each file
2. **Variety**: Ensure diverse options across all four pillars for interesting combinations
3. **Dark-mode first**: Always test how atoms look in dark wallpaper contexts
4. **Combinations matter**: Some atoms work better together than others
5. **Iterate**: Start with a few atoms per file, then expand based on results

## Example Combinations

Here's how atoms combine to create complete prompts:

**Subject**: `lone city skyline at dusk`  
**Environment**: `above a dark ocean`  
**Lighting**: `neon blue accents`  
**Style**: `cinematic 16:9 wide shot`

**Final Prompt**:
```
lone city skyline at dusk above a dark ocean, neon blue accents, cinematic 16:9 wide shot, 16:9 wallpaper, dark mode friendly, no text, no watermark, no signature, high quality, detailed
```

This structured approach ensures consistent, high-quality dark-mode wallpapers while allowing for creative variety through controlled randomization.
