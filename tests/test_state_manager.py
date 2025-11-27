"""Tests for the state manager."""

import json
import pytest
from pathlib import Path

from darkwall_comfyui.config import StateManager


def test_state_manager_initialization(monitor_config):
    """Test that StateManager initializes correctly."""
    mgr = StateManager(monitor_config)
    
    assert mgr.monitor_config == monitor_config
    assert hasattr(mgr, 'state_file')
    assert hasattr(mgr, 'logger')


def test_state_initialization(monitor_config):
    """Test state initialization when no state file exists."""
    import tempfile
    
    # Use a temporary state file to ensure isolation
    with tempfile.TemporaryDirectory() as temp_dir:
        state_file = Path(temp_dir) / "test_state.json"
        
        mgr = StateManager(monitor_config)
        mgr.state_file = state_file
        
        # Ensure state file doesn't exist
        if mgr.state_file.exists():
            mgr.state_file.unlink()
        
        state = mgr.get_state()
        
        assert isinstance(state, dict)
        assert state.get('last_monitor_index') == -1
        assert state.get('rotation_count') == 0


def test_state_persistence(monitor_config):
    """Test that state is saved and loaded correctly."""
    import tempfile
    
    # Use a temporary state file to ensure isolation
    with tempfile.TemporaryDirectory() as temp_dir:
        state_file = Path(temp_dir) / "test_state.json"
        
        mgr = StateManager(monitor_config)
        mgr.state_file = state_file
        
        # Save test state
        test_state = {'last_monitor_index': 2, 'rotation_count': 5}
        mgr.save_state(test_state)
        
        # Load state
        loaded_state = mgr.get_state()
        
        assert loaded_state['last_monitor_index'] == 2
        assert loaded_state['rotation_count'] == 5


def test_state_file_creation(monitor_config):
    """Test that state file is created when saving."""
    import tempfile
    
    # Use a temporary state file to ensure isolation
    with tempfile.TemporaryDirectory() as temp_dir:
        state_file = Path(temp_dir) / "test_state.json"
        
        mgr = StateManager(monitor_config)
        mgr.state_file = state_file
        
        # Ensure state file doesn't exist initially
        if mgr.state_file.exists():
            mgr.state_file.unlink()
        
        assert not mgr.state_file.exists()
        
        # Save state
        test_state = {'last_monitor_index': 0, 'rotation_count': 1}
        mgr.save_state(test_state)
        
        # File should now exist
        assert mgr.state_file.exists()
        
        # Verify content
        content = mgr.state_file.read_text()
        saved_data = json.loads(content)
        assert saved_data == test_state


def test_next_monitor_index_rotation(monitor_config):
    """Test monitor index rotation logic."""
    import tempfile
    
    # Use a temporary state file to ensure isolation
    with tempfile.TemporaryDirectory() as temp_dir:
        state_file = Path(temp_dir) / "test_state.json"
        
        # Create a monitor config with 2 monitors for testing
        test_monitor_config = type('MonitorConfig', (), {'count': 2})()
        
        mgr = StateManager(test_monitor_config)
        mgr.state_file = state_file
        
        # Reset state first
        mgr.reset_rotation()
        
        # First call should return 0 (from -1 initial state)
        next_idx = mgr.get_next_monitor_index()
        assert next_idx == 0
        
        # Second call should return 1
        next_idx = mgr.get_next_monitor_index()
        assert next_idx == 1


def test_rotation_count_increment(monitor_config):
    """Test rotation count increments correctly."""
    import tempfile
    
    # Use a temporary state file to ensure isolation
    with tempfile.TemporaryDirectory() as temp_dir:
        state_file = Path(temp_dir) / "test_state.json"
        
        mgr = StateManager(monitor_config)
        mgr.state_file = state_file
        
        # Start with clean state
        state = mgr.get_state()
        assert state['rotation_count'] == 0
        
        # Get next index multiple times
        mgr.get_next_monitor_index()
        mgr.get_next_monitor_index()
        mgr.get_next_monitor_index()
        
        # Check rotation count
        state = mgr.get_state()
        assert state['rotation_count'] == 3


def test_reset_rotation(monitor_config):
    """Test rotation state reset."""
    import tempfile
    
    # Use a temporary state file to ensure isolation
    with tempfile.TemporaryDirectory() as temp_dir:
        state_file = Path(temp_dir) / "test_state.json"
        
        mgr = StateManager(monitor_config)
        mgr.state_file = state_file
        
        # Set some state
        test_state = {'last_monitor_index': 3, 'rotation_count': 10}
        mgr.save_state(test_state)
        
        # Verify state was set
        state_before = mgr.get_state()
        assert state_before['last_monitor_index'] == 3
        assert state_before['rotation_count'] == 10
        
        # Reset rotation
        mgr.reset_rotation()
        
        # Verify reset
        state_after = mgr.get_state()
        assert state_after['last_monitor_index'] == -1
        assert state_after['rotation_count'] == 0


def test_state_file_corruption_handling(monitor_config):
    """Test handling of corrupted state file."""
    import tempfile
    
    # Use a temporary state file to ensure isolation
    with tempfile.TemporaryDirectory() as temp_dir:
        state_file = Path(temp_dir) / "test_state.json"
        
        mgr = StateManager(monitor_config)
        mgr.state_file = state_file
        
        # Write invalid JSON to state file
        state_file.write_text("invalid json content")
        
        # Should handle gracefully and return default state
        state = mgr.get_state()
        assert state == {'last_monitor_index': -1, 'rotation_count': 0}


def test_single_monitor_rotation(monitor_config):
    """Test rotation behavior with single monitor."""
    import tempfile
    
    # Use a temporary state file to ensure isolation
    with tempfile.TemporaryDirectory() as temp_dir:
        state_file = Path(temp_dir) / "test_state.json"
        
        # Create a monitor config with 1 monitor for testing
        test_monitor_config = type('MonitorConfig', (), {'count': 1})()
        
        mgr = StateManager(test_monitor_config)
        mgr.state_file = state_file
        
        # Reset state first
        mgr.reset_rotation()
        
        # Should always return 0 for single monitor
        next_idx = mgr.get_next_monitor_index()
        assert next_idx == 0
        
        next_idx = mgr.get_next_monitor_index()
        assert next_idx == 0


def test_multi_monitor_rotation(monitor_config):
    """Test rotation behavior with multiple monitors."""
    import tempfile
    
    # Use a temporary state file to ensure isolation
    with tempfile.TemporaryDirectory() as temp_dir:
        state_file = Path(temp_dir) / "test_state.json"
        
        # Create a monitor config with 3 monitors for testing
        test_monitor_config = type('MonitorConfig', (), {'count': 3})()
        
        mgr = StateManager(test_monitor_config)
        mgr.state_file = state_file
        
        # Reset state first
        mgr.reset_rotation()
        
        # Should rotate through 0, 1, 2, 0, 1, 2...
        assert mgr.get_next_monitor_index() == 0
        assert mgr.get_next_monitor_index() == 1
        assert mgr.get_next_monitor_index() == 2
        assert mgr.get_next_monitor_index() == 0
        assert mgr.get_next_monitor_index() == 1
        assert mgr.get_next_monitor_index() == 2
