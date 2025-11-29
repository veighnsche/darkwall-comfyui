{
  description = "Deterministic dark-mode wallpaper generator using ComfyUI";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        # Python package with all dependencies
        darkwall-comfyui = pkgs.python3Packages.buildPythonApplication rec {
          pname = "darkwall-comfyui";
          version = "0.1.0";
          
          src = ./.;
          
          pyproject = true;

          # Python runtime dependencies (must satisfy wheel metadata)
          dependencies = with pkgs.python3Packages; [
            requests
            tomli
            tomli-w
            websocket-client
            tqdm
            astral  # TEAM_003: Solar calculations for theme scheduling
          ];
          
          # Build dependencies
          nativeBuildInputs = with pkgs.python3Packages; [
            setuptools
            wheel
            pkgs.makeWrapper
          ];
          
          # Runtime dependencies for wallpaper setters
          runtimeDependencies = with pkgs; [
            # Wayland wallpaper setters
            swww
            swaybg
            # X11 wallpaper setters  
            feh
            nitrogen
          ];
          
          postInstall = ''
            # Copy default configuration files to share directory FIRST
            mkdir -p $out/share/darkwall-comfyui
            
            # Wrap the binary to include wallpaper setters in PATH
            # and set DARKWALL_CONFIG_TEMPLATES for config initialization
            wrapProgram $out/bin/generate-wallpaper-once \
              --prefix PATH : ${pkgs.lib.makeBinPath runtimeDependencies} \
              --set DARKWALL_CONFIG_TEMPLATES "$out/share/darkwall-comfyui"
            
            # Check if config directory exists and copy files
            if [ -d "$src/config" ]; then
              cp -r $src/config/* $out/share/darkwall-comfyui/ || true
              echo "Config templates copied from $src/config"
            else
              echo "Warning: Config directory not found at $src/config"
              # Create minimal config structure
              mkdir -p $out/share/darkwall-comfyui/atoms
              mkdir -p $out/share/darkwall-comfyui/prompts
              mkdir -p $out/share/darkwall-comfyui/workflows
              cat > $out/share/darkwall-comfyui/config.toml << 'EOF'
[comfyui]
base_url = "http://localhost:8188"
workflow_path = "workflow.json"
timeout = 300
poll_interval = 5

[monitors]
count = 1
command = "swww"
pattern = "monitor_{index}.png"
backup_pattern = "monitor_{index}_{timestamp}.png"

[output]
directory = "~/Pictures/wallpapers"
create_backup = true

[prompt]
atoms_dir = "atoms"
time_slot_minutes = 30
default_template = "default.prompt"

[history]
enabled = true
max_entries = 1000

[logging]
level = "INFO"
EOF
            fi
            
            # Copy systemd service files if they exist
            if [ -d "$src/systemd" ]; then
              mkdir -p $out/share/systemd/user
              cp $src/systemd/*.service $out/share/systemd/user/ 2>/dev/null || true
              cp $src/systemd/*.timer $out/share/systemd/user/ 2>/dev/null || true
            fi
          '';
          
          meta = {
            description = "Deterministic dark-mode wallpaper generator using ComfyUI";
            homepage = "https://github.com/vince/darkwall-comfyui";
            license = pkgs.lib.licenses.mit;
            platforms = pkgs.lib.platforms.linux;
            mainProgram = "generate-wallpaper-once";
          };
        };

        # NixOS module for systemd integration
        nixosModule = { config, lib, pkgs, ... }:
          with lib;
          let
            cfg = config.services.darkwall-comfyui;
          in
          {
            options.services.darkwall-comfyui = {
              enable = mkEnableOption "DarkWall ComfyUI wallpaper generator";
              
              package = mkOption {
                type = types.package;
                default = darkwall-comfyui;
                description = "DarkWall ComfyUI package to use";
              };
              
              user = mkOption {
                type = types.str;
                default = "darkwall";
                description = "User to run the service as";
              };
              
              environment = mkOption {
                type = types.attrsOf types.str;
                default = {};
                description = "Environment variables for the service";
                example = {
                  COMFYUI_BASE_URL = "https://comfyui.home.arpa";
                  TIME_SLOT_MINUTES = "30";
                };
              };
              
              timer = {
                enable = mkOption {
                  type = types.bool;
                  default = true;
                  description = "Enable systemd timer for automatic generation";
                };
                
                onCalendar = mkOption {
                  type = types.str;
                  default = "*:0/30";
                  description = "Systemd timer schedule (default: every 30 minutes)";
                };
              };
            };
            
            config = mkIf cfg.enable {
              # Create user if it doesn't exist
              users.users.${cfg.user} = mkIf (cfg.user != "root") {
                isSystemUser = true;
                group = cfg.user;
              };
              
              users.groups.${cfg.user} = mkIf (cfg.user != "root") {};
              
              # Systemd user service
              systemd.user.services.darkwall-comfyui = {
                description = "Generate dark-mode wallpaper";
                after = [ "network-online.target" ];
                wants = [ "network-online.target" ];
                
                serviceConfig = {
                  Type = "oneshot";
                  ExecStart = "${cfg.package}/bin/generate-wallpaper-once generate";
                  Environment = cfg.environment;
                  Restart = "on-failure";
                  RestartSec = 60;
                };
              };
              
              # Systemd timer
              systemd.user.timers.darkwall-comfyui = mkIf cfg.timer.enable {
                description = "Periodic wallpaper generation";
                timerConfig = {
                  OnCalendar = cfg.timer.onCalendar;
                  Persistent = true;
                };
                
                wantedBy = [ "timers.target" ];
              };
            };
          };

        # Home Manager module
        homeManagerModule = { config, lib, pkgs, ... }:
          with lib;
          let
            cfg = config.services.darkwall-comfyui;
          in
          {
            options.services.darkwall-comfyui = {
              enable = mkEnableOption "DarkWall ComfyUI wallpaper generator";
              
              package = mkOption {
                type = types.package;
                default = darkwall-comfyui;
                description = "DarkWall ComfyUI package to use";
              };
              
              environment = mkOption {
                type = types.attrsOf types.str;
                default = {};
                description = "Environment variables for the service";
                example = {
                  COMFYUI_BASE_URL = "https://comfyui.home.arpa";
                  TIME_SLOT_MINUTES = "30";
                  WALLPAPER_OUTPUT_PATH = "%h/Pictures/wallpapers/current.png";
                };
              };
              
              timer = {
                enable = mkOption {
                  type = types.bool;
                  default = true;
                  description = "Enable systemd timer for automatic generation";
                };
                
                onCalendar = mkOption {
                  type = types.str;
                  default = "*:0/30";
                  description = "Systemd timer schedule (default: every 30 minutes)";
                };
              };
            };
            
            config = mkIf cfg.enable {
              home.packages = [ cfg.package ];
              
              # Systemd user service
              systemd.user.services.darkwall-comfyui = {
                Unit = {
                  Description = "Generate dark-mode wallpaper";
                  After = [ "network-online.target" ];
                };
                
                Service = {
                  Type = "oneshot";
                  ExecStart = "${cfg.package}/bin/generate-wallpaper-once generate";
                  Environment = cfg.environment;
                };
              };
              
              # Systemd timer
              systemd.user.timers.darkwall-comfyui = mkIf cfg.timer.enable {
                Unit = {
                  Description = "Periodic wallpaper generation";
                };
                
                Timer = {
                  OnCalendar = cfg.timer.onCalendar;
                  Persistent = true;
                };
                
                Install.WantedBy = [ "timers.target" ];
              };
            };
          };

      in
      {
        # Packages
        packages = {
          default = darkwall-comfyui;
          darkwall-comfyui = darkwall-comfyui;
        };
        
        # Development shell
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python3
            python3Packages.requests
            python3Packages.tomli
            python3Packages.tomli-w
            python3Packages.websocket-client
            python3Packages.tqdm
            python3Packages.pytest
            python3Packages.pytest-bdd
            python3Packages.black
            python3Packages.isort
            python3Packages.mypy
            darkwall-comfyui

            # Runtime dependencies for testing
            swww
            swaybg
            feh
            nitrogen
          ];

          shellHook = ''
            export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"

            echo "🎨 DarkWall ComfyUI Development Environment"
            echo ""
            echo "Available commands:"
            echo "  pytest                           # Run all tests"
            echo "  pytest tests/step_definitions/   # Run BDD tests only"
            echo "  pytest --collect-only            # List all test scenarios"
            echo "  python -m darkwall_comfyui.cli --help"
            echo ""
            echo "BDD:"
            echo "  Feature files:    tests/features/*.feature"
            echo "  Step definitions: tests/step_definitions/*.py"
            echo ""
            echo "Build with: nix build"
            echo "Run with: nix run . -- --help"
          '';
        };
        
        # NixOS and Home Manager modules
        nixosModules.default = nixosModule;
        homeManagerModules.default = homeManagerModule;
        
        # App definition for nix run
        apps.default = {
          type = "app";
          program = "${darkwall-comfyui}/bin/generate-wallpaper-once";
        };
        
        # Formatter for this flake
        formatter = pkgs.nixfmt;
      });
}
