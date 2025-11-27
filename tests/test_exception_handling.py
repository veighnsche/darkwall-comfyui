"""Tests for improved exception handling after refactoring."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from darkwall_comfyui.config import Config, StateManager, ConfigError
from darkwall_comfyui.exceptions import (
    DarkWallError, PromptError, CommandError, WorkflowError, GenerationError
)
from darkwall_comfyui.prompt_generator import PromptGenerator
from darkwall_comfyui.wallpaper.setters import CustomSetter


class TestSpecificExceptionHandling:
    """Test that specific exceptions are raised instead of generic ones."""
    
    def test_config_validation_raises_config_error(self, temp_config_dir):
        """Test that config validation raises ConfigError with specific messages."""
        # Create invalid config file
        config_file = temp_config_dir / "config.toml"
        config_file.write_text("""
[comfyui]
base_url = "invalid-url"
timeout = -1
poll_interval = 0

[monitors]
count = 0
command = "invalid-command"
pattern = "no-index-placeholder"

[output]
create_backup = true

[prompt]
time_slot_minutes = 2000
atoms_dir = "atoms"

[logging]
level = "INVALID"
""")
        
        with pytest.raises(ConfigError) as exc_info:
            Config.load(config_file=config_file, initialize=False)
        
        # Should catch the first validation error
        assert "Invalid base URL format" in str(exc_info.value)
    
    def test_state_manager_specific_exceptions(self):
        """Test StateManager handles specific exceptions properly."""
        import tempfile
        
        # Use a temporary state file to ensure isolation
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "test_state.json"
            
            monitor_config = type('MonitorConfig', (), {'count': 2})()
            state_mgr = StateManager(monitor_config)
            state_mgr.state_file = state_file
            
            # Test with non-existent state file
            state = state_mgr.get_state()
            assert state == {'last_monitor_index': -1, 'rotation_count': 0}
            
            # Test with corrupted JSON state file
            state_file.write_text("invalid json content")
            state = state_mgr.get_state()  # Should handle gracefully
            assert state == {'last_monitor_index': -1, 'rotation_count': 0}
    
    def test_prompt_generator_specific_exceptions(self, temp_config_dir):
        """Test PromptGenerator handles missing files gracefully."""
        import tempfile
        
        prompt_config = type('PromptConfig', (), {
            'time_slot_minutes': 30,
            'theme': 'default',
            'atoms_dir': 'atoms',
            'use_monitor_seed': True,
            'default_template': 'default.prompt'
        })()
        
        # New behavior: missing atoms directory doesn't raise - uses fallback template
        prompt_gen = PromptGenerator(prompt_config, temp_config_dir / "nonexistent")
        
        # Missing wildcard returns empty list
        atoms = prompt_gen._load_atom_file("nonexistent")
        assert atoms == []
        
        # Template resolution marks missing wildcards
        result = prompt_gen._resolve_template("test __missing__ end", seed=42)
        assert "[missing:missing]" in result
    
    def test_custom_setter_specific_exceptions(self):
        """Test CustomSetter handles specific exceptions properly."""
        # Test invalid template
        setter = CustomSetter("invalid template with {unknown_placeholder}")
        
        result = setter.set(Path("/fake/path.jpg"), 0, "test-monitor")
        assert result is False  # Should fail gracefully
    
    def test_exception_hierarchy(self):
        """Test that all custom exceptions inherit from DarkWallError."""
        assert issubclass(ConfigError, DarkWallError)
        assert issubclass(PromptError, DarkWallError)
        assert issubclass(CommandError, DarkWallError)
        assert issubclass(WorkflowError, DarkWallError)
        assert issubclass(GenerationError, DarkWallError)
    
    def test_no_silent_failures(self, caplog):
        """Test that exceptions are properly logged and not silently ignored."""
        # This test ensures we don't have bare except: pass blocks
        # that would hide errors
        
        monitor_config = type('MonitorConfig', (), {'count': 1})()
        state_mgr = StateManager(monitor_config)
        
        # Try to save to a read-only directory
        with tempfile.TemporaryDirectory() as temp_dir:
            readonly_dir = Path(temp_dir)
            readonly_dir.chmod(0o444)  # Read-only
            
            state_file = readonly_dir / "state.json"
            state_mgr.state_file = state_file
            
            # Should log the error, not raise it (graceful degradation)
            state_mgr.save_state({'test': 'data'})
            
            # Verify error was logged
            assert "Failed to save state file" in caplog.text
            assert "Permission denied" in caplog.text
            
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)


class TestConfigValidationExceptions:
    """Test configuration validation with specific error types."""
    
    def test_url_validation(self, temp_config_dir):
        """Test URL validation raises specific errors."""
        config_file = temp_config_dir / "config.toml"
        
        # Test various invalid URLs
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "http://",
            "https://",
            ""
        ]
        
        for invalid_url in invalid_urls:
            config_file.write_text(f"""
[comfyui]
base_url = "{invalid_url}"
workflow_path = "test.json"
timeout = 300
poll_interval = 5

[monitors]
count = 1
command = "swww"
pattern = "monitor_{{index}}.png"

[output]
create_backup = false

[prompt]
time_slot_minutes = 30
atoms_dir = "atoms"

[logging]
level = "INFO"
""")
            
            with pytest.raises(ConfigError) as exc_info:
                Config.load(config_file=config_file, initialize=False)
            
            assert "Invalid base URL format" in str(exc_info.value)
    
    def test_range_validation(self, temp_config_dir):
        """Test range validation for numeric values."""
        config_file = temp_config_dir / "config.toml"
        
        # Test timeout out of range
        config_file.write_text("""
[comfyui]
base_url = "http://localhost:8188"
workflow_path = "test.json"
timeout = 5000
poll_interval = 5

[monitors]
count = 1
command = "swww"
pattern = "monitor_{index}.png"

[output]
create_backup = false

[prompt]
time_slot_minutes = 30
atoms_dir = "atoms"

[logging]
level = "INFO"
""")
        
        with pytest.raises(ConfigError) as exc_info:
            Config.load(config_file=config_file, initialize=False)
        
        assert "between 1 and 3600 seconds" in str(exc_info.value)
    
    def test_placeholder_validation(self, temp_config_dir):
        """Test placeholder validation in path patterns."""
        config_file = temp_config_dir / "config.toml"
        
        config_file.write_text("""
[comfyui]
base_url = "http://localhost:8188"
workflow_path = "test.json"
timeout = 300
poll_interval = 5

[monitors]
count = 1
command = "swww"
pattern = "monitor.png"
backup_pattern = "backup.png"

[output]
create_backup = false

[prompt]
time_slot_minutes = 30
atoms_dir = "atoms"

[logging]
level = "INFO"
""")
        
        with pytest.raises(ConfigError) as exc_info:
            Config.load(config_file=config_file, initialize=False)
        
        assert "must contain {index} placeholder" in str(exc_info.value)
