# Workflow Placeholder Syntax

## New Placeholder Format

```
$$section_name$$     →  Positive prompt for section
$$section_name:negative$$   →  Negative prompt for section
```

### Examples

```json
{
  "10": {
    "class_type": "CLIPTextEncode",
    "_meta": { "title": "Environment Positive" },
    "inputs": {
      "text": "$$environment$$",
      "clip": ["4", 0]
    }
  },
  "11": {
    "class_type": "CLIPTextEncode",
    "_meta": { "title": "Environment Negative" },
    "inputs": {
      "text": "$$environment:negative$$",
      "clip": ["4", 0]
    }
  },
  "20": {
    "class_type": "CLIPTextEncode",
    "_meta": { "title": "Subject Positive" },
    "inputs": {
      "text": "$$subject$$",
      "clip": ["4", 0]
    }
  },
  "21": {
    "class_type": "CLIPTextEncode",
    "_meta": { "title": "Subject Negative" },
    "inputs": {
      "text": "$$subject:negative$$",
      "clip": ["4", 0]
    }
  }
}
```

## Unified Syntax

The same `$$section$$` syntax is used in both `.prompt` files and workflow JSON:

| `.prompt` file | Workflow JSON | Description |
|----------------|---------------|-------------|
| `$$environment$$` | `"$$environment$$"` | Environment positive prompt |
| `$$environment:negative$$` | `"$$environment:negative$$"` | Environment negative prompt |
| `$$subject$$` | `"$$subject$$"` | Subject positive prompt |
| `$$subject:negative$$` | `"$$subject:negative$$"` | Subject negative prompt |

Section names are arbitrary - use whatever makes sense for your workflow.

## Injection Algorithm

```python
import re

# Matches $$section_name$$ for positive prompts
SECTION_PATTERN = re.compile(r'^__([a-z0-9_]+)__$')
# Matches $$section_name:negative$$ for negative prompts
NEGATIVE_SECTION_PATTERN = re.compile(r'^__([a-z0-9_]+):negative__$')

def inject_prompts(workflow: dict, prompts: PromptResult) -> dict:
    workflow = json.loads(json.dumps(workflow))  # Deep copy
    
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        
        inputs = node.get('inputs', {})
        
        for field, value in inputs.items():
            if not isinstance(value, str):
                continue
            
            # Check for negative section first: $$name:negative$$
            match = NEGATIVE_SECTION_PATTERN.match(value)
            if match:
                section = match.group(1)
                inputs[field] = prompts.negatives.get(section, "")
                continue
            
            # Check for positive section: $$name$$
            match = SECTION_PATTERN.match(value)
            if match:
                section = match.group(1)
                if section in prompts.prompts:
                    inputs[field] = prompts.prompts[section]
                continue
    
    return workflow
```

## Validation

### Required vs Optional Sections

The workflow declares what it needs via placeholders. The template provides sections.

**Behavior**:
- Error if workflow has `__X__` but template lacks `__X__` section
- Missing negative sections use empty string (lenient)
- Logs warning for missing sections

### Logging

```
INFO: Injected prompts: environment, subject, environment:negative, subject:negative
WARN: Workflow requests $$style$$ but template has no matching section
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
  $$environment$$
  $$environment:negative$$
  $$subject$$
  $$subject:negative$$
```
