"""Tests for the template-based prompt generator."""

import pytest
from darkwall_comfyui.prompt_generator import PromptGenerator, PromptResult


def test_prompt_generator_initialization(prompt_config, config_dir):
    """Test that PromptGenerator initializes correctly."""
    gen = PromptGenerator(prompt_config, config_dir)
    
    assert gen.config == prompt_config
    assert gen.config_dir == config_dir
    
    # Test atom loading via internal method
    subject_atoms = gen._load_atom_file("subject")
    assert len(subject_atoms) > 0
    assert "mountain" in subject_atoms
    
    environment_atoms = gen._load_atom_file("environment")
    assert "misty" in environment_atoms


def test_time_slot_seed_generation(prompt_config, config_dir):
    """Test deterministic seed generation."""
    gen = PromptGenerator(prompt_config, config_dir)
    
    # Test seed generation is deterministic
    seed1 = gen.get_time_slot_seed()
    seed2 = gen.get_time_slot_seed()
    assert seed1 == seed2
    
    # Test monitor variation
    seed_monitor_0 = gen.get_time_slot_seed(monitor_index=0)
    seed_monitor_1 = gen.get_time_slot_seed(monitor_index=1)
    assert seed_monitor_0 != seed_monitor_1


def test_atom_selection(prompt_config, config_dir):
    """Test atom selection based on seed."""
    gen = PromptGenerator(prompt_config, config_dir)
    
    atoms = ["mountain", "ocean", "forest"]
    
    # Test deterministic selection
    selected1 = gen._select_from_list(atoms, 42, 0)
    selected2 = gen._select_from_list(atoms, 42, 0)
    assert selected1 == selected2
    
    # Test variation index changes selection
    selected_var_0 = gen._select_from_list(atoms, 42, 0)
    selected_var_1 = gen._select_from_list(atoms, 42, 1)
    assert selected_var_0 != selected_var_1
    
    # Test empty atoms list returns empty string
    empty_selected = gen._select_from_list([], 42, 0)
    assert empty_selected == ""


def test_wildcard_resolution(prompt_config, config_dir):
    """Test __wildcard__ syntax resolution."""
    gen = PromptGenerator(prompt_config, config_dir)
    
    # Test loading atom file
    atoms = gen._load_atom_file("subject")
    assert len(atoms) > 0
    assert "mountain" in atoms
    
    # Test caching
    atoms2 = gen._load_atom_file("subject")
    assert atoms is atoms2  # Same object from cache


def test_variant_resolution(prompt_config, config_dir):
    """Test {variant|syntax} resolution."""
    gen = PromptGenerator(prompt_config, config_dir)
    
    # Test parsing weighted options
    options = gen._parse_weighted_options("0.5::rare|2::common|normal")
    assert len(options) == 3
    assert options[0] == (0.5, "rare")
    assert options[1] == (2.0, "common")
    assert options[2] == (1.0, "normal")


def test_template_resolution(prompt_config, config_dir):
    """Test full template resolution."""
    gen = PromptGenerator(prompt_config, config_dir)
    
    # Simple variant
    result = gen._resolve_template("{red|blue|green}", seed=42)
    assert result in ["red", "blue", "green"]
    
    # Deterministic
    result2 = gen._resolve_template("{red|blue|green}", seed=42)
    assert result == result2


def test_template_sections(prompt_config, config_dir):
    """Test parsing positive/negative sections."""
    gen = PromptGenerator(prompt_config, config_dir)
    
    template = """
    # Comment line
    positive prompt here
    
    ---negative---
    negative prompt here
    """
    
    positive, negative = gen._parse_template_sections(template)
    assert "positive prompt here" in positive
    assert "negative prompt here" in negative
    assert "Comment" not in positive


def test_prompt_pair_generation(prompt_config, config_dir):
    """Test generate_prompt_pair returns both prompts."""
    gen = PromptGenerator(prompt_config, config_dir)
    
    result = gen.generate_prompt_pair(monitor_index=0)
    
    assert isinstance(result, PromptResult)
    assert isinstance(result.positive, str)
    assert isinstance(result.negative, str)
    assert len(result.positive) > 10


def test_full_prompt_generation(prompt_config, config_dir):
    """Test complete prompt generation workflow."""
    gen = PromptGenerator(prompt_config, config_dir)
    
    prompt = gen.generate_prompt(monitor_index=0)
    
    assert isinstance(prompt, str)
    assert len(prompt) > 10
    
    # Test deterministic generation
    prompt2 = gen.generate_prompt(monitor_index=0)
    assert prompt == prompt2
    
    # TEAM_003: Monitor variation test removed - with small test atom files,
    # different monitors may produce identical prompts due to limited variation.
    # The seeding mechanism is tested in test_time_slot_seed_generation.


def test_missing_template_error(prompt_config, config_dir):
    """Test error when template file is missing."""
    from darkwall_comfyui.exceptions import PromptError
    
    gen = PromptGenerator(prompt_config, config_dir)
    
    # Should raise PromptError when template doesn't exist
    with pytest.raises(PromptError, match="Template not found"):
        gen._load_template("nonexistent.prompt")


def test_missing_wildcard_handling(prompt_config, config_dir):
    """Test graceful handling of missing wildcard files."""
    gen = PromptGenerator(prompt_config, config_dir)
    
    # Missing file returns empty list
    atoms = gen._load_atom_file("nonexistent/file")
    assert atoms == []
    
    # Template with missing wildcard marks it
    result = gen._resolve_template("test __nonexistent__ end", seed=42)
    assert "[missing:nonexistent]" in result
