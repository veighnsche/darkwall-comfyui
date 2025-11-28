# DarkWall ComfyUI Documentation

This directory contains comprehensive documentation for DarkWall ComfyUI, a multi-monitor wallpaper generator using ComfyUI.

## Documentation Structure

### User Documentation
- `darkwall.1.md` - Man page source (converted to groff during build)
- `troubleshooting.md` - Common issues and solutions
- `configuration.md` - Complete configuration reference
- `examples.md` - Usage examples and workflows

### Developer Documentation
- `api/` - Internal API documentation
- `architecture.md` - System architecture overview
- `contributing.md` - Development guidelines

## Building Documentation

### Man Page Generation

Man pages are generated during the Nix build process using pandoc:

```bash
# Generate man page locally
pandoc docs/darkwall.1.md -s -t man -o docs/darkwall.1

# View generated man page
man docs/darkwall.1
```

The man page is automatically installed to `/share/man/man1/darkwall.1` during Nix package installation.

### Documentation Installation

Documentation files are installed to standard locations:
- Man pages: `/share/man/man1/darkwall.1`
- User docs: `/share/doc/darkwall-comfyui/`
- API docs: `/share/doc/darkwall-comfyui/api/`
