# DarkWall ComfyUI API Documentation

This directory contains documentation for DarkWall ComfyUI's internal APIs, architecture, and extension points.

## API Documentation Structure

### Core Modules
- [config.md](config.md) - Configuration system and dataclasses
- [comfy/](comfy/) - ComfyUI integration and workflow management
- [history/](history/) - Wallpaper history and gallery system
- [prompt_generator.md](prompt_generator.md) - Prompt generation and templates
- [wallpaper/](wallpaper/) - Wallpaper setting and management

### Commands
- [commands/](commands/) - CLI command implementations

### Utilities
- [exceptions.md](exceptions.md) - Exception hierarchy and error handling

## Architecture Overview

DarkWall ComfyUI follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Layer     │    │  Configuration  │    │   History       │
│                 │    │                 │    │                 │
│ • Commands      │◄──►│ • Dataclasses   │◄──►│ • Gallery       │
│ • Subcommands   │    │ • Validation    │    │ • Metadata      │
│ • Argument      │    │ • Environment   │    │ • Cleanup       │
│   Parsing       │    │   Variables     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Prompt System   │    │  ComfyUI Client │    │ Wallpaper       │
│                 │    │                 │    │ Management      │
│ • Templates     │◄──►│ • HTTP API      │◄──►│ • File I/O      │
│ • Atoms         │    │ • Workflows     │    │ • Setters       │
│ • Generation    │    │ • Generation    │    │ • Backups       │
│                 │    │ • Polling       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Key Design Principles

### 1. Dependency Injection
All classes accept configuration objects rather than accessing global state, making them testable and modular.

### 2. Clean Separation
- **Configuration**: Separate from business logic
- **Generation**: Independent of wallpaper setting
- **History**: Optional feature that can be disabled
- **CLI**: Thin layer over core functionality

### 3. Error Handling
Comprehensive exception hierarchy with specific error types for different failure modes.

### 4. Extensibility
- Plugin architecture for wallpaper setters
- Template system for prompt generation
- Configurable workflows per monitor

## Extension Points

### Custom Wallpaper Setters
Implement `WallpaperSetter` interface:
```python
class CustomSetter(WallpaperSetter):
    def set(self, wallpaper_path: Path, monitor_index: int) -> bool:
        # Your implementation
        return True
```

### Custom Prompt Generators
Extend `PromptGenerator` or create new template processors.

### Custom Workflow Managers
Implement workflow loading, validation, and prompt injection.

## Data Flow

1. **Configuration Loading**: TOML → Dataclasses → Validation
2. **Prompt Generation**: Templates + Atoms → PromptResult
3. **ComfyUI Generation**: Workflow + Prompts → GenerationResult
4. **History Saving**: GenerationResult + Metadata → HistoryEntry
5. **Wallpaper Setting**: Image Data → File System → Wallpaper Tool

## Testing Strategy

- **Unit Tests**: Individual modules and functions
- **Integration Tests**: End-to-end workflows with mocked ComfyUI
- **Golden Tests**: Layout regression prevention
- **CLI Tests**: Command-line interface behavior

## Performance Considerations

- **Lazy Loading**: Resources loaded only when needed
- **Connection Pooling**: HTTP connections reused
- **Background Operations**: History cleanup runs asynchronously
- **Memory Management**: Large image data processed efficiently
