"""
Deterministic prompt generator for dark-mode wallpapers.

This module handles the creation of deterministic wallpaper prompts
based on four pillars: subject, environment, lighting, and style.
Supports multi-monitor setups with monitor-specific seeding.
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

from .config import Config


@dataclass
class PromptPillars:
    """Data class representing the four pillars of prompt generation."""
    subject: str
    environment: str
    lighting: str
    style: str


class PromptGenerator:
    """
    Generates deterministic dark-mode wallpaper prompts.
    
    The generator uses time-based seeds to ensure deterministic output
    while providing variety through different combinations of prompt pillars.
    Supports multi-monitor setups with monitor-specific variation.
    """
    
    def __init__(self, config: Config):
        """Initialize prompt generator with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Load prompt atoms from config directory
        self.atoms = self._load_atoms()
    
    def _load_atoms(self) -> Dict[str, List[str]]:
        """
        Load prompt atoms from the configured atoms directory.
        
        Returns:
            Dictionary mapping pillar names to atom lists
        """
        atoms_dir = self.config.get_config_dir() / self.config.prompt.atoms_dir
        
        if not atoms_dir.exists():
            raise FileNotFoundError(
                f"Atoms directory not found: {atoms_dir}\n"
                f"Run 'generate-wallpaper-once init' to initialize config."
            )
        
        atoms = {}
        
        # Load atoms from numbered files
        for pillar_name, filename in [
            ("subject", "1_subject.txt"),
            ("environment", "2_environment.txt"), 
            ("lighting", "3_lighting.txt"),
            ("style", "4_style.txt")
        ]:
            pillar_file = atoms_dir / filename
            
            if not pillar_file.exists():
                self.logger.warning(f"Atoms file not found: {pillar_file}")
                atoms[pillar_name] = []
                continue
            
            try:
                with open(pillar_file, 'r', encoding='utf-8') as f:
                    # Read lines, strip whitespace, ignore empty lines and comments
                    lines = [
                        line.strip() 
                        for line in f 
                        if line.strip() and not line.strip().startswith('#')
                    ]
                    atoms[pillar_name] = lines
                    
                self.logger.debug(f"Loaded {len(lines)} atoms for {pillar_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to load atoms from {pillar_file}: {e}")
                atoms[pillar_name] = []
        
        return atoms
    
    def get_time_slot_seed(self, slot_minutes: int = None, monitor_index: int = None) -> int:
        """
        Generate deterministic seed based on current time slot and optional monitor index.
        
        Args:
            slot_minutes: Length of each time slot in minutes (defaults to config)
            monitor_index: Monitor index for variation (defaults to None)
            
        Returns:
            Integer seed for deterministic selection
        """
        if slot_minutes is None:
            slot_minutes = self.config.prompt.time_slot_minutes
        
        now = datetime.now()
        # Create slot identifier: YYYY-MM-DD-HH-slot
        slot_number = now.minute // slot_minutes
        slot_string = f"{now.year}-{now.month}-{now.day}-{now.hour}-{slot_number}"
        
        # Add monitor index to seed if enabled and provided
        if self.config.prompt.use_monitor_seed and monitor_index is not None:
            slot_string = f"{slot_string}-monitor{monitor_index}"
        
        # Convert to deterministic integer seed
        seed = int(hashlib.md5(slot_string.encode()).hexdigest()[:8], 16)
        return seed
    
    def select_atom(self, atoms: List[str], seed: int, pillar_index: int) -> str:
        """
        Select an atom from a list using deterministic seed.
        
        Args:
            atoms: List of possible atoms
            seed: Base seed value
            pillar_index: Index of pillar (0-3) for variation
            
        Returns:
            Selected atom string
        """
        if not atoms:
            self.logger.warning(f"No atoms available for pillar {pillar_index}")
            return "minimal dark wallpaper"
        
        # Vary seed per pillar to avoid same selection pattern
        pillar_seed = seed + (pillar_index * 1000)
        index = pillar_seed % len(atoms)
        return atoms[index]
    
    def generate_pillars(self, seed: int) -> PromptPillars:
        """
        Generate the four prompt pillars using deterministic seed.
        
        Args:
            seed: Deterministic seed value
            
        Returns:
            PromptPillars object with selected atoms
        """
        subject = self.select_atom(self.atoms.get("subject", []), seed, 0)
        environment = self.select_atom(self.atoms.get("environment", []), seed, 1)
        lighting = self.select_atom(self.atoms.get("lighting", []), seed, 2)
        style = self.select_atom(self.atoms.get("style", []), seed, 3)
        
        return PromptPillars(
            subject=subject,
            environment=environment,
            lighting=lighting,
            style=style
        )
    
    def build_prompt(self, pillars: PromptPillars) -> str:
        """
        Build final prompt string from pillars.
        
        Args:
            pillars: PromptPillars object with selected atoms
            
        Returns:
            Complete prompt string optimized for dark-mode wallpapers
        """
        # Combine pillars with natural language flow
        prompt_parts = [
            pillars.subject,
            f"{pillars.environment},",
            pillars.lighting + ",",
            pillars.style + ",",
            "16:9 wallpaper, dark mode friendly,",
            "no text, no watermark, no signature,",
            "high quality, detailed"
        ]
        
        return " ".join(prompt_parts)
    
    def generate_prompt(self, monitor_index: int = None) -> str:
        """
        Generate a complete deterministic prompt.
        
        Args:
            monitor_index: Optional monitor index for variation
            
        Returns:
            Complete prompt string ready for ComfyUI
        """
        seed = self.get_time_slot_seed(monitor_index=monitor_index)
        pillars = self.generate_pillars(seed)
        prompt = self.build_prompt(pillars)
        
        self.logger.debug(f"Generated prompt for monitor {monitor_index or 'default'}: {prompt}")
        return prompt
