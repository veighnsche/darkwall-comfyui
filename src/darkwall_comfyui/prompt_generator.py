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

from .config import Config, PromptConfig
from .exceptions import PromptError


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
    
    def __init__(self, prompt_config: PromptConfig, config_dir: Path) -> None:
        """Initialize prompt generator with configuration."""
        self.config = prompt_config
        self.config_dir = config_dir
        self.logger = logging.getLogger(__name__)
        
        # Load prompt atoms from config directory
        self.atoms = self._load_atoms()
    
    def _load_atoms(self) -> Dict[str, List[str]]:
        """
        Load prompt atoms from the configured atoms directory.
        
        Returns:
            Dictionary mapping pillar names to atom lists
            
        Raises:
            FileNotFoundError: If atoms directory doesn't exist
        """
        atoms_dir = self.config_dir / self.config.atoms_dir
        
        self.logger.debug(f"Loading atoms from: {atoms_dir}")
        
        # Check atoms directory exists
        if not atoms_dir.exists():
            raise FileNotFoundError(
                f"Atoms directory not found: {atoms_dir}\n"
                f"Run 'generate-wallpaper-once init' to initialize config."
            )
        
        if not atoms_dir.is_dir():
            raise FileNotFoundError(
                f"Atoms path is not a directory: {atoms_dir}\n"
                f"Please check your configuration."
            )
        
        # Check if directory is readable
        import os
        if not os.access(atoms_dir, os.R_OK):
            raise FileNotFoundError(
                f"Atoms directory is not readable: {atoms_dir}\n"
                f"Check directory permissions."
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
            
            if not pillar_file.is_file():
                self.logger.warning(f"Atoms path is not a file: {pillar_file}")
                atoms[pillar_name] = []
                continue
            
            # Check file is readable
            if not os.access(pillar_file, os.R_OK):
                self.logger.warning(f"Atoms file is not readable: {pillar_file}")
                atoms[pillar_name] = []
                continue
            
            try:
                with open(pillar_file, 'r', encoding='utf-8') as f:
                    # Read lines, strip whitespace, ignore empty lines and comments
                    lines = []
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            lines.append(line)
                        elif not line:
                            # Skip empty lines silently
                            continue
                        elif line.startswith('#'):
                            # Skip comments silently
                            continue
                        else:
                            self.logger.debug(f"Skipping line {line_num} in {pillar_file}: empty or comment")
                    
                    atoms[pillar_name] = lines
                    
                self.logger.info(f"Loaded {len(lines)} atoms for {pillar_name} from {pillar_file}")
                
                # Validate that we have some atoms
                if not lines:
                    self.logger.warning(f"No atoms found in {pillar_file}")
                
            except UnicodeDecodeError as e:
                self.logger.error(f"Encoding error reading {pillar_file}: {e}")
                atoms[pillar_name] = []
            except OSError as e:
                self.logger.error(f"Filesystem error reading {pillar_file}: {e}")
                atoms[pillar_name] = []
            except Exception as e:
                self.logger.error(f"Unexpected error reading {pillar_file}: {e}")
                atoms[pillar_name] = []
        
        # Validate we have at least some atoms
        total_atoms = sum(len(atom_list) for atom_list in atoms.values())
        if total_atoms == 0:
            self.logger.warning("No atoms loaded from any files - prompt generation will fail")
        
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
            slot_minutes = self.config.time_slot_minutes
        
        now = datetime.now()
        # Create slot identifier: YYYY-MM-DD-HH-slot
        slot_number = now.minute // slot_minutes
        slot_string = f"{now.year}-{now.month}-{now.day}-{now.hour}-{slot_number}"
        
        # Add monitor index to seed if enabled and provided
        if self.config.use_monitor_seed and monitor_index is not None:
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
            
        Raises:
            PromptError: If prompt generation fails
        """
        try:
            # Generate time slot seed
            seed = self.get_time_slot_seed(monitor_index=monitor_index)
            self.logger.debug(f"Generated seed {seed} for monitor {monitor_index or 'default'}")
            
            # Generate pillars from seed
            pillars = self.generate_pillars(seed)
            
            # Validate pillars
            if not all([pillars.subject, pillars.environment, pillars.lighting, pillars.style]):
                missing = [name for name, value in [
                    ("subject", pillars.subject),
                    ("environment", pillars.environment), 
                    ("lighting", pillars.lighting),
                    ("style", pillars.style)
                ] if not value]
                self.logger.warning(f"Missing pillars: {missing}")
            
            # Build final prompt
            prompt = self.build_prompt(pillars)
            
            # Validate prompt
            if not prompt or len(prompt.strip()) == 0:
                raise PromptError("Generated prompt is empty")
            
            if len(prompt) < 10:
                raise PromptError(f"Generated prompt too short: {len(prompt)} chars")
            
            return prompt
            
        except PromptError:
            # Re-raise our own exceptions
            raise
        except (ValueError, KeyError) as e:
            self.logger.error(f"Prompt generation error: {e}")
            raise PromptError(f"Prompt generation failed: {e}")
        except Exception as e:
            self.logger.error(f"Failed to generate prompt for monitor {monitor_index}: {e}")
            raise PromptError(f"Prompt generation failed: {e}")
