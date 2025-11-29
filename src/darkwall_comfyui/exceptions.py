"""
Common exception classes for DarkWall ComfyUI.

Provides domain-specific exceptions for consistent error handling across modules.
All exceptions inherit from DarkWallError for unified catching at CLI level.
"""


class DarkWallError(Exception):
    """
    Base exception for all DarkWall ComfyUI errors.
    
    All domain-specific exceptions inherit from this class, allowing
    callers to catch all DarkWall errors with a single except clause.
    """
    pass


# ============================================================================
# Configuration Errors
# ============================================================================

class ConfigError(DarkWallError):
    """
    Configuration-related errors.
    
    Raised when:
    - Config file is malformed or missing required fields
    - Config validation fails
    - Deprecated config keys are used
    - Theme or workflow references are invalid
    """
    pass


class ConfigValidationError(ConfigError):
    """
    Config value validation failed.
    
    Raised when a config value is present but invalid (e.g., out of range,
    wrong type after parsing, invalid URL format).
    """
    pass


class ConfigMigrationError(ConfigError):
    """
    Config migration required.
    
    Raised when deprecated config keys are detected and migration is needed.
    The error message should include migration instructions.
    """
    pass


# ============================================================================
# Workflow Errors
# ============================================================================

class WorkflowError(DarkWallError):
    """
    Workflow loading or validation errors.
    
    Raised when:
    - Workflow file not found or unreadable
    - Workflow JSON is malformed
    - Workflow missing required placeholders
    """
    pass


class WorkflowNotFoundError(WorkflowError):
    """Workflow file does not exist at the expected path."""
    pass


class WorkflowValidationError(WorkflowError):
    """
    Workflow structure is invalid.
    
    Raised when workflow is missing required placeholders like
    __POSITIVE_PROMPT__ or has invalid node structure.
    """
    pass


# ============================================================================
# Generation Errors
# ============================================================================

class GenerationError(DarkWallError):
    """
    Wallpaper generation errors.
    
    Base class for errors during the image generation process.
    """
    pass


class ComfyClientError(GenerationError):
    """
    ComfyUI client communication error.
    
    Raised for HTTP errors, invalid responses, or unexpected API behavior.
    """
    pass


class ComfyConnectionError(ComfyClientError):
    """
    Cannot connect to ComfyUI server.
    
    Raised when the server is unreachable, connection times out,
    or DNS resolution fails.
    """
    pass


class ComfyTimeoutError(ComfyClientError):
    """
    ComfyUI operation timed out.
    
    Raised when generation takes longer than the configured timeout.
    """
    pass


class ComfyGenerationError(ComfyClientError):
    """
    ComfyUI generation failed.
    
    Raised when ComfyUI reports an error during generation,
    or when no output images are produced.
    """
    pass


# ============================================================================
# Command Errors
# ============================================================================

class CommandError(DarkWallError):
    """
    Command execution errors (wallpaper setters, external tools).
    
    Raised when external commands fail to execute or return errors.
    """
    pass


class CommandNotFoundError(CommandError):
    """
    Required command/tool not found in PATH.
    
    Raised when a wallpaper setter or other required tool is not installed.
    """
    pass


class CommandTimeoutError(CommandError):
    """External command timed out."""
    pass


class CommandPermissionError(CommandError):
    """Permission denied executing command."""
    pass


# ============================================================================
# Prompt Errors
# ============================================================================

class PromptError(DarkWallError):
    """
    Prompt generation errors.
    
    Raised when prompt template loading or expansion fails.
    """
    pass


class TemplateNotFoundError(PromptError):
    """Prompt template file not found."""
    pass


class AtomFileError(PromptError):
    """Error loading or parsing atom file."""
    pass


class TemplateParseError(PromptError):
    """Error parsing prompt template syntax."""
    pass


# ============================================================================
# State Errors
# ============================================================================

class StateError(DarkWallError):
    """
    State management errors.
    
    Raised when reading/writing rotation state fails.
    """
    pass


# ============================================================================
# Monitor Detection Errors
# ============================================================================

class MonitorDetectionError(DarkWallError):
    """
    Monitor detection errors.
    
    Base class for errors during compositor monitor detection.
    """
    pass


class CompositorNotFoundError(MonitorDetectionError):
    """
    No supported compositor is running.
    
    Raised when neither niri, sway, nor hyprland is detected.
    """
    pass


class CompositorCommunicationError(MonitorDetectionError):
    """
    Failed to communicate with compositor.
    
    Raised when compositor IPC commands fail or time out.
    """
    pass


class NoMonitorsDetectedError(MonitorDetectionError):
    """
    No monitors detected from compositor.
    
    Raised when compositor reports no connected outputs.
    """
    pass


# ============================================================================
# Schedule Errors
# ============================================================================

class ScheduleError(DarkWallError):
    """
    Theme scheduling errors.
    
    Raised when solar calculations or schedule configuration fails.
    """
    pass


class SolarCalculationError(ScheduleError):
    """
    Solar position calculation failed.
    
    Raised when astral library fails to calculate sunrise/sunset,
    typically due to invalid coordinates or extreme latitudes.
    """
    pass


# ============================================================================
# Notification Errors
# ============================================================================

class NotificationError(DarkWallError):
    """
    Desktop notification errors.
    
    Raised when notification sending fails. These are typically non-fatal.
    """
    pass
