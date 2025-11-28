# Contributing to DarkWall ComfyUI

Guide for contributing to DarkWall ComfyUI, a multi-monitor wallpaper generator using ComfyUI.

## Table of Contents

- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Bug Reports](#bug-reports)
- [Feature Requests](#feature-requests)
- [Documentation](#documentation)

## Development Setup

### Prerequisites

- Python 3.9+
- Nix (recommended) or Python development environment
- ComfyUI server for testing (can be mocked)

### Getting Started

#### Using Nix (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/darkwall-comfyui.git
cd darkwall-comfyui

# Enter development environment
nix develop

# Run tests
pytest

# Run CLI
python -m darkwall_comfyui --help
```

#### Using Python

```bash
# Clone the repository
git clone https://github.com/yourusername/darkwall-comfyui.git
cd darkwall-comfyui

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements-dev.txt

# Install in development mode
pip install -e .

# Run tests
pytest
```

### Project Structure

```
darkwall-comfyui/
├── src/darkwall_comfyui/
│   ├── __init__.py
│   ├── cli.py              # CLI entry point
│   ├── config.py           # Configuration system
│   ├── exceptions.py       # Exception hierarchy
│   ├── prompt_generator.py # Prompt generation
│   ├── commands/           # CLI commands
│   │   ├── generate.py
│   │   ├── gallery.py
│   │   ├── prompt.py
│   │   └── ...
│   ├── comfy/              # ComfyUI integration
│   │   ├── client.py
│   │   └── workflow.py
│   ├── wallpaper/          # Wallpaper management
│   │   ├── target.py
│   │   └── setters.py
│   └── history/            # History system
│       ├── manager.py
│       └── exceptions.py
├── tests/                  # Test suite
├── docs/                   # Documentation
├── config/                 # Default configurations
└── flake.nix              # Nix build configuration
```

## Code Style

### Python Style Guide

We follow PEP 8 with additional conventions:

#### Formatting

- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Use f-strings for string formatting
- Type hints required for all public functions/methods

```python
# Good
def generate_wallpaper(config: Config, monitor_index: int) -> Path:
    """Generate wallpaper for specific monitor."""
    output_path = config.monitors.get_output_path(monitor_index)
    return output_path

# Bad
def generateWallpaper(config, monitor_index):
    return config.monitors.get_output_path(monitor_index)
```

#### Documentation

All public modules, classes, and functions must have docstrings:

```python
class WallpaperGenerator:
    """
    Generates wallpapers using ComfyUI.
    
    Attributes:
        config: Configuration object
        client: ComfyUI client instance
    """
    
    def generate(self, prompt: str, workflow: Dict[str, Any]) -> GenerationResult:
        """
        Generate wallpaper from prompt and workflow.
        
        Args:
            prompt: Text prompt for generation
            workflow: ComfyUI workflow dictionary
            
        Returns:
            GenerationResult with image data and metadata
            
        Raises:
            GenerationError: If generation fails
        """
        pass
```

#### Error Handling

Use specific exception types and include helpful error messages:

```python
# Good
try:
    result = client.generate(workflow, prompt)
except ComfyConnectionError as e:
    logger.error(f"Failed to connect to ComfyUI: {e}")
    raise GenerationError(f"ComfyUI unavailable: {e}") from e

# Bad
try:
    result = client.generate(workflow, prompt)
except:
    print("Error")
    raise
```

#### Logging

Use structured logging with appropriate levels:

```python
import logging

logger = logging.getLogger(__name__)

def process_workflow(workflow: Dict[str, Any]) -> None:
    logger.info("Processing workflow with %d nodes", len(workflow))
    
    for node_id, node in workflow.items():
        logger.debug("Processing node %s: %s", node_id, node.get('class_type'))
    
    logger.warning("Workflow contains no prompt field")
```

### Naming Conventions

- **Classes**: PascalCase (e.g., `WallpaperTarget`)
- **Functions/Methods**: snake_case (e.g., `generate_wallpaper`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_TIMEOUT`)
- **Private members**: Prefix with underscore (e.g., `_validate_config`)

### Import Organization

```python
# Standard library imports
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Third-party imports
import requests
from dataclasses import dataclass

# Local imports
from ..config import Config
from ..exceptions import GenerationError
from .client import ComfyClient
```

## Testing

### Test Structure

Tests are organized by module in the `tests/` directory:

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_config.py           # Configuration tests
├── test_client.py           # ComfyUI client tests
├── test_prompt_generator.py # Prompt generation tests
├── test_history.py          # History system tests
└── test_integration.py      # End-to-end tests
```

### Writing Tests

#### Unit Tests

Test individual functions and classes in isolation:

```python
import pytest
from unittest.mock import Mock, patch

from darkwall_comfyui.config import Config, ComfyUIConfig

class TestConfig:
    def test_load_default_config(self):
        """Test loading default configuration."""
        config = Config.load()
        assert config.comfyui.base_url == "https://comfyui.home.arpa"
        assert config.monitors.count == 3
    
    def test_environment_variable_override(self):
        """Test environment variable overrides."""
        with patch.dict('os.environ', {'DARKWALL_COMFYUI_TIMEOUT': '600'}):
            config = Config.load()
            assert config.comfyui.timeout == 600
    
    def test_invalid_config_raises_error(self):
        """Test that invalid configuration raises ConfigError."""
        with pytest.raises(ConfigError):
            Config.load(Path("invalid.toml"))
```

#### Integration Tests

Test component interactions with mocked external dependencies:

```python
import pytest
from unittest.mock import Mock, patch

from darkwall_comfyui.commands.generate import generate_once
from darkwall_comfyui.config import Config

class TestGenerateIntegration:
    @patch('darkwall_comfyui.commands.generate.ComfyClient')
    @patch('darkwall_comfyui.commands.generate.PromptGenerator')
    def test_generate_once_success(self, mock_prompt_gen, mock_client):
        """Test successful wallpaper generation."""
        # Setup mocks
        mock_client_instance = mock_client.return_value
        mock_client_instance.health_check.return_value = True
        mock_client_instance.generate.return_value = Mock(
            prompt_id="test-id",
            filename="test.png",
            image_data=b"fake image"
        )
        
        # Run test
        config = Config()
        generate_once(config)
        
        # Verify calls
        mock_client_instance.health_check.assert_called_once()
        mock_client_instance.generate.assert_called_once()
```

#### Fixtures

Use fixtures for common test setup:

```python
# conftest.py
import pytest
from pathlib import Path
from darkwall_comfyui.config import Config

@pytest.fixture
def temp_config_dir(tmpdir):
    """Create temporary config directory."""
    config_dir = Path(tmpdir) / "config"
    config_dir.mkdir()
    return config_dir

@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return Config(
        comfyui=ComfyUIConfig(base_url="http://localhost:8188"),
        monitors=MonitorConfig(count=1)
    )
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=darkwall_comfyui --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run with verbose output
pytest -v

# Run integration tests only
pytest tests/test_integration.py -m integration
```

### Test Requirements

- All new features must include tests
- Maintain 90%+ code coverage
- Tests must be deterministic (no random failures)
- Use mocks for external dependencies (ComfyUI, filesystem)

## Submitting Changes

### Git Workflow

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/new-feature`
3. **Make** changes with descriptive commits
4. **Test** your changes thoroughly
5. **Push** to your fork: `git push origin feature/new-feature`
6. **Create** pull request

### Commit Messages

Use clear, descriptive commit messages:

```
# Good
feat(history): add wallpaper history and gallery system
fix(config): resolve environment variable override bug
docs(readme): update installation instructions

# Bad
fixed stuff
update
wip
```

Follow Conventional Commits format:
- `feat:`: New feature
- `fix:`: Bug fix
- `docs:`: Documentation changes
- `style:`: Code style changes
- `refactor:`: Code refactoring
- `test:`: Test additions/changes
- `chore:`: Maintenance tasks

### Pull Request Process

1. **Update** documentation if needed
2. **Add** tests for new functionality
3. **Ensure** all tests pass: `pytest`
4. **Run** code formatting: `black .`
5. **Check** type hints: `mypy .`
6. **Update** CHANGELOG.md if applicable

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

## Bug Reports

### Reporting Bugs

Use GitHub Issues with the following template:

```markdown
**Bug Description**
Clear description of the bug

**Steps to Reproduce**
1. Run command: `darkwall generate`
2. With config: [attach config file]
3. Error occurs: [describe error]

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: Linux/NixOS
- Python version: 3.11
- DarkWall version: latest
- ComfyUI version: latest

**Additional Context**
Logs, screenshots, or other relevant information
```

### Debug Information

Include debug output when reporting bugs:

```bash
# Enable verbose logging
darkwall --verbose generate > debug.log 2>&1

# Show configuration
darkwall status > config.txt

# Test ComfyUI connection
curl -v https://your-comfyui-url/system_stats
```

## Feature Requests

### Requesting Features

1. **Check** existing issues for duplicates
2. **Use** feature request template
3. **Provide** clear use case and motivation
4. **Consider** implementation complexity

### Feature Request Template

```markdown
**Feature Description**
Clear description of requested feature

**Use Case**
Why this feature is needed

**Proposed Solution**
How the feature should work

**Alternatives Considered**
Other approaches considered

**Additional Context**
Relevant information or examples
```

## Documentation

### Writing Documentation

- Use clear, concise language
- Include practical examples
- Update man page for CLI changes
- Add API docs for new modules
- Test examples and commands

### Documentation Structure

```
docs/
├── README.md           # Documentation overview
├── darkwall.1.md       # Man page source
├── troubleshooting.md  # Common issues
├── configuration.md    # Config reference
├── examples.md         # Usage examples
├── contributing.md     # This file
└── api/               # API documentation
    ├── README.md       # Architecture overview
    └── *.md           # Module documentation
```

### Building Documentation

```bash
# Generate man page
pandoc docs/darkwall.1.md -s -t man -o docs/darkwall.1

# View man page
man docs/darkwall.1
```

## Development Tools

### Code Quality

```bash
# Code formatting
black .

# Type checking
mypy .

# Linting
flake8 .

# Security scanning
bandit -r .
```

### Pre-commit Hooks

Set up pre-commit hooks for automated checks:

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Development Environment

Use Nix for reproducible development:

```nix
# flake.nix
devShells.default = pkgs.mkShell {
  packages = with pkgs; [
    python311
    python311Packages.black
    python311Packages.mypy
    python311Packages.pytest
    python311Packages.coverage
    pandoc  # For documentation
  ];
};
```

## Getting Help

### Communication

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Code Reviews**: Feedback on contributions

### Resources

- [Python Documentation](https://docs.python.org/)
- [ComfyUI Documentation](https://github.com/comfyanonymous/ComfyUI)
- [PEP 8 Style Guide](https://pep8.org/)
- [pytest Documentation](https://docs.pytest.org/)

Thank you for contributing to DarkWall ComfyUI! 🎨
