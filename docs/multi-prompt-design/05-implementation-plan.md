# Implementation Plan

## Phase 1: Core Data Structures

### 1.1 Update PromptResult

**File**: `src/darkwall_comfyui/prompt_generator.py`

```python
@dataclass
class PromptResult:
    prompts: dict[str, str]
    negatives: dict[str, str]
    seed: Optional[int] = None
    
    @property
    def positive(self) -> str:
        return self.prompts.get("positive", "")
    
    @property
    def negative(self) -> str:
        return self.negatives.get("positive", "")
```

**Tests**: Update `tests/test_prompt_generator.py`

### 1.2 Update Section Parser

**File**: `src/darkwall_comfyui/prompt_generator.py`

Change `_parse_template_sections` from:
```python
def _parse_template_sections(self, template: str) -> Tuple[str, str]:
```

To:
```python
def _parse_template_sections(self, template: str) -> dict[str, str]:
```

**Backwards compat**: 
- Content before first `---name---` goes to `positive`
- `---negative---` alone maps to `positive:negative`

## Phase 2: Prompt Generation

### 2.1 Update generate_prompt_pair

**File**: `src/darkwall_comfyui/prompt_generator.py`

```python
def generate_prompt_pair(self, monitor_index: int = None, ...) -> PromptResult:
    sections = self._parse_template_sections(template)
    
    prompts = {}
    negatives = {}
    
    for section_name, content in sections.items():
        if section_name.endswith(':negative'):
            base_name = section_name[:-9]  # Remove ':negative'
            negatives[base_name] = self._resolve_template(content, seed + hash(section_name))
        elif section_name == 'negative':
            # Legacy: ---negative--- maps to positive:negative
            negatives['positive'] = self._resolve_template(content, seed + 50000)
        else:
            prompts[section_name] = self._resolve_template(content, seed + hash(section_name))
    
    return PromptResult(prompts=prompts, negatives=negatives, seed=seed)
```

## Phase 3: Workflow Injection

### 3.1 Update _inject_prompts

**File**: `src/darkwall_comfyui/comfy/client.py`

Add regex patterns:
```python
PROMPT_PATTERN = re.compile(r'^__PROMPT:([a-z0-9_]+)__$')
NEGATIVE_PATTERN = re.compile(r'^__NEGATIVE:([a-z0-9_]+)__$')
```

Update injection logic to:
1. Match new `__PROMPT:name__` format
2. Match new `__NEGATIVE:name__` format  
3. Fall back to old `__POSITIVE_PROMPT__` / `__NEGATIVE_PROMPT__`

### 3.2 Add Validation

- Warn if workflow requests section not in template
- Log all injected sections for debugging

## Phase 4: Testing

### 4.1 Unit Tests

- `test_parse_sections_legacy` — old format still works
- `test_parse_sections_multi` — new multi-section format
- `test_prompt_result_backwards_compat` — .positive/.negative properties
- `test_inject_new_placeholders` — __PROMPT:name__ injection
- `test_inject_legacy_placeholders` — __POSITIVE_PROMPT__ still works

### 4.2 Integration Tests

- End-to-end with multi-section template + multi-placeholder workflow
- End-to-end with legacy template + legacy workflow (regression)

## Phase 5: Documentation

### 5.1 Update docs/configuration.md

Add section on multi-prompt templates.

### 5.2 Update docs/workflow-migration.md

Add section on new placeholder format.

### 5.3 Create example templates

Add example multi-section templates to `config/themes/*/prompts/`.

## Checklist

- [ ] Phase 1.1: Update PromptResult dataclass
- [ ] Phase 1.2: Update _parse_template_sections
- [ ] Phase 2.1: Update generate_prompt_pair
- [ ] Phase 3.1: Update _inject_prompts
- [ ] Phase 3.2: Add validation/logging
- [ ] Phase 4.1: Unit tests
- [ ] Phase 4.2: Integration tests
- [ ] Phase 5.1: Update configuration docs
- [ ] Phase 5.2: Update migration docs
- [ ] Phase 5.3: Create example templates

## Estimated Changes

| File | Lines Changed |
|------|---------------|
| `prompt_generator.py` | ~80 |
| `comfy/client.py` | ~40 |
| `tests/test_prompt_generator.py` | ~60 |
| `tests/test_client.py` | ~30 |
| Documentation | ~100 |
| **Total** | **~310** |
