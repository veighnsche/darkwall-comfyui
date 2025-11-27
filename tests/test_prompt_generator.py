"""Tests for the prompt generator."""

import pytest
from darkwall_comfyui.prompt_generator import PromptGenerator


def test_prompt_generator_initialization(test_config):
    """Test that PromptGenerator initializes correctly."""
    gen = PromptGenerator(test_config)
    
    assert gen.config == test_config
    assert hasattr(gen, 'atoms')
    assert isinstance(gen.atoms, dict)
    
    # Check that atoms were loaded
    assert "subject" in gen.atoms
    assert "environment" in gen.atoms
    assert "lighting" in gen.atoms
    assert "style" in gen.atoms
    
    # Check atom content
    assert "mountain" in gen.atoms["subject"]
    assert "misty" in gen.atoms["environment"]
    assert "soft light" in gen.atoms["lighting"]
    assert "photorealistic" in gen.atoms["style"]


def test_time_slot_seed_generation(test_config):
    """Test deterministic seed generation."""
    gen = PromptGenerator(test_config)
    
    # Test seed generation is deterministic
    seed1 = gen.get_time_slot_seed()
    seed2 = gen.get_time_slot_seed()
    assert seed1 == seed2
    
    # Test monitor variation
    seed_monitor_0 = gen.get_time_slot_seed(monitor_index=0)
    seed_monitor_1 = gen.get_time_slot_seed(monitor_index=1)
    assert seed_monitor_0 != seed_monitor_1


def test_atom_selection(test_config):
    """Test atom selection with deterministic seeds."""
    gen = PromptGenerator(test_config)
    
    atoms = ["mountain", "ocean", "forest"]
    
    # Test deterministic selection
    selected1 = gen.select_atom(atoms, 42, 0)
    selected2 = gen.select_atom(atoms, 42, 0)
    assert selected1 == selected2
    
    # Test pillar variation
    selected_pillar_0 = gen.select_atom(atoms, 42, 0)
    selected_pillar_1 = gen.select_atom(atoms, 42, 1)
    # Should be different due to pillar seed variation
    assert selected_pillar_0 != selected_pillar_1
    
    # Test empty atoms list
    empty_selected = gen.select_atom([], 42, 0)
    assert empty_selected == "minimal dark wallpaper"


def test_pillar_generation(test_config):
    """Test prompt pillar generation."""
    gen = PromptGenerator(test_config)
    
    pillars = gen.generate_pillars(42)
    
    assert hasattr(pillars, 'subject')
    assert hasattr(pillars, 'environment')
    assert hasattr(pillars, 'lighting')
    assert hasattr(pillars, 'style')
    
    assert isinstance(pillars.subject, str)
    assert isinstance(pillars.environment, str)
    assert isinstance(pillars.lighting, str)
    assert isinstance(pillars.style, str)
    
    assert len(pillars.subject) > 0
    assert len(pillars.environment) > 0
    assert len(pillars.lighting) > 0
    assert len(pillars.style) > 0


def test_prompt_building(test_config):
    """Test final prompt building."""
    gen = PromptGenerator(test_config)
    
    from darkwall_comfyui.prompt_generator import PromptPillars
    
    pillars = PromptPillars(
        subject="mountain",
        environment="misty",
        lighting="soft light",
        style="photorealistic"
    )
    
    prompt = gen.build_prompt(pillars)
    
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "mountain" in prompt
    assert "misty" in prompt
    assert "soft light" in prompt
    assert "photorealistic" in prompt
    assert "dark mode friendly" in prompt


def test_full_prompt_generation(test_config):
    """Test complete prompt generation."""
    gen = PromptGenerator(test_config)
    
    prompt = gen.generate_prompt(monitor_index=0)
    
    assert isinstance(prompt, str)
    assert len(prompt) > 10
    assert "dark mode friendly" in prompt
    
    # Test deterministic generation
    prompt2 = gen.generate_prompt(monitor_index=0)
    assert prompt == prompt2
    
    # Test monitor variation
    prompt_monitor_1 = gen.generate_prompt(monitor_index=1)
    assert prompt != prompt_monitor_1


def test_missing_atoms_directory():
    """Test behavior when atoms directory is missing."""
    from darkwall_comfyui.config import Config
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        
        # Create config without atoms directory
        config_file = config_dir / "config.toml"
        config_file.write_text("""
[comfyui]
base_url = "http://localhost:8188"
workflow_path = "test_workflow.json"
timeout = 300
poll_interval = 2

[monitors]
count = 1
command = "swww"
pattern = "monitor_{index}.png"
backup_pattern = "monitor_{index}_{timestamp}.png"

[output]
directory = "~/wallpapers"
create_backup = true

[prompt]
atoms_dir = "atoms"
time_slot_minutes = 60

[logging]
level = "INFO"
""")
        
        config = Config.load(config_file=config_file, initialize=False)
        
        with pytest.raises(FileNotFoundError):
            PromptGenerator(config)
