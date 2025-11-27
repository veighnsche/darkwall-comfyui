"""Tests for the state manager."""

import json
import pytest
from pathlib import Path

from darkwall_comfyui.config import StateManager


def test_state_manager_initialization(test_config):
    """Test that StateManager initializes correctly."""
    mgr = StateManager(test_config)
    
    assert mgr.config == test_config
    assert mgr.state_file == test_config.get_state_file()
    assert hasattr(mgr, 'logger')


def test_state_initialization(test_config):
    """Test state initialization when no state file exists."""
    mgr = StateManager(test_config)
    
    # Ensure state file doesn't exist
    if mgr.state_file.exists():
        mgr.state_file.unlink()
    
    state = mgr.get_state()
    
    assert isinstance(state, dict)
    assert state.get('last_monitor_index') == -1
    assert state.get('rotation_count') == 0


def test_state_persistence(test_config):
    """Test that state is saved and loaded correctly."""
    mgr = StateManager(test_config)
    
    # Save test state
    test_state = {'last_monitor_index': 2, 'rotation_count': 5}
    mgr.save_state(test_state)
    
    # Load state
    loaded_state = mgr.get_state()
    
    assert loaded_state['last_monitor_index'] == 2
    assert loaded_state['rotation_count'] == 5


def test_state_file_creation(test_config):
    """Test that state file is created when saving."""
    mgr = StateManager(test_config)
    
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


def test_next_monitor_index_rotation(test_config):
    """Test monitor index rotation logic."""
    mgr = StateManager(test_config)
    
    # Reset state first
    mgr.reset_rotation()
    
    # Test rotation for 2 monitors
    test_config.monitors.count = 2
    
    # First call should return 0 (from -1 initial state)
    next_idx = mgr.get_next_monitor_index()
    assert next_idx == 0
    
    # Second call should return 1
    next_idx = mgr.get_next_monitor_index()
    assert next_idx == 1
    
    # Third call should wrap back to 0
    next_idx = mgr.get_next_monitor_index()
    assert next_idx == 0


def test_rotation_count_increment(test_config):
    """Test that rotation count is incremented correctly."""
    mgr = StateManager(test_config)
    
    # Reset state first
    mgr.reset_rotation()
    
    initial_count = mgr.get_state().get('rotation_count', 0)
    assert initial_count == 0
    
    # Get next monitor (should increment count)
    mgr.get_next_monitor_index()
    
    count_after_one = mgr.get_state().get('rotation_count', 0)
    assert count_after_one == 1
    
    # Get next monitor again
    mgr.get_next_monitor_index()
    
    count_after_two = mgr.get_state().get('rotation_count', 0)
    assert count_after_two == 2


def test_reset_rotation(test_config):
    """Test rotation state reset."""
    mgr = StateManager(test_config)
    
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


def test_state_file_corruption_handling(test_config):
    """Test handling of corrupted state file."""
    mgr = StateManager(test_config)
    
    # Write invalid JSON to state file
    mgr.state_file.parent.mkdir(parents=True, exist_ok=True)
    mgr.state_file.write_text("{ invalid json content")
    
    # Should fall back to default state
    state = mgr.get_state()
    
    assert state.get('last_monitor_index') == -1
    assert state.get('rotation_count') == 0


def test_state_directory_creation(test_config):
    """Test that state directory is created when needed."""
    mgr = StateManager(test_config)
    
    # Remove state directory if it exists
    if mgr.state_file.parent.exists():
        mgr.state_file.parent.rmdir()
    
    assert not mgr.state_file.parent.exists()
    
    # Save state (should create directory)
    test_state = {'last_monitor_index': 0, 'rotation_count': 1}
    mgr.save_state(test_state)
    
    # Directory should exist
    assert mgr.state_file.parent.exists()
    assert mgr.state_file.exists()


def test_single_monitor_rotation(test_config):
    """Test rotation with single monitor."""
    mgr = StateManager(test_config)
    
    # Reset state
    mgr.reset_rotation()
    
    # Set single monitor
    test_config.monitors.count = 1
    
    # Should always return 0 for single monitor
    for i in range(5):
        next_idx = mgr.get_next_monitor_index()
        assert next_idx == 0


def test_multi_monitor_rotation(test_config):
    """Test rotation with multiple monitors."""
    mgr = StateManager(test_config)
    
    # Reset state
    mgr.reset_rotation()
    
    # Test with 3 monitors
    test_config.monitors.count = 3
    
    expected_sequence = [0, 1, 2, 0, 1, 2]
    actual_sequence = []
    
    for _ in range(6):
        next_idx = mgr.get_next_monitor_index()
        actual_sequence.append(next_idx)
    
    assert actual_sequence == expected_sequence
