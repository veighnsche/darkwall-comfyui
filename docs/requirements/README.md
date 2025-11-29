# Requirements Documentation

This directory contains the formal requirements specification for DarkWall ComfyUI.

## Files

| File | Purpose |
|------|---------|
| `REQUIREMENTS.md` | Frozen behavior requirements with unique IDs |
| `QUESTIONNAIRE.md` | Open questions requiring user decisions |
| `TRACEABILITY.md` | Mapping requirements → code → tests |

## Workflow

### Adding New Behavior

1. **Check QUESTIONNAIRE.md** — Is there an open question about this?
2. **If yes** — Get user answer first, then convert to requirement
3. **If no** — Add new requirement ID to REQUIREMENTS.md
4. **Update TRACEABILITY.md** — Add source file and test mappings
5. **Write tests first** — TDD: test → implement → verify

### Modifying Existing Behavior

1. **Find requirement ID** in REQUIREMENTS.md
2. **Check TRACEABILITY.md** for affected files and tests
3. **Update requirement** if behavior is changing
4. **Update tests** to match new expected behavior
5. **Implement change**

### Answering Open Questions

1. **Edit QUESTIONNAIRE.md** — Fill in answers inline
2. **AI will convert** — Answered questions become frozen requirements
3. **Remove from questionnaire** — Once converted

## Requirement ID Convention

```
REQ-{CATEGORY}-{NUMBER}
```

| Category | Domain |
|----------|--------|
| CORE | Core generation pipeline |
| COMFY | ComfyUI integration |
| PROMPT | Prompt generation & templates |
| THEME | Theme system |
| MONITOR | Multi-monitor support |
| SCHED | Scheduling & time-based features |
| WALL | Wallpaper setter integration |
| HIST | History & gallery |
| CLI | CLI interface |
| CONFIG | Configuration system |
| NIX | NixOS/Nix integration |

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ FROZEN | Implemented, tested, locked |
| 🔧 IMPLEMENTED | Works, needs more tests |
| 📋 PLANNED | Designed, not implemented |
| ❓ OPEN | Requires user decision |

## TDD Workflow

```
1. Write failing test for requirement
2. Implement minimal code to pass
3. Refactor while keeping tests green
4. Mark requirement as FROZEN when stable
```

---

*Last Updated: 2025-11-29*
