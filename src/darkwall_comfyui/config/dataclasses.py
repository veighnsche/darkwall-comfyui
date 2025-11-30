"""
Configuration dataclasses for DarkWall ComfyUI.

TEAM_007: Split from monolithic config.py for better organization.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class CleanupPolicy:
    """Cleanup policy for history management."""
    max_count: Optional[int] = None  # Keep max N wallpapers
    max_days: Optional[int] = None   # Keep wallpapers newer than X days
    min_favorites: Optional[int] = None  # Always keep at least N favorites
    max_size_mb: Optional[int] = None  # Keep history under X MB


@dataclass
class WeightedWorkflow:
    """A workflow prefix with a selection weight."""
    prefix: str
    weight: float = 1.0
    
    @classmethod
    def from_config(cls, data) -> 'WeightedWorkflow':
        """Parse from config (string or dict)."""
        if isinstance(data, str):
            return cls(prefix=data, weight=1.0)
        elif isinstance(data, dict):
            return cls(prefix=data['prefix'], weight=data.get('weight', 1.0))
        raise ValueError(f"Invalid workflow config: {data}")


@dataclass
class ThemeConfig:
    """
    Configuration for a content theme.
    
    Themes contain atoms (phrase fragments) and prompts (templates).
    Each theme is a self-contained content set that can be switched.
    
    TEAM_006: Added workflow_prefix for theme-to-workflow mapping.
    The workflow for a monitor is: {workflow_prefix}-{monitor_resolution}
    
    TEAM_006: Added workflows list for weighted random workflow selection.
    """
    name: str
    atoms_dir: str = "atoms"      # Relative to theme directory
    prompts_dir: str = "prompts"  # Relative to theme directory
    default_template: str = "default.prompt"
    workflow_prefix: Optional[str] = None  # TEAM_006: Single prefix (legacy)
    workflows: Optional[List[WeightedWorkflow]] = None  # TEAM_006: Weighted list of prefixes
    
    def get_atoms_path(self, config_dir: Path) -> Path:
        """Get absolute path to atoms directory for this theme."""
        return config_dir / "themes" / self.name / self.atoms_dir
    
    def get_prompts_path(self, config_dir: Path) -> Path:
        """Get absolute path to prompts directory for this theme."""
        return config_dir / "themes" / self.name / self.prompts_dir
    
    def get_template_path(self, config_dir: Path, template_name: Optional[str] = None) -> Path:
        """Get absolute path to a template file."""
        template = template_name or self.default_template
        return self.get_prompts_path(config_dir) / template
    
    def select_workflow_prefix(self) -> str:
        """
        Select a workflow prefix, using weighted random if multiple are configured.
        
        TEAM_006: Supports weighted random selection from workflows list.
        
        Returns:
            Selected workflow prefix
        """
        import random
        
        # If workflows list is configured, use weighted selection
        if self.workflows:
            total_weight = sum(w.weight for w in self.workflows)
            if total_weight > 0:
                r = random.random() * total_weight
                cumulative = 0.0
                for w in self.workflows:
                    cumulative += w.weight
                    if r <= cumulative:
                        return w.prefix
                return self.workflows[-1].prefix
        
        # Fallback to single workflow_prefix or theme name
        return self.workflow_prefix or self.name
    
    def get_workflow_for_resolution(self, resolution: str) -> str:
        """
        Get workflow name for a given resolution.
        
        TEAM_006: Theme determines workflow prefix, resolution comes from monitor.
        Uses weighted random selection if multiple workflows configured.
        
        Args:
            resolution: Monitor resolution string (e.g., "2327x1309", "1920x1080")
            
        Returns:
            Full workflow name (e.g., "z-image-turbo-2327x1309")
        """
        prefix = self.select_workflow_prefix()
        return f"{prefix}-{resolution}"
    
    def get_workflow_weights_display(self) -> str:
        """Get a display string showing workflow weights."""
        if self.workflows:
            parts = [f"{w.prefix}: {w.weight/(sum(ww.weight for ww in self.workflows))*100:.0f}%" 
                     for w in self.workflows]
            return ", ".join(parts)
        return self.workflow_prefix or self.name


@dataclass
class WorkflowConfig:
    """
    Configuration for a workflow with optional prompt filtering.
    
    TEAM_002: REQ-WORKFLOW-001, REQ-WORKFLOW-002
    
    Workflow ID = filename (without .json extension).
    Prompts can be optionally restricted to a subset.
    """
    name: str  # Workflow ID (filename without .json)
    prompts: Optional[List[str]] = None  # Optional: restrict to these prompts only
    
    def get_workflow_path(self, config_dir: Path) -> Path:
        """
        Get workflow file path.
        
        REQ-WORKFLOW-001: Workflow ID = filename.
        """
        workflow_id = self.name
        if not workflow_id.endswith(".json"):
            workflow_id = f"{workflow_id}.json"
        return config_dir / "workflows" / workflow_id
    
    def filter_prompts(self, available_prompts: List[str]) -> List[str]:
        """
        Filter available prompts based on workflow config.
        
        REQ-WORKFLOW-002: Optional prompt filtering.
        TEAM_006: ["*"] means all prompts (wildcard).
        
        Args:
            available_prompts: All prompts available in the theme
            
        Returns:
            Filtered list of prompts (all if no filter configured)
        """
        if self.prompts is None:
            return available_prompts
        # TEAM_006: ["*"] means all prompts
        if "*" in self.prompts:
            return available_prompts
        return [p for p in available_prompts if p in self.prompts]


@dataclass
class PerMonitorConfig:
    """
    Configuration for a single monitor (new format).
    
    REQ-MONITOR-003: Inline config sections per monitor.
    TEAM_006: Added resolution for theme-based workflow selection.
    """
    name: str  # Compositor output name (e.g., "DP-1")
    workflow: str = "default"  # Workflow ID (filename without .json) - DEPRECATED, use resolution + theme
    output: Optional[str] = None  # Output path (defaults to ~/Pictures/wallpapers/{name}.png)
    templates: Optional[List[str]] = None  # Allowed templates for this monitor
    resolution: Optional[str] = None  # TEAM_006: e.g., "2327x1309", "1920x1080" - used with theme.workflow_prefix
    command: Optional[str] = None  # Per-monitor wallpaper setter override
    
    def get_output_path(self) -> Path:
        """Get output path for this monitor."""
        if self.output:
            return Path(self.output).expanduser()
        return Path(f"~/Pictures/wallpapers/{self.name}.png").expanduser()
    
    def get_workflow_path(self, config_dir: Path, theme: Optional['ThemeConfig'] = None) -> Path:
        """
        Get workflow file path.
        
        TEAM_006: If theme has workflow_prefix and monitor has resolution,
        compute workflow as {prefix}-{resolution}. Otherwise use explicit workflow.
        """
        # TEAM_006: Theme-based workflow selection
        if theme and theme.workflow_prefix and self.resolution:
            workflow_id = theme.get_workflow_for_resolution(self.resolution)
        else:
            workflow_id = self.workflow
            
        if not workflow_id.endswith(".json"):
            workflow_id = f"{workflow_id}.json"
        return config_dir / "workflows" / workflow_id
    
    def get_resolution(self) -> Optional[str]:
        """Get monitor resolution string."""
        return self.resolution


@dataclass
class MonitorsConfig:
    """
    New-style monitors configuration using compositor names.
    
    REQ-MONITOR-001: Auto-detection via compositor
    REQ-MONITOR-002: Compositor names as identifiers
    REQ-MONITOR-003: Inline config sections
    """
    monitors: Dict[str, PerMonitorConfig] = field(default_factory=dict)
    command: str = "swaybg"  # Wallpaper setter command
    
    def __len__(self) -> int:
        return len(self.monitors)
    
    def get_monitor(self, name: str) -> Optional[PerMonitorConfig]:
        """Get configuration for a specific monitor."""
        return self.monitors.get(name)
    
    def get_monitor_names(self) -> List[str]:
        """Get list of configured monitor names."""
        return list(self.monitors.keys())
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MonitorsConfig':
        """
        Create MonitorsConfig from config dictionary.
        
        TEAM_006: Updated to support resolution field for theme-based workflow selection.
        
        Expects format:
        {
            "DP-1": {"resolution": "2327x1309", "output": "~/Pictures/wallpapers/DP-1.png"},
            "HDMI-A-1": {"resolution": "2327x1309"},
            "HDMI-A-2": {"resolution": "1920x1080"},
            "command": "swaybg"
        }
        """
        monitors = {}
        command = "swaybg"
        
        for key, value in config_dict.items():
            if key == "command":
                command = value
            elif isinstance(value, dict):
                # This is a monitor config
                monitors[key] = PerMonitorConfig(
                    name=key,
                    workflow=value.get("workflow", "default"),
                    output=value.get("output"),
                    templates=value.get("templates"),
                    resolution=value.get("resolution"),  # TEAM_006: For theme-based workflow
                    command=value.get("command"),  # Per-monitor wallpaper setter
                )
        
        return cls(monitors=monitors, command=command)


@dataclass
class ComfyUIConfig:
    """ComfyUI connection settings."""
    base_url: str = "https://comfyui.home.arpa"
    workflow_path: Path = field(default_factory=lambda: Path("workflow.json"))
    timeout: int = 300
    poll_interval: int = 5
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class PromptConfig:
    """Prompt generation settings."""
    time_slot_minutes: int = 30
    theme: str = "default"  # TEAM_001: Now references themes/<name>/ directory
    use_monitor_seed: bool = True
    default_template: str = "default.prompt"  # Default prompt template
    variations_per_monitor: int = 1
    # TEAM_001: Deprecated - kept for backwards compatibility, ignored if themes/ exists
    atoms_dir: str = "atoms"


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    verbose: bool = False


@dataclass
class HistoryConfig:
    """Wallpaper history configuration."""
    enabled: bool = True
    history_dir: str = "~/Pictures/wallpapers/history"
    max_entries: int = 1000
    cleanup_policy: Optional[CleanupPolicy] = None
    
    def get_history_dir(self) -> Path:
        """Get absolute history directory path."""
        return Path(self.history_dir).expanduser()
