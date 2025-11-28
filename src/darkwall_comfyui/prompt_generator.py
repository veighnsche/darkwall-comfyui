"""
Template-based prompt generator for dark-mode wallpapers.

This module handles prompt generation using user-configurable templates
with wildcard substitution and variant selection.

Syntax:
  __path__ - Random line from atoms/path.txt
  {a|b|c}  - Random choice from options
  {0.5::a|2::b} - Weighted random choice
  ---negative--- - Separator for negative prompt section
"""

import hashlib
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from .config import PromptConfig
from .exceptions import PromptError


@dataclass
class PromptResult:
    """Result of prompt generation with positive and negative prompts."""
    positive: str
    negative: str = ""
    seed: Optional[int] = None


class PromptGenerator:
    """
    Template-based prompt generator with wildcard and variant support.
    
    Uses time-based seeds for deterministic output with per-monitor variation.
    """
    
    # Regex patterns for template parsing
    WILDCARD_PATTERN = re.compile(r'__([a-zA-Z0-9_/.-]+)__')
    VARIANT_PATTERN = re.compile(r'\{([^{}]+)\}')
    WEIGHTED_OPTION = re.compile(r'^(\d+(?:\.\d+)?)::(.*)')
    
    def __init__(self, prompt_config: PromptConfig, config_dir: Path) -> None:
        """Initialize prompt generator with configuration."""
        self.config = prompt_config
        self.config_dir = config_dir
        self.logger = logging.getLogger(__name__)
        
        # Cache for loaded atom files
        self._atom_cache: Dict[str, List[str]] = {}
    
    def get_time_slot_seed(self, slot_minutes: int = None, monitor_index: int = None) -> int:
        """
        Generate deterministic seed based on current time slot.
        
        Args:
            slot_minutes: Length of each time slot in minutes
            monitor_index: Monitor index for variation
            
        Returns:
            Integer seed for deterministic selection
        """
        if slot_minutes is None:
            slot_minutes = self.config.time_slot_minutes
        
        now = datetime.now()
        slot_number = now.minute // slot_minutes
        slot_string = f"{now.year}-{now.month}-{now.day}-{now.hour}-{slot_number}"
        
        if self.config.use_monitor_seed and monitor_index is not None:
            slot_string = f"{slot_string}-monitor{monitor_index}"
        
        return int(hashlib.md5(slot_string.encode()).hexdigest()[:8], 16)
    
    def _load_atom_file(self, path: str) -> List[str]:
        """
        Load atoms from a file, with caching.
        
        Args:
            path: Relative path within atoms directory (without .txt)
            
        Returns:
            List of atom strings (empty list if file not found)
            
        Raises:
            PromptError: If file loading fails critically
        """
        if path in self._atom_cache:
            return self._atom_cache[path]
        
        atoms_dir = self.config_dir / self.config.atoms_dir
        atom_file = atoms_dir / f"{path}.txt"
        
        atoms = []
        
        if atom_file.exists() and atom_file.is_file():
            try:
                with open(atom_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            atoms.append(line)
                        elif not line and line_num > 1:  # Skip empty lines except first
                            continue
                
                self.logger.debug(f"Loaded {len(atoms)} atoms from {atom_file}")
            except (OSError, UnicodeDecodeError) as e:
                raise PromptError(f"Failed to load atom file {atom_file}: {e}")
            except Exception as e:
                raise PromptError(f"Unexpected error loading atom file {atom_file}: {e}")
        else:
            self.logger.warning(f"Atom file not found: {atom_file}")
        
        self._atom_cache[path] = atoms
        return atoms
    
    def _select_from_list(self, items: List[str], seed: int, variation: int = 0) -> str:
        """
        Deterministically select an item from a list.
        
        Args:
            items: List of options
            seed: Base seed value
            variation: Variation offset for different selections
            
        Returns:
            Selected item, or empty string if list is empty
        """
        if not items:
            return ""
        
        index = (seed + variation * 1000) % len(items)
        return items[index]
    
    def _resolve_wildcard(self, match: re.Match, seed: int, variation_counter: List[int]) -> str:
        """
        Resolve a __wildcard__ to a random atom.
        
        Args:
            match: Regex match object
            seed: Base seed
            variation_counter: Mutable counter for variation
            
        Returns:
            Selected atom string
        """
        path = match.group(1)
        atoms = self._load_atom_file(path)
        
        if not atoms:
            self.logger.warning(f"No atoms for wildcard __{path}__")
            return f"[missing:{path}]"
        
        result = self._select_from_list(atoms, seed, variation_counter[0])
        variation_counter[0] += 1
        return result
    
    def _parse_weighted_options(self, options_str: str) -> List[Tuple[float, str]]:
        """
        Parse options with optional weights.
        
        Format: "0.5::option1|2::option2|option3"
        
        Returns:
            List of (weight, option) tuples
        """
        options = []
        for opt in options_str.split('|'):
            opt = opt.strip()
            if not opt:
                continue
            
            weight_match = self.WEIGHTED_OPTION.match(opt)
            if weight_match:
                weight = float(weight_match.group(1))
                value = weight_match.group(2)
            else:
                weight = 1.0
                value = opt
            
            options.append((weight, value))
        
        return options
    
    def _resolve_variant(self, match: re.Match, seed: int, variation_counter: List[int]) -> str:
        """
        Resolve a {variant|syntax} to a random option.
        
        Args:
            match: Regex match object
            seed: Base seed
            variation_counter: Mutable counter for variation
            
        Returns:
            Selected option string
        """
        options = self._parse_weighted_options(match.group(1))
        
        if not options:
            return ""
        
        # Calculate total weight
        total_weight = sum(w for w, _ in options)
        
        # Deterministic weighted selection
        var_seed = seed + variation_counter[0] * 1000
        variation_counter[0] += 1
        
        # Use seed to pick a point in the weight range
        pick_point = (var_seed % 10000) / 10000.0 * total_weight
        
        cumulative = 0.0
        for weight, value in options:
            cumulative += weight
            if pick_point <= cumulative:
                return value
        
        # Fallback to last option
        return options[-1][1]
    
    def _resolve_template(self, template: str, seed: int) -> str:
        """
        Resolve all wildcards and variants in a template.
        
        Args:
            template: Template string with __wildcards__ and {variants}
            seed: Base seed for deterministic selection
            
        Returns:
            Resolved prompt string
        """
        variation_counter = [0]  # Mutable counter for variation
        
        # First resolve wildcards (they may contain variants)
        def resolve_wc(m):
            return self._resolve_wildcard(m, seed, variation_counter)
        
        result = self.WILDCARD_PATTERN.sub(resolve_wc, template)
        
        # Then resolve variants
        def resolve_var(m):
            return self._resolve_variant(m, seed, variation_counter)
        
        # Keep resolving until no more variants (handles nested)
        prev_result = None
        max_iterations = 10
        iteration = 0
        
        while result != prev_result and iteration < max_iterations:
            prev_result = result
            result = self.VARIANT_PATTERN.sub(resolve_var, result)
            iteration += 1
        
        return result
    
    def _load_template(self, template_path: Optional[str] = None) -> str:
        """
        Load a prompt template file.
        
        Args:
            template_path: Path to template relative to prompts/ dir
            
        Returns:
            Template content string
            
        Raises:
            PromptError: If template loading fails
        """
        if template_path is None:
            template_path = getattr(self.config, 'default_template', 'default.prompt')
        
        prompts_dir = self.config_dir / "prompts"
        template_file = prompts_dir / template_path
        
        if not template_file.exists():
            raise PromptError(
                f"Template not found: {template_file}\n"
                f"Create a .prompt file in {prompts_dir}/ or run 'darkwall init'"
            )
        
        if not template_file.is_file():
            raise PromptError(f"Template path is not a file: {template_file}")
        
        try:
            content = template_file.read_text(encoding='utf-8')
            if not content.strip():
                raise PromptError(f"Template file is empty: {template_file}")
            self.logger.debug(f"Loaded template: {template_file}")
            return content
        except (OSError, UnicodeDecodeError) as e:
            raise PromptError(f"Failed to load template {template_file}: {e}")
        except Exception as e:
            raise PromptError(f"Unexpected error loading template {template_file}: {e}")
    
    
    def _parse_template_sections(self, template: str) -> Tuple[str, str]:
        """
        Parse template into positive and negative sections.
        
        Args:
            template: Full template content
            
        Returns:
            Tuple of (positive_template, negative_template)
        """
        # Remove comment lines
        lines = []
        for line in template.split('\n'):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                lines.append(line)
        
        content = '\n'.join(lines)
        
        # Split on ---negative--- separator
        separator = '---negative---'
        if separator in content:
            parts = content.split(separator, 1)
            positive = parts[0].strip()
            negative = parts[1].strip() if len(parts) > 1 else ""
        else:
            positive = content.strip()
            negative = ""
        
        return positive, negative
    
    def generate_prompt(self, monitor_index: int = None, template_path: str = None) -> str:
        """
        Generate a complete deterministic prompt (positive only, for backwards compatibility).
        
        Args:
            monitor_index: Optional monitor index for variation
            template_path: Optional path to template file
            
        Returns:
            Complete prompt string ready for ComfyUI
            
        Raises:
            PromptError: If prompt generation fails
        """
        result = self.generate_prompt_pair(monitor_index, template_path)
        return result.positive
    
    def generate_prompt_pair(self, monitor_index: int = None, template_path: str = None, seed: int = None) -> PromptResult:
        """
        Generate both positive and negative prompts.
        
        Args:
            monitor_index: Optional monitor index for variation
            template_path: Optional path to template file
            seed: Optional specific seed to use (default: time-based)
            
        Returns:
            PromptResult with positive and negative prompts
            
        Raises:
            PromptError: If prompt generation fails
        """
        try:
            if seed is None:
                seed = self.get_time_slot_seed(monitor_index=monitor_index)
            self.logger.debug(f"Generated seed {seed} for monitor {monitor_index or 'default'}")
            
            # Load and parse template
            template = self._load_template(template_path)
            positive_template, negative_template = self._parse_template_sections(template)
            
            # Resolve templates
            positive = self._resolve_template(positive_template, seed)
            negative = self._resolve_template(negative_template, seed + 50000)  # Different seed for negative
            
            # Clean up whitespace
            positive = ' '.join(positive.split())
            negative = ' '.join(negative.split())
            
            # Validate
            if not positive or len(positive.strip()) < 10:
                raise PromptError(f"Generated prompt too short: {len(positive)} chars")
            
            self.logger.info(f"Generated prompt: {positive[:80]}...")
            if negative:
                self.logger.debug(f"Negative prompt: {negative[:80]}...")
            
            return PromptResult(positive=positive, negative=negative, seed=seed)
            
        except PromptError:
            raise
        except Exception as e:
            self.logger.error(f"Prompt generation failed: {e}")
            raise PromptError(f"Prompt generation failed: {e}")
    
