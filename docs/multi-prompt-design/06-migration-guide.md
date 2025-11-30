# Migration Guide

## For Existing Users

### Your Templates Still Work

If you have templates like this:

```
beautiful landscape, mountains

---negative---
ugly, blurry
```

**No changes needed.** This is automatically parsed as:

| Section | Content |
|---------|---------|
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
    "inputs": { "text": "__PROMPT:environment__" }
  },
  "20": {
    "inputs": { "text": "__PROMPT:subject__" }
  }
}
```

### Step 2: Update Your Template

Add named sections to your `.prompt` file:

**Before:**
```
beautiful woman in forest, sunset lighting

---negative---
ugly, blurry
```

**After:**
```
---environment---
dense forest, golden sunset, volumetric lighting, cinematic

---environment:negative---
ugly, blurry, low quality

---subject---
beautiful woman, standing on right side of frame, elegant pose

---subject:negative---
bad anatomy, deformed, extra limbs
```

### Step 3: Test

```bash
darkwall generate --dry-run
```

Check that prompts are injected correctly.

## Workflow Placeholder Reference

| Placeholder | Template Section |
|-------------|------------------|
| `__PROMPT:positive__` | `---positive---` or content before first section |
| `__NEGATIVE:positive__` | `---positive:negative---` or `---negative---` |
| `__PROMPT:environment__` | `---environment---` |
| `__NEGATIVE:environment__` | `---environment:negative---` |
| `__PROMPT:subject__` | `---subject---` |
| `__NEGATIVE:subject__` | `---subject:negative---` |
| `__POSITIVE_PROMPT__` | Same as `__PROMPT:positive__` (legacy) |
| `__NEGATIVE_PROMPT__` | Same as `__NEGATIVE:positive__` (legacy) |

## Common Patterns

### Niri Layout (Subject on Right)

For Niri compositor where apps occupy left 60%:

```
---environment---
__environment__, wide landscape, detailed background,
left side focus, {morning|afternoon|evening} lighting

---environment:negative---
subject in center, person in center, ugly, blurry

---subject---
__character__, positioned on right third of frame,
looking left, __pose__, __expression__

---subject:negative---
centered subject, bad anatomy, deformed
```

### Dual Monitor (Different Subjects)

For workflows that generate different content per area:

```
---left---
abstract geometric patterns, cool colors

---right---
organic flowing shapes, warm colors

---left:negative---
realistic, photographic

---right:negative---
geometric, angular
```

## Troubleshooting

### "Workflow requests PROMPT:X but template has no ---X--- section"

Your workflow uses `__PROMPT:X__` but your template doesn't have a `---X---` section.

**Fix**: Add the missing section to your template.

### "No prompts injected"

Your workflow doesn't have any recognized placeholders.

**Fix**: Add `__PROMPT:name__` placeholders to your workflow's text nodes.

### "Template has sections but workflow uses legacy placeholders"

You updated your template to multi-section but workflow still uses `__POSITIVE_PROMPT__`.

**Fix**: Either:
1. Update workflow to use `__PROMPT:section__` format
2. Or keep a `---positive---` section in your template for backwards compat
