"""Tests for consolidated duplicate logic after refactoring."""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from darkwall_comfyui.config import MonitorsConfig, PerMonitorConfig, OutputConfig
# TEAM_006: MonitorConfig deleted - using MonitorsConfig
from darkwall_comfyui.wallpaper.setters import (
    WallpaperSetter, SwwwSetter, SwaybgSetter, FehSetter, get_setter
)


class TestConsolidatedCommandExecution:
    """Test that _run_command method consolidation works correctly."""
    
    def test_base_class_has_run_command_method(self):
        """Test that base WallpaperSetter class has the consolidated _run_command method."""
        # Use a concrete implementation since WallpaperSetter is abstract
        setter = FehSetter()
        
        # Should have the consolidated method
        assert hasattr(setter, '_run_command')
        assert callable(getattr(setter, '_run_command'))
    
    def test_run_command_background_parameter(self):
        """Test that _run_command accepts background parameter."""
        setter = FehSetter()
        
        # Mock subprocess to test background behavior
        with patch('subprocess.Popen') as mock_popen, \
             patch('time.sleep') as mock_sleep:
            
            mock_process = Mock()
            mock_process.poll.return_value = None  # Still running
            mock_popen.return_value = mock_process
            
            # Test background command
            result = setter._run_command(['echo', 'test'], background=True)
            
            assert result is True
            mock_popen.assert_called_once()
            mock_sleep.assert_called_once_with(0.5)
    
    def test_run_command_non_background(self):
        """Test that _run_command works in non-background mode."""
        setter = FehSetter()
        
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            result = setter._run_command(['echo', 'test'], background=False)
            
            assert result is True
            mock_run.assert_called_once()
    
    def test_run_command_timeout_handling(self):
        """Test that _run_command handles timeouts properly."""
        setter = FehSetter()
        
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('cmd', 30)):
            result = setter._run_command(['sleep', '60'])
            assert result is False
    
    def test_run_command_file_not_found(self):
        """Test that _run_command handles command not found properly."""
        setter = FehSetter()
        
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            result = setter._run_command(['nonexistent_command'])
            assert result is False


class TestConsolidatedMonitorNameGeneration:
    """Test that _default_monitor_name method consolidation works correctly."""
    
    def test_base_class_has_default_monitor_name(self):
        """Test that base WallpaperSetter class has _default_monitor_name method."""
        setter = FehSetter()
        
        assert hasattr(setter, '_default_monitor_name')
        assert callable(getattr(setter, '_default_monitor_name'))
    
    def test_default_monitor_name_values(self):
        """Test that _default_monitor_name returns expected values."""
        setter = FehSetter()
        
        # Test known indices
        assert setter._default_monitor_name(0) == "eDP-1"
        assert setter._default_monitor_name(1) == "DP-1"
        assert setter._default_monitor_name(2) == "DP-2"
        assert setter._default_monitor_name(3) == "HDMI-A-1"
        assert setter._default_monitor_name(4) == "HDMI-A-2"
        
        # Test out of range indices
        assert setter._default_monitor_name(10) == "DP-10"
        assert setter._default_monitor_name(100) == "DP-100"
    
    def test_setters_use_consolidated_method(self):
        """Test that all setter classes use the consolidated _default_monitor_name."""
        setters = [SwwwSetter(), SwaybgSetter(), FehSetter()]
        
        for setter in setters:
            # All should return the same values since they use the base class method
            assert setter._default_monitor_name(0) == "eDP-1"
            assert setter._default_monitor_name(1) == "DP-1"


class TestSwaybgSetterBackgroundHandling:
    """Test that SwaybgSetter properly uses background mode."""
    
    def test_swaybg_uses_background_mode(self):
        """Test that SwaybgSetter calls _run_command with background=True."""
        setter = SwaybgSetter()
        
        # TEAM_003: Mock Path.exists() to allow fake image path
        with patch.object(setter, '_run_command', return_value=True) as mock_run, \
             patch('pathlib.Path.exists', return_value=True):
            result = setter.set(Path("/fake/image.png"), 0, "eDP-1")
            
            assert result is True
            mock_run.assert_called_once()
            # Check that background=True was passed
            call_args = mock_run.call_args
            assert call_args[1]['background'] is True
    
    def test_swaybg_kills_existing_processes(self):
        """Test that SwaybgSetter kills existing swaybg processes."""
        setter = SwaybgSetter()
        
        # TEAM_003: Mock Path.exists() to allow fake image path
        with patch.object(setter, '_kill_existing_swaybg') as mock_kill, \
             patch.object(setter, '_run_command', return_value=True), \
             patch('pathlib.Path.exists', return_value=True):
            
            setter.set(Path("/fake/image.png"), 0, "eDP-1")
            
            mock_kill.assert_called_once_with("eDP-1")


class TestSwwwSetterForegroundHandling:
    """Test that SwwwSetter properly uses foreground mode."""
    
    def test_swww_uses_foreground_mode(self):
        """Test that SwwwSetter calls _run_command with background=False."""
        setter = SwwwSetter()
        
        with patch.object(setter, '_run_command', return_value=True) as mock_run:
            result = setter.set(Path("/fake/image.png"), 0, "eDP-1")
            
            assert result is True
            mock_run.assert_called_once()
            # Check that background=False (default) was used
            call_args = mock_run.call_args
            # Check if background parameter was passed (it should be False or not passed at all)
            assert 'background' not in call_args[1] or call_args[1]['background'] is False


class TestNoDuplicateMethods:
    """Test that duplicate methods have been properly removed."""
    
    def test_no_duplicate_run_background_command(self):
        """Test that setters don't have separate _run_background_command methods."""
        setters = [SwwwSetter(), SwaybgSetter(), FehSetter()]
        
        for setter in setters:
            # Should not have the old duplicate method
            assert not hasattr(setter, '_run_background_command')
    
    def test_no_duplicate_default_monitor_name_in_setters(self):
        """Test that individual setters don't have their own _default_monitor_name."""
        setters = [SwwwSetter(), SwaybgSetter(), FehSetter()]
        
        for setter in setters:
            # The method should be on the base class, not the subclass
            method = getattr(setter, '_default_monitor_name')
            # Method should be defined in WallpaperSetter, not the subclass
            assert method.__qualname__.startswith('WallpaperSetter')


class TestWallpaperTargetConsolidation:
    """Test that WallpaperTarget properly uses injected configs."""
    
    def test_wallpaper_target_uses_injected_configs(self):
        """Test that WallpaperTarget uses injected MonitorsConfig and OutputConfig."""
        # TEAM_006: Use MonitorsConfig instead of MonitorConfig
        monitors_config = MonitorsConfig(
            monitors={
                "DP-1": PerMonitorConfig(name="DP-1", workflow="default"),
                "HDMI-A-1": PerMonitorConfig(name="HDMI-A-1", workflow="default"),
            },
            command="swww"
        )
        output_config = OutputConfig(create_backup=True)
        
        from darkwall_comfyui.wallpaper.target import WallpaperTarget
        target = WallpaperTarget(monitors_config, output_config)
        
        # Should use injected configs, not a full Config object
        assert target.monitors_config == monitors_config
        assert target.output_config == output_config
        assert len(target.monitors_config) == 2
        assert target.output_config.create_backup is True
