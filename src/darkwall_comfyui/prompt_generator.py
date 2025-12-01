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

from .config import PromptConfig, Config, ThemeConfig
from .exceptions import PromptError, TemplateNotFoundError, AtomFileError, TemplateParseError


@dataclass
class PromptResult:
    """
    Result of prompt generation with named prompt sections.
    
    TEAM_007: Updated to support arbitrary named sections for multi-prompt workflows.
    Backwards compatible via .positive and .negative properties.
    """
    prompts: Dict[str, str]      # {"positive": "...", "environment": "...", "subject": "..."}
    negatives: Dict[str, str]    # {"positive": "...", "environment": "...", "subject": "..."}
    seed: Optional[int] = None
    
    # Backwards compatibility properties
    @property
    def positive(self) -> str:
        """Get the 'positive' section for backwards compatibility."""
        return self.prompts.get("positive", "")
    
    @property
    def negative(self) -> str:
        """Get the 'positive:negative' section for backwards compatibility."""
        return self.negatives.get("positive", "")
    
    def get_prompt(self, section: str) -> str:
        """Get a named prompt section."""
        return self.prompts.get(section, "")
    
    def get_negative(self, section: str) -> str:
        """Get a named negative section."""
        return self.negatives.get(section, "")
    
    def sections(self) -> List[str]:
        """List all available prompt sections."""
        return list(self.prompts.keys())
    
    @classmethod
    def from_legacy(cls, positive: str, negative: str = "", seed: int = None) -> 'PromptResult':
        """Create from legacy positive/negative format."""
        return cls(
            prompts={"positive": positive},
            negatives={"positive": negative} if negative else {},
            seed=seed
        )
    
    def __str__(self) -> str:
        """String representation for logging."""
        sections = []
        for name in sorted(self.prompts.keys()):
            prompt_preview = self.prompts[name][:50] + "..." if len(self.prompts[name]) > 50 else self.prompts[name]
            sections.append(f"[{name}] {prompt_preview}")
            if name in self.negatives:
                neg_preview = self.negatives[name][:50] + "..." if len(self.negatives[name]) > 50 else self.negatives[name]
                sections.append(f"[{name}:negative] {neg_preview}")
        return "\n".join(sections)


class PromptGenerator:
    """
    Template-based prompt generator with wildcard and variant support.
    
    Uses time-based seeds for deterministic output with per-monitor variation.
    """
    
    # Regex patterns for template parsing
    WILDCARD_PATTERN = re.compile(r'__([a-zA-Z0-9_/.-]+)__')
    VARIANT_PATTERN = re.compile(r'\{([^{}]+)\}')
    WEIGHTED_OPTION = re.compile(r'^(\d+(?:\.\d+)?)::(.*)')
    
    def __init__(self, prompt_config: PromptConfig, config_dir: Path, 
                 atoms_dir: Optional[Path] = None, prompts_dir: Optional[Path] = None) -> None:
        """
        Initialize prompt generator with configuration.
        
        TEAM_001: Now accepts explicit atoms_dir and prompts_dir paths
        to support theme-based directory structures.
        
        Args:
            prompt_config: Prompt generation settings
            config_dir: Base config directory
            atoms_dir: Override path for atoms (for theme support)
            prompts_dir: Override path for prompts (for theme support)
        """
        self.config = prompt_config
        self.config_dir = config_dir
        self.logger = logging.getLogger(__name__)
        
        # TEAM_001: Theme-aware paths (fall back to legacy if not provided)
        self._atoms_dir = atoms_dir or (config_dir / prompt_config.atoms_dir)
        self._prompts_dir = prompts_dir or (config_dir / "prompts")
        
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
        
        # TEAM_001: Use theme-aware atoms directory
        atom_file = self._atoms_dir / f"{path}.txt"
        
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
            except UnicodeDecodeError as e:
                raise AtomFileError(
                    f"Invalid encoding in atom file {atom_file}: {e}\n"
                    "Atom files must be UTF-8 encoded."
                ) from e
            except PermissionError as e:
                raise AtomFileError(
                    f"Permission denied reading atom file {atom_file}: {e}"
                ) from e
            except OSError as e:
                raise AtomFileError(
                    f"Failed to read atom file {atom_file}: {e}"
                ) from e
            except Exception as e:
                raise AtomFileError(
                    f"Unexpected error loading atom file {atom_file}: {type(e).__name__}: {e}"
                ) from e
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
        
        # TEAM_001: Use theme-aware prompts directory
        template_file = self._prompts_dir / template_path
        
        if not template_file.exists():
            raise TemplateNotFoundError(
                f"Template not found: {template_file}\n"
                f"Create a .prompt file in {self._prompts_dir}/ or run 'darkwall init'\n"
                f"Available templates can be listed with 'darkwall prompt list'"
            )
        
        if not template_file.is_file():
            raise TemplateNotFoundError(
                f"Template path is not a file: {template_file}\n"
                "Check that the path points to a .prompt file, not a directory."
            )
        
        try:
            content = template_file.read_text(encoding='utf-8')
            if not content.strip():
                raise TemplateParseError(
                    f"Template file is empty: {template_file}\n"
                    "Templates must contain at least a positive prompt section."
                )
            self.logger.debug(f"Loaded template: {template_file}")
            return content
        except UnicodeDecodeError as e:
            raise TemplateParseError(
                f"Invalid encoding in template {template_file}: {e}\n"
                "Template files must be UTF-8 encoded."
            ) from e
        except PermissionError as e:
            raise TemplateNotFoundError(
                f"Permission denied reading template {template_file}: {e}"
            ) from e
        except OSError as e:
            raise TemplateNotFoundError(
                f"Failed to read template {template_file}: {e}"
            ) from e
        except PromptError:
            raise
        except Exception as e:
            raise PromptError(
                f"Unexpected error loading template {template_file}: {type(e).__name__}: {e}"
            ) from e
    
    
    def _parse_template_sections(self, template: str) -> Dict[str, str]:
        """
        Parse template into named sections.
        
        TEAM_007: Uses $$section$$ syntax to avoid conflict with __wildcard__ atoms.
        
        Section syntax:
            $$section_name$$          -> prompts["section_name"]
            $$section_name:negative$$ -> negatives["section_name"]
            $$negative$$              -> negatives["positive"] (legacy)
        
        Content before first section marker goes to "positive".
        
        Args:
            template: Full template content
            
        Returns:
            Dict mapping section names to content (including :negative suffix for negatives)
        """
        sections: Dict[str, str] = {}
        current_section = "positive"  # Default section for content before first marker
        current_content: List[str] = []
        
        for line in template.split('\n'):
            stripped = line.strip()
            
            # Skip comments
            if stripped.startswith('#'):
                continue
            
            # Check for section marker: $$name$$ or $$name:negative$$ (must be alone on line)
            if stripped.startswith('$$') and stripped.endswith('$$') and len(stripped) > 4:
                # Verify it's a section marker (contains only valid section name chars)
                inner = stripped[2:-2]  # Remove $$ from both ends
                # Section names: lowercase alphanumeric, underscores, and optional :negative suffix
                if inner and all(c.isalnum() or c in '_:' for c in inner):
                    # Save previous section if it has content
                    if current_content:
                        content = '\n'.join(current_content).strip()
                        if content:
                            sections[current_section] = content
                    
                    # Start new section
                    current_section = inner
                    current_content = []
                    continue
            
            current_content.append(line)
        
        # Save final section
        if current_content:
            content = '\n'.join(current_content).strip()
            if content:
                sections[current_section] = content
        
        return sections
    
    def generate_prompt(self, monitor_index: int = None, template_path: str = None) -> str:
        """
        Generate a complete deterministic prompt (positive only, for backwards compatibility).
        
        TEAM_007: For multi-section templates, combines all positive sections.
        
        Args:
            monitor_index: Optional monitor index for variation
            template_path: Optional path to template file
            
        Returns:
            Complete prompt string ready for ComfyUI
            
        Raises:
            PromptError: If prompt generation fails
        """
        result = self.generate_prompt_pair(monitor_index, template_path)
        
        # For legacy single-section templates, use .positive
        sections = result.sections()
        if 'positive' in sections:
            return result.positive
        
        # For multi-section templates, combine all positive prompts
        return "\n\n".join(result.get_prompt(s) for s in sections if result.get_prompt(s))
    
    def generate_prompt_pair(self, monitor_index: int = None, template_path: str = None, seed: int = None) -> PromptResult:
        """
        Generate prompts for all sections in the template.
        
        TEAM_007: Updated to support arbitrary named sections.
        
        Args:
            monitor_index: Optional monitor index for variation
            template_path: Optional path to template file
            seed: Optional specific seed to use (default: time-based)
            
        Returns:
            PromptResult with named prompt sections
            
        Raises:
            PromptError: If prompt generation fails
        """
        try:
            if seed is None:
                seed = self.get_time_slot_seed(monitor_index=monitor_index)
            self.logger.debug(f"Generated seed {seed} for monitor {monitor_index or 'default'}")
            
            # Load and parse template into named sections
            template = self._load_template(template_path)
            sections = self._parse_template_sections(template)
            
            # TEAM_007: Process sections into prompts and negatives dicts
            prompts: Dict[str, str] = {}
            negatives: Dict[str, str] = {}
            
            for section_name, content in sections.items():
                # Use section name hash for variation to ensure reproducibility
                section_offset = hash(section_name) % 10000
                
                if section_name.endswith(':negative'):
                    # This is a negative section: ---subject:negative---
                    base_name = section_name[:-9]  # Remove ':negative'
                    resolved = self._resolve_template(content, seed + section_offset)
                    negatives[base_name] = ' '.join(resolved.split())
                elif section_name == 'negative':
                    # Legacy: ---negative--- maps to positive:negative
                    resolved = self._resolve_template(content, seed + 50000)
                    negatives['positive'] = ' '.join(resolved.split())
                else:
                    # Regular prompt section
                    resolved = self._resolve_template(content, seed + section_offset)
                    prompts[section_name] = ' '.join(resolved.split())
            
            # Validate: must have at least one prompt section
            if not prompts:
                raise TemplateParseError(
                    "No prompt sections found in template.\n"
                    "Templates must contain at least one prompt section."
                )
            
            # Validate: primary prompt (positive or first section) must be substantial
            primary_prompt = prompts.get('positive', next(iter(prompts.values())))
            if len(primary_prompt.strip()) < 10:
                raise TemplateParseError(
                    f"Generated prompt too short ({len(primary_prompt)} chars).\n"
                    "Check that your template contains valid content and wildcards resolve correctly."
                )
            
            # Log generated prompts
            for name, prompt in prompts.items():
                self.logger.info(f"Generated [{name}]: {prompt[:60]}...")
            for name, neg in negatives.items():
                self.logger.debug(f"Generated [{name}:negative]: {neg[:60]}...")
            
            return PromptResult(prompts=prompts, negatives=negatives, seed=seed)
            
        except PromptError:
            raise
        except Exception as e:
            self.logger.error(f"Prompt generation failed: {e}")
            raise PromptError(f"Prompt generation failed: {e}")
    
    @classmethod
    def from_config(cls, config: Config, theme_name: Optional[str] = None) -> 'PromptGenerator':
        """
        Create a PromptGenerator from a full Config object.
        
        TEAM_001: Factory method that handles theme-aware path resolution.
        
        Args:
            config: Full configuration object
            theme_name: Optional theme override (defaults to config.prompt.theme)
            
        Returns:
            PromptGenerator configured for the specified theme
        """
        config_dir = config.get_config_dir()
        atoms_dir = config.get_theme_atoms_path(theme_name)
        prompts_dir = config.get_theme_prompts_path(theme_name)
        
        return cls(
            prompt_config=config.prompt,
            config_dir=config_dir,
            atoms_dir=atoms_dir,
            prompts_dir=prompts_dir,
        )
    
