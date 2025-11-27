"""Integration tests for the complete wallpaper generation workflow."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from darkwall_comfyui.commands.generate import generate_once, generate_all
from darkwall_comfyui.comfy.client import ComfyClient, GenerationResult
from darkwall_comfyui.config import Config, StateManager


class TestEndToEndWorkflow:
    """Test the complete wallpaper generation workflow with mocked ComfyUI."""
    
    def test_generate_once_complete_workflow(self, test_config, test_workflow_json, tmp_path):
        """Test complete single monitor generation workflow."""
        # Setup config paths for testing
        test_config.comfyui.workflow_path = str(tmp_path / "workflow.json")
        test_config.monitors.output_pattern = str(tmp_path / "monitor_{index}.png")
        
        # Create workflow file
        workflow_file = Path(test_config.comfyui.workflow_path)
        workflow_file.write_text(test_workflow_json)
        
        # Mock ComfyClient responses
        mock_result = GenerationResult(
            prompt_id="test-prompt-123",
            filename="test_wallpaper.png",
            image_data=b"fake PNG image data for testing"
        )
        
        with patch('darkwall_comfyui.commands.generate.ComfyClient') as mock_client_class:
            mock_client = Mock()
            mock_client.health_check.return_value = True
            mock_client.generate.return_value = mock_result
            mock_client_class.return_value = mock_client
            
            # Mock wallpaper setter
            with patch('darkwall_comfyui.commands.generate.WallpaperTarget') as mock_target:
                mock_target_instance = Mock()
                mock_target.return_value = mock_target_instance
                mock_target_instance.save_wallpaper.return_value = tmp_path / "monitor_0.png"
                mock_target_instance.set_wallpaper.return_value = True
                
                # Execute generation
                generate_once(test_config, dry_run=False)
                
                # Verify workflow
                mock_client.health_check.assert_called_once()
                mock_client.generate.assert_called_once()
                mock_target_instance.save_wallpaper.assert_called_once()
                mock_target_instance.set_wallpaper.assert_called_once()
                
                # Verify state was updated
                state_mgr = StateManager(test_config)
                state = state_mgr.get_state()
                assert state['last_monitor_index'] == 0
                assert state['rotation_count'] == 1
    
    def test_generate_all_complete_workflow(self, test_config, test_workflow_json, tmp_path):
        """Test complete multi-monitor generation workflow."""
        # Setup config for 3 monitors
        test_config.monitors.count = 3
        test_config.comfyui.workflow_path = str(tmp_path / "workflow.json")
        test_config.monitors.output_pattern = str(tmp_path / "monitor_{index}.png")
        
        # Create workflow file
        workflow_file = Path(test_config.comfyui.workflow_path)
        workflow_file.write_text(test_workflow_json)
        
        # Mock ComfyClient responses
        mock_results = [
            GenerationResult(
                prompt_id=f"test-prompt-{i}",
                filename=f"test_wallpaper_{i}.png",
                image_data=f"fake PNG data for monitor {i}".encode()
            )
            for i in range(3)
        ]
        
        with patch('darkwall_comfyui.commands.generate.ComfyClient') as mock_client_class:
            mock_client = Mock()
            mock_client.health_check.return_value = True
            mock_client.generate.side_effect = mock_results
            mock_client_class.return_value = mock_client
            
            # Mock wallpaper target
            with patch('darkwall_comfyui.commands.generate.WallpaperTarget') as mock_target:
                mock_target_instance = Mock()
                mock_target.return_value = mock_target_instance
                mock_target_instance.save_wallpaper.return_value = tmp_path / "monitor_0.png"
                mock_target_instance.set_wallpaper.return_value = True
                
                # Execute generation for all monitors
                generate_all(test_config, dry_run=False)
                
                # Verify all monitors were processed
                assert mock_client.health_check.call_count == 1  # Only once for all
                assert mock_client.generate.call_count == 3
                assert mock_target_instance.save_wallpaper.call_count == 3
                assert mock_target_instance.set_wallpaper.call_count == 3
    
    def test_generate_once_with_comfyui_unreachable(self, test_config, test_workflow_json, tmp_path):
        """Test workflow when ComfyUI is unreachable."""
        test_config.comfyui.workflow_path = str(tmp_path / "workflow.json")
        test_config.monitors.output_pattern = str(tmp_path / "monitor_{index}.png")
        
        # Create workflow file first
        workflow_file = Path(test_config.comfyui.workflow_path)
        workflow_file.write_text(test_workflow_json)
        
        with patch('darkwall_comfyui.commands.generate.ComfyClient') as mock_client_class:
            mock_client = Mock()
            mock_client.health_check.return_value = False
            mock_client_class.return_value = mock_client
            
            # Should exit with error code 2
            with pytest.raises(SystemExit) as exc_info:
                generate_once(test_config, dry_run=False)
            
            assert exc_info.value.code == 2
            mock_client.health_check.assert_called_once()
            mock_client.generate.assert_not_called()
    
    def test_generate_once_with_workflow_error(self, test_config, tmp_path):
        """Test workflow when workflow loading fails."""
        test_config.comfyui.workflow_path = str(tmp_path / "nonexistent.json")
        test_config.monitors.output_pattern = str(tmp_path / "monitor_{index}.png")
        
        with patch('darkwall_comfyui.commands.generate.ComfyClient') as mock_client_class:
            mock_client = Mock()
            mock_client.health_check.return_value = True
            mock_client_class.return_value = mock_client
            
            # Should exit with error code 1 due to workflow error
            with pytest.raises(SystemExit) as exc_info:
                generate_once(test_config, dry_run=False)
            
            assert exc_info.value.code == 1
            # health_check should NOT be called since workflow loading fails first
            mock_client.health_check.assert_not_called()
            mock_client.generate.assert_not_called()
    
    def test_generate_once_rotation_persistence(self, test_config, test_workflow_json, tmp_path):
        """Test that rotation state persists across multiple generations."""
        # Setup config
        test_config.comfyui.workflow_path = str(tmp_path / "workflow.json")
        test_config.monitors.count = 3
        test_config.monitors.output_pattern = str(tmp_path / "monitor_{index}.png")
        
        # Create workflow file
        workflow_file = Path(test_config.comfyui.workflow_path)
        workflow_file.write_text(test_workflow_json)
        
        # Mock ComfyClient
        mock_result = GenerationResult(
            prompt_id="test-prompt-123",
            filename="test_wallpaper.png",
            image_data=b"fake PNG image data"
        )
        
        with patch('darkwall_comfyui.commands.generate.ComfyClient') as mock_client_class:
            mock_client = Mock()
            mock_client.health_check.return_value = True
            mock_client.generate.return_value = mock_result
            mock_client_class.return_value = mock_client
            
            # Mock wallpaper target
            with patch('darkwall_comfyui.commands.generate.WallpaperTarget') as mock_target:
                mock_target_instance = Mock()
                mock_target.return_value = mock_target_instance
                mock_target_instance.save_wallpaper.return_value = tmp_path / "monitor_0.png"
                mock_target_instance.set_wallpaper.return_value = True
                
                # First generation - should use monitor 0
                generate_once(test_config, dry_run=False)
                state_mgr = StateManager(test_config)
                state = state_mgr.get_state()
                assert state['last_monitor_index'] == 0
                assert state['rotation_count'] == 1
                
                # Second generation - should use monitor 1
                generate_once(test_config, dry_run=False)
                state = state_mgr.get_state()
                assert state['last_monitor_index'] == 1
                assert state['rotation_count'] == 2
                
                # Third generation - should use monitor 2
                generate_once(test_config, dry_run=False)
                state = state_mgr.get_state()
                assert state['last_monitor_index'] == 2
                assert state['rotation_count'] == 3
                
                # Fourth generation - should wrap back to monitor 0
                generate_once(test_config, dry_run=False)
                state = state_mgr.get_state()
                assert state['last_monitor_index'] == 0
                assert state['rotation_count'] == 4
    
    def test_dry_run_mode(self, test_config, test_workflow_json, tmp_path, capsys):
        """Test dry run mode doesn't make actual changes."""
        test_config.comfyui.workflow_path = str(tmp_path / "workflow.json")
        test_config.monitors.output_pattern = str(tmp_path / "monitor_{index}.png")
        
        # Create workflow file
        workflow_file = Path(test_config.comfyui.workflow_path)
        workflow_file.write_text(test_workflow_json)
        
        # Execute dry run
        generate_once(test_config, dry_run=True)
        
        # Capture output
        captured = capsys.readouterr()
        
        # Should show what would be done
        assert "DRY RUN: Would generate wallpaper for monitor 0" in captured.out
        assert "Output path:" in captured.out
        assert "ComfyUI URL:" in captured.out
        assert "Prompt:" in captured.out
        assert "DRY RUN: No actual changes made" in captured.out
        
        # State should not be updated
        state_mgr = StateManager(test_config)
        state = state_mgr.get_state()
        assert state['last_monitor_index'] == -1
        assert state['rotation_count'] == 0
    
    def test_generate_all_dry_run_mode(self, test_config, test_workflow_json, tmp_path, capsys):
        """Test dry run mode for generate-all command."""
        test_config.monitors.count = 3
        test_config.comfyui.workflow_path = str(tmp_path / "workflow.json")
        test_config.monitors.output_pattern = str(tmp_path / "monitor_{index}.png")
        
        # Create workflow file
        workflow_file = Path(test_config.comfyui.workflow_path)
        workflow_file.write_text(test_workflow_json)
        
        # Execute dry run
        generate_all(test_config, dry_run=True)
        
        # Capture output
        captured = capsys.readouterr()
        
        # Should show what would be done for all monitors
        assert "DRY RUN: Would generate wallpapers for all 3 monitors" in captured.out
        assert "Monitor 0:" in captured.out
        assert "Monitor 1:" in captured.out
        assert "Monitor 2:" in captured.out
        assert "DRY RUN: No actual changes made" in captured.out


class TestErrorScenarios:
    """Test error handling in the generation workflow."""
    
    def test_comfyui_generation_error(self, test_config, test_workflow_json, tmp_path):
        """Test handling of ComfyUI generation errors."""
        test_config.comfyui.workflow_path = str(tmp_path / "workflow.json")
        test_config.monitors.output_pattern = str(tmp_path / "monitor_{index}.png")
        
        # Create workflow file
        workflow_file = Path(test_config.comfyui.workflow_path)
        workflow_file.write_text(test_workflow_json)
        
        with patch('darkwall_comfyui.commands.generate.ComfyClient') as mock_client_class:
            mock_client = Mock()
            mock_client.health_check.return_value = True
            mock_client.generate.side_effect = Exception("ComfyUI generation failed")
            mock_client_class.return_value = mock_client
            
            # Should exit with error code 1
            with pytest.raises(SystemExit) as exc_info:
                generate_once(test_config, dry_run=False)
            
            assert exc_info.value.code == 1
    
    def test_wallpaper_save_error(self, test_config, test_workflow_json, tmp_path):
        """Test handling of wallpaper save errors."""
        test_config.comfyui.workflow_path = str(tmp_path / "workflow.json")
        test_config.monitors.output_pattern = str(tmp_path / "monitor_{index}.png")
        
        # Create workflow file
        workflow_file = Path(test_config.comfyui.workflow_path)
        workflow_file.write_text(test_workflow_json)
        
        mock_result = GenerationResult(
            prompt_id="test-prompt-123",
            filename="test_wallpaper.png",
            image_data=b"fake PNG image data"
        )
        
        with patch('darkwall_comfyui.commands.generate.ComfyClient') as mock_client_class:
            mock_client = Mock()
            mock_client.health_check.return_value = True
            mock_client.generate.return_value = mock_result
            mock_client_class.return_value = mock_client
            
            # Mock wallpaper target to fail on save
            with patch('darkwall_comfyui.commands.generate.WallpaperTarget') as mock_target:
                mock_target_instance = Mock()
                mock_target.return_value = mock_target_instance
                mock_target_instance.save_wallpaper.side_effect = RuntimeError("Disk full")
                
                # Should exit with error code 1
                with pytest.raises(SystemExit) as exc_info:
                    generate_once(test_config, dry_run=False)
                
                assert exc_info.value.code == 1
    
    def test_wallpaper_set_error_continues(self, test_config, test_workflow_json, tmp_path):
        """Test that wallpaper setting errors are logged but don't stop generation."""
        test_config.comfyui.workflow_path = str(tmp_path / "workflow.json")
        test_config.monitors.output_pattern = str(tmp_path / "monitor_{index}.png")
        
        # Create workflow file
        workflow_file = Path(test_config.comfyui.workflow_path)
        workflow_file.write_text(test_workflow_json)
        
        mock_result = GenerationResult(
            prompt_id="test-prompt-123",
            filename="test_wallpaper.png",
            image_data=b"fake PNG image data"
        )
        
        with patch('darkwall_comfyui.commands.generate.ComfyClient') as mock_client_class:
            mock_client = Mock()
            mock_client.health_check.return_value = True
            mock_client.generate.return_value = mock_result
            mock_client_class.return_value = mock_client
            
            # Mock wallpaper target to fail on set_wallpaper but succeed on save
            with patch('darkwall_comfyui.commands.generate.WallpaperTarget') as mock_target:
                mock_target_instance = Mock()
                mock_target.return_value = mock_target_instance
                mock_target_instance.save_wallpaper.return_value = tmp_path / "monitor_0.png"
                mock_target_instance.set_wallpaper.return_value = False  # Failed to set
                
                # Should complete successfully (exit code 0) despite wallpaper setting failure
                # This is expected behavior - the image is saved but setting fails
                generate_once(test_config, dry_run=False)  # Should not raise SystemExit
