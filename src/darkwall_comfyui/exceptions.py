"""
Common exception classes for DarkWall ComfyUI.

Provides domain-specific exceptions for consistent error handling across modules.
"""


class DarkWallError(Exception):
    """Base exception for all DarkWall ComfyUI errors."""
    pass


class ConfigError(DarkWallError):
    """Configuration-related errors."""
    pass


class WorkflowError(DarkWallError):
    """Workflow loading or validation errors."""
    pass


class GenerationError(DarkWallError):
    """Wallpaper generation errors."""
    pass


class CommandError(DarkWallError):
    """Command execution errors (wallpaper setters, external tools)."""
    pass


class PromptError(DarkWallError):
    """Prompt generation errors."""
    pass


class StateError(DarkWallError):
    """State management errors."""
    pass
