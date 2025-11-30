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
            websocket-client
            tqdm
            astral  # Solar calculations for theme scheduling
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
            mkdir -p $out/share/darkwall-comfyui
            cp -r $src/config/* $out/share/darkwall-comfyui/
            
            wrapProgram $out/bin/darkwall \
              --prefix PATH : ${pkgs.lib.makeBinPath runtimeDependencies} \
              --set DARKWALL_CONFIG_TEMPLATES "$out/share/darkwall-comfyui"
          '';
          
          meta = {
            description = "Deterministic dark-mode wallpaper generator using ComfyUI";
            homepage = "https://github.com/vince/darkwall-comfyui";
            license = pkgs.lib.licenses.mit;
            platforms = pkgs.lib.platforms.linux;
            mainProgram = "darkwall";
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
                  ExecStart = "${cfg.package}/bin/darkwall generate";
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
                  ExecStart = "${cfg.package}/bin/darkwall generate";
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
            python3Packages.websocket-client
            python3Packages.astral
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
          program = "${darkwall-comfyui}/bin/darkwall";
        };
        
        # Formatter for this flake
        formatter = pkgs.nixfmt;
      });
}
