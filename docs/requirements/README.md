# Requirements Documentation

This directory contains the formal requirements specification for DarkWall ComfyUI.

## Files

| File | Purpose |
|------|---------|
| `REQUIREMENTS.md` | Frozen behavior requirements with unique IDs |
| `QUESTIONNAIRE.md` | Open questions requiring user decisions |
| `UNCLEAR_BEHAVIORS.md` | Questions discovered during BDD writing |
| `TRACEABILITY.md` | Mapping requirements → code → tests |

---

## BDD Workflow (Preferred)

We use **Behavior-Driven Development** with `pytest-bdd`.

### Directory Structure

```
tests/
├── features/           # Gherkin .feature files
│   ├── monitor_detection.feature
│   ├── monitor_config.feature
│   ├── workflow_system.feature
│   ├── theme_system.feature
│   ├── scheduling.feature
│   ├── generation.feature
│   └── cli_status.feature
└── step_definitions/   # Python step implementations
    └── test_*.py
```

### Running BDD Tests

```bash
# Enter dev shell
nix develop

# Run all tests
pytest

# Run BDD tests only
pytest tests/step_definitions/

# Run specific feature
pytest tests/step_definitions/test_monitor_detection.py

# List all scenarios
pytest --collect-only

# Run tests for specific requirement
pytest -m "REQ-MONITOR-001"
```

### Writing New Behaviors

1. **Write Feature File** (Gherkin)
   ```gherkin
   @REQ-XXX-001
   Feature: Your Feature
       Scenario: Specific behavior
           Given some precondition
           When some action
           Then expected result
   ```

2. **Document Unclear Behaviors**
   - Add `# UNCLEAR: ...` comments in feature file
   - Add to `UNCLEAR_BEHAVIORS.md` for user to answer

3. **Write Step Definitions**
   ```python
   from pytest_bdd import scenarios, given, when, then
   
   scenarios("../features/your_feature.feature")
   
   @given("some precondition")
   def given_precondition():
       pass
   ```

4. **Run and Iterate**
   - Tests fail first (red)
   - Implement code (green)
   - Refactor

### IDE Setup

Install VSCode/Windsurf extension: **Cucumber (Gherkin) Full Support**
- Extension ID: `alexkrechik.cucumberautocomplete`

---

## Requirement ID Convention

```
REQ-{CATEGORY}-{NUMBER}
```

| Category | Domain |
|----------|--------|
| CORE | Core generation pipeline |
| COMFY | ComfyUI integration |
| PROMPT | Prompt generation & templates |
| WORKFLOW | Workflow system |
| THEME | Theme system |
| MONITOR | Multi-monitor support |
| SCHED | Scheduling & time-based features |
| WALL | Wallpaper setter integration |
| HIST | History & gallery |
| CLI | CLI interface |
| CONFIG | Configuration system |
| MISC | Miscellaneous features |
| NIX | NixOS/Nix integration |

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ FROZEN | Implemented, tested, locked |
| 🔧 IMPLEMENTED | Works, needs more tests |
| 📋 PLANNED | Designed, not implemented |
| ❓ OPEN | Requires user decision |

## Gherkin Tags

Feature files use tags to link to requirements:

```gherkin
@REQ-MONITOR-001 @REQ-MONITOR-002
Feature: Monitor Detection

    @planned
    Scenario: Not yet implemented
```

Run specific requirements:
```bash
pytest -m "REQ-MONITOR-001"
pytest -m "planned"  # Skip planned tests
```

---

*Last Updated: 2025-11-29*
