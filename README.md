# DarkWall ComfyUI

A deterministic dark-mode wallpaper generator that calls ComfyUI to create time-based wallpapers.

## What this tool does

- Generates deterministic dark-mode wallpaper prompts from composable "pillars"
- Calls ComfyUI at https://comfyui.home.arpa using saved workflow API format
- Polls until results are ready and saves wallpaper images to ~/Pictures/wallpapers/current.png
- Designed to be called periodically by systemd user timers on NixOS

## Project Phases

### PHASE 0 — PROJECT SETUP ✅
- Choose project name: `darkwall-comfyui`
- Create project directory under ~/Projects/
- Initialize Git repository
- Create this README with all phases documented

### PHASE 1 — PROJECT CREATION & NAMING ✅
- [x] Create minimal .gitignore file
- [x] Enhance README.md with project structure
- [x] Add "Quick start" section placeholder
- [x] Add "Nix flake integration" section placeholder

### PHASE 2 — PROJECT LAYOUT & MODULE STRUCTURE ✅
- [x] Design Python package layout under src/
- [x] Create planned module structure:
  - `src/darkwall_comfyui/`
  - `__init__.py`
  - `main.py` or `cli.py` (entry point)
  - `prompt_generator.py` (deterministic dark-mode wallpaper prompt builder)
  - `comfy_client.py` (talks to ComfyUI HTTP API)
  - `wallpaper_target.py` (manages output path and wallpaper update logic)
  - `config.py` (reads environment variables / simple config file)
- [x] Document structure in README

### PHASE 3 — DETERMINISTIC PROMPT DESIGN (NO IMPLEMENTATION YET) ✅
- [x] Design prompt model based on four "pillars":
  - Subject / focal point
  - Environment / space
  - Lighting & color (dark mode)
  - Style & composition
- [x] Define phrase "atoms" for each pillar
- [x] Ensure all examples are dark-mode friendly
- [x] Design determinism using time-slot-derived seeds
- [x] Document in README "Prompt Design & Determinism" section
- [x] Add design comments to prompt_generator.py

### PHASE 4 — RESEARCH COMFYUI HTTP API (LOOK ONLINE) ✅
- [x] Research ComfyUI HTTP API endpoints:
  - `/prompt` to submit workflow
  - `/history/{prompt_id}` to query progress/results
  - `/view` to download generated images
- [x] Find guides on "Save (API Format)" workflows
- [x] Research Python examples using requests
- [x] Summarize findings in README "ComfyUI API notes" section
- [x] Add API design comments to comfy_client.py

## Tool Behaviour & Configuration

### CLI Command: generate-wallpaper-once

The tool executes as a single-shot command that generates one wallpaper and exits. No internal scheduling or loops - periodic execution is handled by external systemd timers.

#### Execution Flow

1. **Configuration Loading**
   - Load environment variables (COMFYUI_BASE_URL, etc.)
   - Parse optional config file if provided
   - Validate workflow file exists and is valid JSON
   - Ensure output directory is writable

2. **Deterministic Prompt Generation**
   - Calculate current time slot (default: 30-minute windows)
   - Generate seed from date+hour+slot using MD5 hash
   - Select one atom from each pillar using seed with offsets
   - Combine pillars into final prompt with wallpaper optimizations

3. **Workflow Preparation**
   - Load ComfyUI workflow JSON from configured path
   - Locate text input nodes (CLIPTextEncode class types)
   - Inject generated prompt into appropriate node fields
   - Preserve workflow structure and node connections

4. **Generation Submission**
   - POST workflow to ComfyUI /prompt endpoint
   - Extract prompt_id from response for tracking
   - Log submission with prompt ID and timestamp

5. **Result Polling**
   - Poll /history/{prompt_id} every 5 seconds (configurable)
   - Check for completion status or timeout (default: 5 minutes)
   - Parse output data to find generated image metadata
   - Handle generation failures gracefully

6. **Image Download & Storage**
   - Extract filename from completed generation results
   - Download image via /view endpoint with proper parameters
   - Save to configured path (default: ~/Pictures/wallpapers/current.png)
   - Verify file integrity and log final location

#### Logging Strategy

- **stdout**: Progress updates and final result path
- **stderr**: Errors and warnings with timestamps
- **Verbose mode**: Detailed debug information including API calls
- **Quiet mode**: Minimal output, just final wallpaper path

### Configuration Variables

#### Core Settings
- **COMFYUI_BASE_URL**: ComfyUI instance URL (default: https://comfyui.home.arpa)
- **COMFYUI_WORKFLOW_PATH**: Path to workflow JSON file (default: workflow.json)
- **WALLPAPER_OUTPUT_PATH**: Output image path (default: ~/Pictures/wallpapers/current.png)

#### Timing & Reliability
- **COMFYUI_TIMEOUT**: Generation timeout in seconds (default: 300)
- **COMFYUI_POLL_INTERVAL**: Polling interval in seconds (default: 5)
- **TIME_SLOT_MINUTES**: Time slot duration for determinism (default: 30)

#### Authentication & Headers
- **COMFYUI_HEADERS**: Custom headers in "Key1:Value1,Key2:Value2" format
- **DARKWALL_THEME**: Theme selector for future expansion (default: default)

#### Logging
- **DARKWALL_LOG_LEVEL**: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Error Handling Strategy

#### Configuration Errors
- Missing workflow file: Clear error with expected path
- Invalid JSON: Show parsing error location
- Permission issues: Directory creation failures
- Network connectivity: DNS resolution and connection errors

#### Generation Errors
- Invalid workflow submission: API response validation
- Timeout scenarios: Graceful failure with configurable limits
- Generation failures: ComfyUI error message forwarding
- Missing output images: Validation of result completeness

#### Recovery Behavior
- Network retries: Exponential backoff for transient failures
- Partial failures: Cleanup of temporary files
- State consistency: Ensure no partial wallpaper overwrites

### Integration Points

#### Systemd Timer Integration
The tool is designed for systemd user service integration:
- **Service**: Executes generate-wallpaper-once command
- **Timer**: Triggers service every 30 minutes (configurable)
- **User scope**: Runs as user service, no root required
- **Logging**: systemd journal captures stdout/stderr

#### Example Timer Configuration
```ini
[Unit]
Description=Generate dark-mode wallpaper

[Service]
Type=oneshot
ExecStart=/nix/store/.../bin/generate-wallpaper-once
StandardOutput=journal
StandardError=journal

[Timer]
OnCalendar=*:0/30
Persistent=true

[Install]
WantedBy=timers.target
```

### Exit Codes

- **0**: Success - wallpaper generated and saved
- **1**: Configuration error - missing files, invalid settings
- **2**: Network error - ComfyUI unreachable
- **3**: Generation error - ComfyUI failed to generate
- **4**: Timeout error - generation exceeded time limit
- **5**: Filesystem error - unable to save wallpaper

### Performance Considerations

- **Memory usage**: Minimal - loads single workflow JSON
- **Network efficiency**: Reuses HTTP session, reasonable polling
- **Disk usage**: Overwrites single wallpaper file, optional backups
- **CPU usage**: Light - prompt generation and HTTP handling only

## Nix Flake Design

### Flake Structure Overview

The flake.nix provides both a development environment and a distributable package for the darkwall-comfyui wallpaper generator.

#### Design Philosophy
- **Minimal dependencies**: Only Python 3.9+ and requests library
- **Standard Python packaging**: Uses pyproject.toml with buildPythonPackage
- **Dual output**: Package for production use + devShell for development
- **Non-flake compatibility**: Importable from traditional NixOS configs

#### Flake Outputs

##### packages.${system}.default
- **Type**: Python package derivation using buildPythonPackage
- **Entry point**: `generate-wallpaper-once` CLI command
- **Dependencies**: python3, requests
- **Runtime**: Ready-to-use binary for systemd user services

##### devShells.${system}.default  
- **Type**: Development environment with additional tooling
- **Includes**: python3, requests, pytest, black, isort, mypy
- **Purpose**: Development, testing, and code quality maintenance

### Integration Patterns

#### Flake-based Integration
For users already using flakes:
```nix
# flake.nix
inputs.darkwall.url = "path:/home/vince/Projects/darkwall-comfyui";

outputs = { self, nixpkgs, darkwall }: {
  homeConfigurations.vince = nixpkgs.lib.homeManagerConfiguration {
    configuration = {
      home.packages = [ darkwall.packages.${system}.default ];
      
      systemd.user = {
        services.wallpaper-generator = {
          Unit = { Description = "Generate dark-mode wallpaper"; };
          Service = {
            Type = "oneshot";
            ExecStart = "${darkwall.packages.${system}.default}/bin/generate-wallpaper-once";
          };
        };
        
        timers.wallpaper-generator = {
          Unit = { Description = "Periodic wallpaper generation"; };
          Timer = {
            OnCalendar = "*:0/30";  # Every 30 minutes
            Persistent = true;
          };
          Install.WantedBy = [ "timers.target" ];
        };
      };
    };
  };
}
```

#### Non-flake Integration (bridging pattern)
For traditional NixOS with home-manager via builtins.fetchTarball:

```nix
# pkgs/darkwall-comfyui.nix
{ pkgs, system ? "x86_64-linux" }:
let
  flake = builtins.getFlake "/home/vince/Projects/darkwall-comfyui";
in
flake.packages.${system}.default
```

Then import in main configuration:
```nix
# home/default.nix
{ pkgs, ... }:
{
  home.packages = [
    (pkgs.callPackage ../pkgs/darkwall-comfyui.nix { inherit pkgs; })
  ];
  
  # systemd user service configuration as above
}
```

#### Alternative: Direct fetchTarball approach
For completely offline builds:
```nix
# pkgs/darkwall-comfyui.nix
{ pkgs }:

pkgs.python3Packages.buildPythonPackage rec {
  pname = "darkwall-comfyui";
  version = "0.1.0";
  
  src = pkgs.fetchFromGitHub {
    owner = "vince";
    repo = "darkwall-comfyui";
    rev = "v${version}";
    hash = "sha256-...";  # Updated on release
  };
  
  propagatedBuildInputs = with pkgs.python3Packages; [
    requests
  ];
  
  meta = {
    description = "Deterministic dark-mode wallpaper generator using ComfyUI";
    homepage = "https://github.com/vince/darkwall-comfyui";
    license = pkgs.lib.licenses.mit;
  };
}
```

### Development Workflow

#### Using the Dev Shell
```bash
# Enter development environment
nix develop

# Run tests
pytest

# Format code
black src/
isort src/

# Type checking
mypy src/
```

#### Building the Package
```bash
# Build for current system
nix build

# Install to user profile
nix profile install .

# Test CLI
./result/bin/generate-wallpaper-once --help
```

### Deployment Considerations

#### Systemd User Service Integration
The generated package includes the CLI binary at:
```
/nix/store/...-darkwall-comfyui-0.1.0/bin/generate-wallpaper-once
```

This binary can be directly referenced in systemd user service files without additional wrapper scripts.

#### Configuration Management
Environment variables for the service can be set via:
```nix
systemd.user.services.wallpaper-generator.Service.Environment = {
  COMFYUI_BASE_URL = "https://comfyui.home.arpa";
  WALLPAPER_OUTPUT_PATH = "%h/Pictures/wallpapers/current.png";
};
```

#### Update Strategy
- **Development**: Update flake input and rebuild
- **Production**: Pin specific git hash in configuration
- **Rollback**: Use nix profile rollback or previous generation

### Flake Dependencies

#### Minimal Input Set
```nix
inputs = {
  nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  flake-utils.url = "github:numtide/flake-utils";
};
```

#### Future Expansion Points
- **nixpkgs-stable**: For production stability
- **poetry2nix**: If dependency management grows complex
- **treefmt-nix**: For consistent code formatting
- **pre-commit-hooks**: For development quality gates

### PHASE 7 — IMPLEMENTATION (AFTER DESIGN IS CLEAR) ✅
- [x] Implement Python modules according to design
- [x] Implement flake.nix according to design
- [x] Update README "Quick start" and "Nix flake integration" sections
- [x] Test CLI runs manually once
- [x] Ensure project compiles/builds successfully

## Quick start

### Prerequisites

- NixOS or any system with Nix flakes enabled
- Access to a ComfyUI instance at https://comfyui.home.arpa (or configurable URL)
- A ComfyUI workflow exported in API format (see below)

### Setup

1. **Clone and build the project:**
   ```bash
   cd ~/Projects/darkwall-comfyui
   nix build
   ```

2. **Create a ComfyUI workflow:**
   - Open ComfyUI web interface
   - Enable Dev Mode Options: Settings → Enable Dev Mode Options
   - Create your image generation workflow
   - Export: Menu → Save (API Format) → Save as `workflow.json`
   - Place `workflow.json` in the project directory

3. **Test the CLI:**
   ```bash
   ./result/bin/generate-wallpaper-once --help
   ./result/bin/generate-wallpaper-once --verbose
   ```

4. **Development environment (optional):**
   ```bash
   nix develop
   # Now you can run tests, format code, etc.
   python -m darkwall_comfyui.main --verbose
   ```

### Configuration

Set environment variables or create a config file:

```bash
# Required
export COMFYUI_BASE_URL="https://comfyui.home.arpa"
export COMFYUI_WORKFLOW_PATH="/path/to/your/workflow.json"
export WALLPAPER_OUTPUT_PATH="$HOME/Pictures/wallpapers/current.png"

# Optional
export COMFYUI_TIMEOUT="300"
export COMFYUI_POLL_INTERVAL="5"
export TIME_SLOT_MINUTES="30"
export DARKWALL_LOG_LEVEL="INFO"
```

### Systemd Integration

Add to your NixOS/home-manager configuration:

```nix
# Add the package
home.packages = [
  (builtins.getFlake "/home/vince/Projects/darkwall-comfyui").packages.${system}.default
];

# Systemd user service
systemd.user.services.wallpaper-generator = {
  Unit = { Description = "Generate dark-mode wallpaper"; };
  Service = {
    Type = "oneshot";
    ExecStart = "%h/.nix-profile/bin/generate-wallpaper-once";
    Environment = {
      COMFYUI_BASE_URL = "https://comfyui.home.arpa";
      WALLPAPER_OUTPUT_PATH = "%h/Pictures/wallpapers/current.png";
    };
  };
};

systemd.user.timers.wallpaper-generator = {
  Unit = { Description = "Periodic wallpaper generation"; };
  Timer = {
    OnCalendar = "*:0/30";  # Every 30 minutes
    Persistent = true;
  };
  Install.WantedBy = [ "timers.target" ];
};
```

### Usage

Run manually:
```bash
generate-wallpaper-once --verbose
```

Enable automatic generation:
```bash
systemctl --user enable --now wallpaper-generator.timer
```

The wallpaper will be updated every 30 minutes with deterministic, dark-mode friendly images.

## Project Structure

```
darkwall-comfyui/
├── README.md
├── LICENSE
├── pyproject.toml
├── flake.nix
├── .gitignore
└── src/
    └── darkwall_comfyui/
        ├── __init__.py
        ├── main.py              # CLI entry point
        ├── prompt_generator.py  # Deterministic prompt builder
        ├── comfy_client.py      # ComfyUI HTTP API client
        ├── wallpaper_target.py  # Output path and wallpaper handling
        └── config.py            # Configuration management
```

### Module Responsibilities

- **`prompt_generator.py`**: Pure logic for building deterministic dark-mode wallpaper prompts from four pillars
- **`comfy_client.py`**: HTTP client for ComfyUI API communication (workflow submission, polling, image download)
- **`wallpaper_target.py`**: Filesystem operations and wallpaper output management
- **`config.py`**: Environment variable and configuration file handling
- **`main.py`**: CLI orchestration and command-line interface

## Nix flake integration

*This section placeholder for later.*

## Prompt Design & Determinism

### Four Pillars Model

The prompt generator uses a deterministic model based on four compositional "pillars" that ensure dark-mode friendly wallpapers while providing variety through controlled randomization.

#### Pillar 1: Subject / Focal Point
The primary visual element that anchors the composition. Subjects are chosen to work well with dark backgrounds and limited lighting.

**Planned Atoms:**
- Lone architectural elements (city skyline, lighthouse, tower)
- Natural formations (mountain peak, twisted tree, waterfall)
- Mystical objects (crystal cave, stone monolith, floating island)
- Solitary structures (abandoned building, bridge silhouette)

**Design Principles:**
- Single focal point to avoid visual clutter
- Strong silhouette potential against dark backgrounds
- Compatible with dramatic lighting scenarios
- Scalable to wallpaper resolution without losing impact

#### Pillar 2: Environment / Space
The surrounding context that provides depth and atmosphere. Environments complement the dark-mode aesthetic.

**Planned Atoms:**
- Above reflective surfaces (dark ocean, calm lake)
- Enclosed spaces (misty valley, canyon walls, forest edge)
- Celestial settings (star-filled sky, under aurora, deep space)
- Atmospheric conditions (surrounded by fog, in endless desert)

**Design Principles:**
- Naturally dark or low-light environments
- Provide negative space for desktop icons
- Create sense of scale and depth
- Support the lighting pillar requirements

#### Pillar 3: Lighting & Color (Dark Mode)
The illumination scheme that ensures dark-mode compatibility while adding visual interest.

**Planned Atoms:**
- Low-key lighting techniques
- Navy and charcoal color palettes
- Neon accent colors (blue, purple, cyan)
- Moonlight and ambient glow scenarios
- High contrast with limited bright areas

**Design Principles:**
- Dark backgrounds dominate (>70% of image)
- Limited bright accents for visual hierarchy
- Cool color temperature preference
- Sufficient contrast for UI element visibility

#### Pillar 4: Style & Composition
The artistic approach and compositional guidelines that optimize for wallpaper use.

**Planned Atoms:**
- Cinematic 16:9 aspect ratio emphasis
- Abundant negative space for icon placement
- Digital art styles (painterly, crisp rendering)
- Minimalist composition principles
- Professional photography aesthetics

**Design Principles:**
- Explicit 16:9 or wallpaper references in prompts
- No text, watermarks, or signatures
- High resolution and detail requirements
- Clean edges and defined boundaries

### Determinism Strategy

#### Time-Slot Seed Generation
The system uses deterministic seeding based on time slots to ensure:
- Same prompt within the same time slot across multiple runs
- Different prompts for different time slots
- Predictable daily variation

**Algorithm:**
1. Calculate current time slot: `floor(current_minutes / slot_minutes)`
2. Create slot identifier: `YYYY-MM-DD-HH-slot_number`
3. Generate MD5 hash of slot identifier
4. Convert first 8 hex characters to integer seed
5. Use seed with pillar-specific offsets for atom selection

**Default Configuration:**
- Time slot duration: 30 minutes
- 48 unique prompts per day
- Seed variation per pillar prevents patterns

#### Seed-to-Atom Mapping
Each pillar uses the base seed with different offsets to ensure varied combinations:
- Subject: `seed + (0 * 1000)`
- Environment: `seed + (1 * 1000)`
- Lighting: `seed + (2 * 1000)`
- Style: `seed + (3 * 1000)`

This prevents the same time slot from always selecting the same indexed atom across all pillars.

### Final Prompt Construction

The complete prompt combines all pillars with explicit wallpaper optimization:

```
{subject} {environment}, {lighting}, {style}, 16:9 wallpaper, dark mode friendly, no text, no watermark, no signature, high quality, detailed
```

**Example Output:**
```
lone city skyline at dusk above a dark ocean, low-key lighting, cinematic 16:9 wide shot, lots of negative space for icons, 16:9 wallpaper, dark mode friendly, no text, no watermark, no signature, high quality, detailed
```

### Configuration Points

- **Time slot duration**: Configurable (default 30 minutes)
- **Theme support**: Future expansion for different atom sets
- **Pillar weights**: Future enhancement for favoring certain pillars
- **Prompt templates**: Future customization of final prompt format

## ComfyUI API notes

### Core Endpoints

ComfyUI provides five key HTTP endpoints that form the foundation for API integration:

#### POST /prompt
- **Purpose**: Queues workflows for execution
- **Request**: JSON with `prompt` (workflow JSON) and optional `client_id`
- **Response**: Returns `prompt_id` for tracking or error details
- **Usage**: Submit workflow with injected prompt for generation

#### GET /history/{prompt_id}
- **Purpose**: Retrieves generation status and results
- **Request**: prompt_id from /prompt response
- **Response**: JSON with queue status or output data (including image filenames)
- **Usage**: Poll for completion and get image metadata

#### GET /view
- **Purpose**: Downloads generated images
- **Request**: Query parameters `filename`, `subfolder`, `type`
- **Response**: Raw image data (binary)
- **Usage**: Download final wallpaper image

#### POST /upload/image
- **Purpose**: Uploads images to ComfyUI (not needed for our use case)
- **Request**: multipart/form-data with image file
- **Response**: Upload confirmation
- **Usage**: Future expansion for image-to-image workflows

#### WebSocket /ws
- **Purpose**: Real-time status updates and progress tracking
- **Usage**: Alternative to polling /history endpoint
- **Our approach**: Will use simple HTTP polling for reliability

### Workflow Format

#### Save (API Format)
- Export workflows via ComfyUI GUI: Settings → Enable Dev Mode Options → Save (API Format)
- Produces JSON file with node structure and input connections
- Contains node IDs, class types, and input parameters
- Example node types: KSampler, CLIPTextEncode, CheckpointLoader, VAEDecode

#### Prompt Injection Strategy
- Locate text input nodes (typically CLIPTextEncode class_type)
- Find KSampler node for seed management
- Inject generated prompt into `text` field of appropriate nodes
- Ensure seed variation for unique outputs

### Request/Response Patterns

#### Workflow Submission
```json
POST /prompt
{
  "prompt": {
    "1": {
      "class_type": "CLIPTextEncode",
      "inputs": {
        "text": "generated prompt here",
        "clip": ["2", 1]
      }
    }
  },
  "client_id": "optional_client_id"
}
```

#### Status Check Response
```json
GET /history/{prompt_id}
{
  "prompt_id": {
    "outputs": {
      "4": {
        "images": [
          {
            "filename": "ComfyUI_00001_.png",
            "subfolder": "",
            "type": "output"
          }
        ]
      }
    },
    "status": "completed"
  }
}
```

#### Image Download
```
GET /view?filename=ComfyUI_00001_.png&subfolder=&type=output
```

### Configuration for Our Use Case

#### Base URL Adaptation
- Default: `http://127.0.0.1:8188`
- Our target: `https://comfyui.home.arpa`
- Configuration: `COMFYUI_BASE_URL` environment variable
- TLS/HTTPS: Supported via standard HTTPS requests

#### Authentication Headers
- Basic auth: Add `Authorization` header to requests
- API keys: Add custom headers via `COMFYUI_HEADERS` env var
- Format: `"Key1:Value1,Key2:Value2"`

#### Error Handling
- Network timeouts: Configurable timeout values
- Invalid workflows: JSON validation before submission
- Generation failures: Check status field in /history response
- Missing images: Validate image list in outputs

### Python Implementation Notes

#### Required Dependencies
- `requests` for HTTP client
- `json` for workflow manipulation
- `time` for polling intervals
- `pathlib` for file handling

#### Key Implementation Points
- Use `requests.Session()` for connection reuse
- Implement exponential backoff for polling
- Validate workflow JSON before submission
- Handle both HTTP and HTTPS schemes transparently
- Support custom headers for future authentication needs
