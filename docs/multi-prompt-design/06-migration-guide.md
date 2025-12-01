# Migration Guide

## For Existing Users

### Your Templates Still Work

If you have templates like this:

```
beautiful landscape, mountains

$$negative$$
ugly, blurry
```

**No changes needed.** This is automatically parsed as:

| Section | Content |
|$$$$---|$$$$---|
| `positive` | "beautiful landscape, mountains" |
| `positive:negative` | "ugly, blurry" |

### Your Workflows Still Work

If your workflows use:

```json
"text": "__POSITIVE_PROMPT__"
"text": "__NEGATIVE_PROMPT__"
```

**No changes needed.** These are automatically mapped to the `positive` section.

## Upgrading to Multi-Prompt

### Step 1: Update Your Workflow

Change your ComfyUI workflow to use named placeholders:

**Before:**
```json
{
  "3": {
    "inputs": { "text": "__POSITIVE_PROMPT__" }
  }
}
```

**After:**
```json
{
  "10": {
    "inputs": { "text": "$$environment$$" }
  },
  "20": {
    "inputs": { "text": "$$subject$$" }
  }
}
```

### Step 2: Update Your Template

Add named sections to your `.prompt` file:

**Before:**
```
beautiful woman in forest, sunset lighting

$$negative$$
ugly, blurry
```

**After:**
```
$$environment$$
dense forest, golden sunset, volumetric lighting, cinematic

$$environment:negative$$
ugly, blurry, low quality

$$subject$$
beautiful woman, standing on right side of frame, elegant pose

$$subject:negative$$
bad anatomy, deformed, extra limbs
```

### Step 3: Test

```bash
darkwall generate --dry-run
```

Check that prompts are injected correctly.

## Workflow Placeholder Reference

| Placeholder | Template Section |
|$$____$$-|$$________$$|
| `$$positive$$` | `$$positive$$` or content before first section |
| `$$positive:negative$$` | `$$positive:negative$$` or `$$negative$$` |
| `$$environment$$` | `$$environment$$` |
| `$$environment:negative$$` | `$$environment:negative$$` |
| `$$subject$$` | `$$subject$$` |
| `$$subject:negative$$` | `$$subject:negative$$` |
| `__POSITIVE_PROMPT__` | Same as `$$positive$$` (legacy) |
| `__NEGATIVE_PROMPT__` | Same as `$$positive:negative$$` (legacy) |

## Common Patterns

### Niri Layout (Subject on Right)

For Niri compositor where apps occupy left 60%:

```
$$environment$$
$$environment$$, wide landscape, detailed background,
left side focus, {morning|afternoon|evening} lighting

$$environment:negative$$
subject in center, person in center, ugly, blurry

$$subject$$
$$character$$, positioned on right third of frame,
looking left, $$pose$$, $$expression$$

$$subject:negative$$
centered subject, bad anatomy, deformed
```

### Dual Monitor (Different Subjects)

For workflows that generate different content per area:

```
$$left$$
abstract geometric patterns, cool colors

$$right$$
organic flowing shapes, warm colors

$$left:negative$$
realistic, photographic

$$right:negative$$
geometric, angular
```

## Troubleshooting

### "Workflow requests PROMPT:X but template has no ---X--- section"

Your workflow uses `__PROMPT:X__` but your template doesn't have a `---X---` section.

**Fix**: Add the missing section to your template.

### "No prompts injected"

Your workflow doesn't have any recognized placeholders.

**Fix**: Add `$$name$$` placeholders to your workflow's text nodes.

### "Template has sections but workflow uses legacy placeholders"

You updated your template to multi-section but workflow still uses `__POSITIVE_PROMPT__`.

**Fix**: Either:
1. Update workflow to use `$$section$$` format
2. Or keep a `$$positive$$` section in your template for backwards compat
