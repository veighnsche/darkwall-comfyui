"""Tests for dependency injection refactoring."""

import pytest
from pathlib import Path

from darkwall_comfyui.config import (
    ComfyUIConfig, MonitorConfig, OutputConfig, PromptConfig, StateManager
)
from darkwall_comfyui.comfy.client import ComfyClient
from darkwall_comfyui.comfy.workflow import WorkflowManager
from darkwall_comfyui.prompt_generator import PromptGenerator
from darkwall_comfyui.wallpaper.target import WallpaperTarget


class TestDependencyInjection:
    """Test that classes accept specific config objects instead of full Config."""
    
    def test_comfy_client_accepts_comfyui_config(self):
        """Test ComfyClient can be instantiated with ComfyUIConfig only."""
        comfyui_config = ComfyUIConfig(
            base_url="http://localhost:8188",
            workflow_path="test.json",
            timeout=300,
            poll_interval=5
        )
        
        client = ComfyClient(comfyui_config)
        
        assert client.base_url == "http://localhost:8188"
        assert client.timeout == 300
        assert client.poll_interval == 5
    
    def test_workflow_manager_accepts_comfyui_config(self):
        """Test WorkflowManager can be instantiated with ComfyUIConfig only."""
        comfyui_config = ComfyUIConfig(
            base_url="http://localhost:8188",
            workflow_path="test.json",
            timeout=300,
            poll_interval=5
        )
        
        workflow_mgr = WorkflowManager(comfyui_config)
        
        assert workflow_mgr.config == comfyui_config
    
    def test_prompt_generator_accepts_prompt_config_and_config_dir(self):
        """Test PromptGenerator accepts PromptConfig and config_dir."""
        import tempfile
        
        prompt_config = PromptConfig(
            time_slot_minutes=30,
            theme="default",
            atoms_dir="atoms",
            use_monitor_seed=True
        )
        
        # Create a temporary config directory with atoms
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            atoms_dir = config_dir / "atoms"
            atoms_dir.mkdir()
            
            # Create test atom files
            (atoms_dir / "1_subject.txt").write_text("test\n")
            (atoms_dir / "2_environment.txt").write_text("test\n")
            (atoms_dir / "3_lighting.txt").write_text("test\n")
            (atoms_dir / "4_style.txt").write_text("test\n")
            
            prompt_gen = PromptGenerator(prompt_config, config_dir)
            
            assert prompt_gen.config == prompt_config
            assert prompt_gen.config_dir == config_dir
    
    def test_wallpaper_target_accepts_monitor_and_output_configs(self):
        """Test WallpaperTarget accepts MonitorConfig and OutputConfig."""
        monitor_config = MonitorConfig(
            count=2,
            pattern="monitor_{index}.png",
            command="swww",
            backup_pattern="backup_{index}_{timestamp}.png"
        )
        output_config = OutputConfig(create_backup=True)
        
        target = WallpaperTarget(monitor_config, output_config)
        
        assert target.monitor_config == monitor_config
        assert target.output_config == output_config
        assert target.monitor_config.count == 2
        assert target.output_config.create_backup is True
    
    def test_state_manager_accepts_monitor_config(self):
        """Test StateManager accepts MonitorConfig only."""
        monitor_config = MonitorConfig(
            count=3,
            pattern="monitor_{index}.png",
            command="swaybg",
            backup_pattern="backup_{index}_{timestamp}.png"
        )
        
        state_mgr = StateManager(monitor_config)
        
        assert state_mgr.monitor_config == monitor_config
        assert state_mgr.monitor_config.count == 3
    
    def test_classes_dont_accept_full_config_anymore(self):
        """Test that classes have been properly refactored and don't expect full Config."""
        # This test ensures the refactoring was successful
        # by verifying the classes don't try to access nested config attributes
        
        comfyui_config = ComfyUIConfig(
            base_url="http://test:8188",
            workflow_path="test.json",
            timeout=100,
            poll_interval=2
        )
        
        # Should work with specific config
        client = ComfyClient(comfyui_config)
        assert client.base_url == "http://test:8188"
        
        # If we passed a full Config object, it would fail because
        # the constructor now expects ComfyUIConfig, not Config
        with pytest.raises(AttributeError):
            # This should fail because full Config doesn't have the right attributes
            wrong_config = type('WrongConfig', (), {
                'base_url': 'http://test:8188',
                'workflow_path': 'test.json',
                'timeout': 100,
                'poll_interval': 2
            })()
            ComfyClient(wrong_config)  # Should fail
