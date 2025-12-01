"""Test configuration and fixtures.

TEAM_006: Updated to use Config with per-monitor format (ConfigV2 merged).
"""

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from darkwall_comfyui.config import (
    Config,
    ComfyUIConfig,
    PromptConfig,
    MonitorsConfig,
    PerMonitorConfig,
)
# TEAM_006: ConfigV2 deleted - merged into Config
# TEAM_007: OutputConfig removed - no longer exists


@pytest.fixture
def temp_config_dir() -> Generator[Path, None, None]:
    """Create a temporary config directory with test files using theme structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        
        # Create theme structure: themes/default/atoms/ and themes/default/prompts/
        theme_dir = config_dir / "themes" / "default"
        atoms_dir = theme_dir / "atoms"
        prompts_dir = theme_dir / "prompts"
        atoms_dir.mkdir(parents=True)
        prompts_dir.mkdir(parents=True)
        
        # Create test atom files
        (atoms_dir / "subject.txt").write_text("mountain\nocean\nforest\n")
        (atoms_dir / "environment.txt").write_text("misty\nsunset\nnight\n")
        (atoms_dir / "lighting.txt").write_text("soft light\ndramatic\nambient\n")
        (atoms_dir / "style.txt").write_text("photorealistic\nartistic\nminimalist\n")
        
        # Create default template
        (prompts_dir / "default.prompt").write_text(
            "__subject__, __environment__, __lighting__, __style__, "
            "dark mode friendly, high quality\n\n"
            "$$negative$$\n"
            "blurry, low quality\n"
        )
        
        # Create workflows directory with test workflow
        workflows_dir = config_dir / "workflows"
        workflows_dir.mkdir()
        (workflows_dir / "default.json").write_text('{"1": {"class_type": "Test"}}')
        
        # Create test config file with theme configuration
        config_file = config_dir / "config.toml"
        config_file.write_text("""
[comfyui]
base_url = "http://localhost:8188"
workflow_path = "test_workflow.json"
timeout = 300
poll_interval = 2

[monitors.DP-1]
workflow = "default"
output = "~/Pictures/wallpapers/DP-1.png"

[monitors.HDMI-A-1]
workflow = "default"
output = "~/Pictures/wallpapers/HDMI-A-1.png"

[prompt]
theme = "default"
time_slot_minutes = 60

[logging]
level = "INFO"

[themes.default]
atoms_dir = "atoms"
prompts_dir = "prompts"
default_template = "default.prompt"
""")
        
        yield config_dir


@pytest.fixture
def test_config(temp_config_dir: Path) -> Config:
    """Create a test Config instance with isolated state."""
    config_file = temp_config_dir / "config.toml"
    
    # Temporarily patch the config directory method
    original_get_config_dir = Config.get_config_dir
    Config.get_config_dir = classmethod(lambda cls: temp_config_dir)
    
    try:
        # TEAM_006: Use Config.load with monitor detection disabled for tests
        config = Config.load(config_file=config_file, initialize=False, detect_monitors=False)
        yield config
    finally:
        # Restore original method
        Config.get_config_dir = original_get_config_dir


@pytest.fixture
def comfyui_config(test_config: Config) -> ComfyUIConfig:
    """Extract ComfyUIConfig from test config."""
    return test_config.comfyui


@pytest.fixture
def monitors_config(test_config: Config) -> MonitorsConfig:
    """Extract MonitorsConfig from test config."""
    return test_config.monitors


@pytest.fixture
def prompt_config(test_config: Config) -> PromptConfig:
    """Extract PromptConfig from test config."""
    return test_config.prompt


@pytest.fixture
def config_dir(temp_config_dir: Path) -> Path:
    """Get the config directory path for tests."""
    return temp_config_dir


@pytest.fixture
def prompt_generator(test_config: Config):
    """Create a PromptGenerator using the factory method."""
    from darkwall_comfyui.prompt_generator import PromptGenerator
    return PromptGenerator.from_config(test_config)


@pytest.fixture
def test_workflow_json() -> str:
    """Test workflow JSON content."""
    return """
{
    "1": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "test prompt",
            "clip": ["2", 0]
        }
    },
    "2": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "test_model.safetensors"
        }
    },
    "3": {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "test",
            "images": ["4", 0]
        }
    }
}
"""
