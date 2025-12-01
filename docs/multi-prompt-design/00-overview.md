# Multi-Prompt System Design

## Problem Statement

Niri compositor places application windows on the left 60% of the screen. For wallpapers to look good, the **subject** (e.g., a person) must be positioned on the **right 40%** of the screen where it won't be obscured.

Current ComfyUI workflows support this via two separate prompt nodes:
1. **Environment prompt** — describes the background/scene
2. **Subject prompt** — describes the focal element (positioned right)

However, DarkWall currently only supports two hardcoded placeholders:
- `__POSITIVE_PROMPT__`
- `__NEGATIVE_PROMPT__`

This is insufficient for workflows that need multiple distinct prompts.

## Goal

Design an **arbitrary named prompt system** that:
1. Supports any number of named prompt sections
2. Each section can have its own negative prompt
3. Remains backwards compatible with existing workflows and templates
4. Keeps the `.prompt` file format simple and readable

## Design Documents

| Document | Description |
|$$$$----|$$____$$-|
| [01-current-state.md](./01-current-state.md) | Analysis of current implementation |
| [02-new-prompt-format.md](./02-new-prompt-format.md) | New `.prompt` file format specification |
| [03-workflow-placeholders.md](./03-workflow-placeholders.md) | New workflow placeholder syntax |
| [04-prompt-result.md](./04-prompt-result.md) | Changes to PromptResult dataclass |
| [05-implementation-plan.md](./05-implementation-plan.md) | Step-by-step implementation |
| [06-migration-guide.md](./06-migration-guide.md) | How to migrate existing templates |

## Quick Example

**Before** (single prompt):
```
beautiful landscape, mountains, sunset

$$negative$$
ugly, blurry
```

**After** (multiple named prompts):
```
$$environment$$
mountain landscape, golden hour lighting, cinematic atmosphere

$$environment:negative$$
ugly, blurry, low quality

$$subject$$
elegant woman in flowing dress, standing on right side of frame

$$subject:negative$$
bad anatomy, extra limbs, deformed face
```

**Workflow placeholders**:
```
$$environment$$    →  injects environment section
$$subject$$        →  injects subject section
$$environment:negative$$  →  injects environment:negative section
$$subject:negative$$      →  injects subject:negative section
```
