"""Tests for dependency injection refactoring.

TEAM_006: Updated to use MonitorsConfig instead of MonitorConfig.
"""

import pytest
from pathlib import Path

from darkwall_comfyui.config import (
    ComfyUIConfig, MonitorsConfig, PerMonitorConfig, PromptConfig, NamedStateManager
)
# TEAM_007: OutputConfig removed - no longer exists
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
    
    def test_prompt_generator_requires_explicit_paths(self):
        """Test PromptGenerator requires atoms_dir and prompts_dir."""
        import tempfile
        from darkwall_comfyui.exceptions import PromptError
        
        prompt_config = PromptConfig(
            time_slot_minutes=30,
            theme="default",
            use_monitor_seed=True
        )
        
        # Create a temporary config directory with theme structure
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            atoms_dir = config_dir / "themes" / "default" / "atoms"
            prompts_dir = config_dir / "themes" / "default" / "prompts"
            atoms_dir.mkdir(parents=True)
            prompts_dir.mkdir(parents=True)
            
            # Create test atom files
            (atoms_dir / "subject.txt").write_text("test\n")
            
            # Create test prompt template
            (prompts_dir / "default.prompt").write_text("Test __subject__\n")
            
            # Direct construction requires explicit paths
            prompt_gen = PromptGenerator(prompt_config, config_dir, atoms_dir=atoms_dir, prompts_dir=prompts_dir)
            
            assert prompt_gen.config == prompt_config
            assert prompt_gen.config_dir == config_dir
            assert prompt_gen._atoms_dir == atoms_dir
            assert prompt_gen._prompts_dir == prompts_dir
            
            # Without paths, should raise error
            with pytest.raises(Exception) as exc_info:
                PromptGenerator(prompt_config, config_dir)
            assert "atoms_dir and prompts_dir are required" in str(exc_info.value)
    
    def test_wallpaper_target_accepts_monitors_config(self):
        """Test WallpaperTarget accepts MonitorsConfig."""
        # TEAM_006: Use MonitorsConfig instead of MonitorConfig
        # TEAM_007: OutputConfig removed - WallpaperTarget only needs MonitorsConfig
        monitors_config = MonitorsConfig(
            monitors={
                "DP-1": PerMonitorConfig(name="DP-1", workflow="default"),
                "HDMI-A-1": PerMonitorConfig(name="HDMI-A-1", workflow="default"),
            },
            command="swww"
        )
        
        target = WallpaperTarget(monitors_config)
        
        assert target.monitors_config == monitors_config
        assert len(target.monitors_config) == 2
    
    def test_named_state_manager_accepts_monitor_names(self):
        """Test NamedStateManager accepts list of monitor names."""
        # TEAM_007: Updated to use NamedStateManager (StateManager deleted)
        monitor_names = ["DP-1", "HDMI-A-1", "DP-2"]
        
        state_mgr = NamedStateManager(monitor_names)
        
        assert state_mgr.monitor_names == monitor_names
        assert len(state_mgr.monitor_names) == 3
    
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
