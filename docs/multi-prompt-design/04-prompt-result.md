# PromptResult Dataclass Changes

## Current Implementation

```python
@dataclass
class PromptResult:
    """Result of prompt generation with positive and negative prompts."""
    positive: str
    negative: str = ""
    seed: Optional[int] = None
```

## New Implementation

```python
@dataclass
class PromptResult:
    """Result of prompt generation with named prompt sections."""
    prompts: dict[str, str]    # {"environment": "...", "subject": "..."}
    negatives: dict[str, str]  # {"environment": "...", "subject": "..."}
    seed: Optional[int] = None
    
    # Backwards compatibility properties
    @property
    def positive(self) -> str:
        """Get the 'positive' section for backwards compatibility."""
        return self.prompts.get("positive", "")
    
    @property
    def negative(self) -> str:
        """Get the 'positive:negative' section for backwards compatibility."""
        return self.negatives.get("positive", "")
    
    def get_prompt(self, section: str) -> str:
        """Get a named prompt section."""
        return self.prompts.get(section, "")
    
    def get_negative(self, section: str) -> str:
        """Get a named negative section."""
        return self.negatives.get(section, "")
    
    def sections(self) -> list[str]:
        """List all available prompt sections."""
        return list(self.prompts.keys())
```

## Factory Method Update

```python
@classmethod
def from_legacy(cls, positive: str, negative: str = "", seed: int = None) -> 'PromptResult':
    """Create from legacy positive/negative format."""
    return cls(
        prompts={"positive": positive},
        negatives={"positive": negative} if negative else {},
        seed=seed
    )
```

## Usage Examples

### New Multi-Section Usage

```python
result = generator.generate_prompt_pair(monitor_index=0)

# Access named sections
env_prompt = result.prompts["environment"]
env_negative = result.negatives["environment"]
subject_prompt = result.prompts["subject"]
subject_negative = result.negatives["subject"]

# List available sections
print(result.sections())  # ["environment", "subject"]
```

### Backwards Compatible Usage

```python
result = generator.generate_prompt_pair(monitor_index=0)

# Old code still works
positive = result.positive  # Gets "positive" section
negative = result.negative  # Gets "positive:negative" section
```

## Serialization

For logging and debugging:

```python
def __str__(self) -> str:
    sections = []
    for name in sorted(self.prompts.keys()):
        sections.append(f"[{name}] {self.prompts[name][:50]}...")
        if name in self.negatives:
            sections.append(f"[{name}:negative] {self.negatives[name][:50]}...")
    return "\n".join(sections)
```

## Test Cases

```python
def test_backwards_compat():
    result = PromptResult(
        prompts={"positive": "a beautiful landscape"},
        negatives={"positive": "ugly, blurry"},
        seed=12345
    )
    assert result.positive == "a beautiful landscape"
    assert result.negative == "ugly, blurry"

def test_multi_section():
    result = PromptResult(
        prompts={
            "environment": "mountain landscape",
            "subject": "woman standing right"
        },
        negatives={
            "environment": "ugly",
            "subject": "bad anatomy"
        },
        seed=12345
    )
    assert result.get_prompt("environment") == "mountain landscape"
    assert result.get_negative("subject") == "bad anatomy"
    assert result.sections() == ["environment", "subject"]
```
