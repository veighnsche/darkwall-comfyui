# Workflow Placeholder Syntax

## New Placeholder Format

```
__PROMPT:section_name__     →  Positive prompt for section
__NEGATIVE:section_name__   →  Negative prompt for section
```

### Examples

```json
{
  "10": {
    "class_type": "CLIPTextEncode",
    "_meta": { "title": "Environment Positive" },
    "inputs": {
      "text": "__PROMPT:environment__",
      "clip": ["4", 0]
    }
  },
  "11": {
    "class_type": "CLIPTextEncode",
    "_meta": { "title": "Environment Negative" },
    "inputs": {
      "text": "__NEGATIVE:environment__",
      "clip": ["4", 0]
    }
  },
  "20": {
    "class_type": "CLIPTextEncode",
    "_meta": { "title": "Subject Positive" },
    "inputs": {
      "text": "__PROMPT:subject__",
      "clip": ["4", 0]
    }
  },
  "21": {
    "class_type": "CLIPTextEncode",
    "_meta": { "title": "Subject Negative" },
    "inputs": {
      "text": "__NEGATIVE:subject__",
      "clip": ["4", 0]
    }
  }
}
```

## Backwards Compatibility

Old placeholders are aliased to new format:

| Old Placeholder | Equivalent New Placeholder |
|-----------------|---------------------------|
| `__POSITIVE_PROMPT__` | `__PROMPT:positive__` |
| `__NEGATIVE_PROMPT__` | `__NEGATIVE:positive__` |

Both formats work. Old workflows don't need changes.

## Injection Algorithm

```python
import re

PROMPT_PATTERN = re.compile(r'__PROMPT:([a-z0-9_]+)__')
NEGATIVE_PATTERN = re.compile(r'__NEGATIVE:([a-z0-9_]+)__')

def _inject_prompts(self, workflow: dict, prompts: PromptResult) -> dict:
    workflow = json.loads(json.dumps(workflow))  # Deep copy
    
    injected = set()
    
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        
        inputs = node.get('inputs', {})
        
        for field, value in inputs.items():
            if not isinstance(value, str):
                continue
            
            # Check for new format: __PROMPT:name__
            match = PROMPT_PATTERN.match(value)
            if match:
                section = match.group(1)
                if section in prompts.prompts:
                    inputs[field] = prompts.prompts[section]
                    injected.add(f"PROMPT:{section}")
                continue
            
            # Check for new format: __NEGATIVE:name__
            match = NEGATIVE_PATTERN.match(value)
            if match:
                section = match.group(1)
                if section in prompts.negatives:
                    inputs[field] = prompts.negatives[section]
                    injected.add(f"NEGATIVE:{section}")
                continue
            
            # Backwards compat: old placeholders
            if value == "__POSITIVE_PROMPT__":
                inputs[field] = prompts.prompts.get("positive", "")
                injected.add("PROMPT:positive")
            elif value == "__NEGATIVE_PROMPT__":
                inputs[field] = prompts.negatives.get("positive", "")
                injected.add("NEGATIVE:positive")
    
    return workflow
```

## Validation

### Required vs Optional Sections

The workflow declares what it needs via placeholders. The template provides sections.

**Strict mode** (recommended for new workflows):
- Error if workflow has `__PROMPT:X__` but template lacks `---X---`

**Lenient mode** (for migration):
- Warn if section missing
- Fall back to `positive` section if available
- Use empty string as last resort

### Logging

```
INFO: Injected prompts: PROMPT:environment, PROMPT:subject, NEGATIVE:environment, NEGATIVE:subject
WARN: Workflow requests PROMPT:style but template has no ---style--- section
```

## Workflow Discovery

To help users understand what a workflow needs:

```bash
darkwall workflow inspect my-workflow.json
```

Output:
```
Workflow: my-workflow.json
Required prompt sections:
  - environment (positive + negative)
  - subject (positive + negative)

Template sections needed:
  ---environment---
  ---environment:negative---
  ---subject---
  ---subject:negative---
```
