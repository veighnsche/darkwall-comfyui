# Current State Analysis

## File Locations

| Component | Path |
|$$$$-----|$$$$|
| Prompt Generator | `src/darkwall_comfyui/prompt_generator.py` |
| ComfyUI Client | `src/darkwall_comfyui/comfy/client.py` |
| Prompt Templates | `config/themes/{theme}/prompts/*.prompt` |
| Atom Files | `config/themes/{theme}/atoms/*.txt` |

## Current `.prompt` Format

```
# Comments start with #

positive prompt content here with $$wildcards$$ and {variants|syntax}

$$negative$$
negative prompt content here
```

### Parsing Logic (`_parse_template_sections`)

```python
def _parse_template_sections(self, template: str) -> Tuple[str, str]:
    # Split on $$negative$$ separator
    separator = '$$negative$$'
    if separator in content:
        parts = content.split(separator, 1)
        positive = parts[0].strip()
        negative = parts[1].strip()
    else:
        positive = content.strip()
        negative = ""
    
    return positive, negative
```

**Limitation**: Only supports exactly two sections (positive, negative).

## Current `PromptResult` Dataclass

```python
@dataclass
class PromptResult:
    positive: str
    negative: str = ""
    seed: Optional[int] = None
```

**Limitation**: Fixed to two string fields.

## Current Workflow Injection (`_inject_prompts`)

```python
def _inject_prompts(self, workflow: dict, prompts: PromptResult) -> dict:
    for node_id, node in workflow.items():
        inputs = node.get('inputs', {})
        for field, value in inputs.items():
            if value == "__POSITIVE_PROMPT__":
                inputs[field] = prompts.positive
            elif value == "__NEGATIVE_PROMPT__" and prompts.negative:
                inputs[field] = prompts.negative
```

**Limitation**: Hardcoded placeholder names.

## Current Workflow Example

```json
{
  "3": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "__POSITIVE_PROMPT__",
      "clip": ["4", 0]
    }
  },
  "7": {
    "class_type": "CLIPTextEncode", 
    "inputs": {
      "text": "__NEGATIVE_PROMPT__",
      "clip": ["4", 0]
    }
  }
}
```

## What Needs to Change

1. **PromptResult** — Support arbitrary named prompts
2. **_parse_template_sections** — Parse multiple `$$name$$` sections
3. **_inject_prompts** — Match `$$name$$` patterns dynamically
4. **Backwards compatibility** — Old templates and workflows must still work
