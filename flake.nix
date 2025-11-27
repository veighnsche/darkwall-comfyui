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
        
        # Python package derivation
        darkwall-comfyui = pkgs.python3Packages.buildPythonPackage rec {
          pname = "darkwall-comfyui";
          version = "0.1.0";
          
          src = ./.;
          
          pyproject = true;
          
          propagatedBuildInputs = with pkgs.python3Packages; [
            requests
            tomli
            tomli-w
          ];
          
          # Optional dev dependencies for the shell
          nativeBuildInputs = with pkgs.python3Packages; [
            setuptools
            wheel
            pkgs.makeWrapper
          ];
          
          postInstall = ''
            # Install config templates to share directory
            mkdir -p $out/share/darkwall-comfyui/config
            
            # Debug: Check what's in $src/config
            echo "DEBUG: Checking $src/config:" >&2
            ls -la $src/config/ >&2 || echo "No $src/config directory" >&2
            
            # Check if config directory exists and copy files
            if [ -d "$src/config" ]; then
              echo "DEBUG: Copying from $src/config to $out/share/darkwall-comfyui/config/" >&2
              cp -r $src/config/. $out/share/darkwall-comfyui/config/ || echo "DEBUG: cp failed with exit code $?" >&2
              echo "DEBUG: Contents after copy:" >&2
              ls -la $out/share/darkwall-comfyui/config/ >&2
              echo "Config templates copied from $src/config" >&2
            else
              echo "Warning: Config directory not found at $src/config" >&2
              # Create minimal config structure
              echo "# Config file will be created during initialization" > $out/share/darkwall-comfyui/config/config.toml
              mkdir -p $out/share/darkwall-comfyui/config/atoms
            fi
            
            # Use makeWrapper to set environment variable
            wrapProgram $out/bin/generate-wallpaper-once \
              --set DARKWALL_CONFIG_TEMPLATES "$out/share/darkwall-comfyui/config"
          '';
          
          meta = {
            description = "Deterministic dark-mode wallpaper generator using ComfyUI";
            homepage = "https://github.com/vince/darkwall-comfyui";
            license = pkgs.lib.licenses.mit;
            platforms = pkgs.lib.platforms.all;
            mainProgram = "generate-wallpaper-once";
          };
        };
        
        # Development shell with additional tooling
        devShell = pkgs.mkShell {
          buildInputs = with pkgs; [
            python3
            python3Packages.requests
            python3Packages.pytest
            python3Packages.black
            python3Packages.isort
            python3Packages.mypy
          ];
          
          shellHook = ''
            echo "🎨 DarkWall ComfyUI Development Environment"
            echo "Available commands:"
            echo "  - python -m darkwall_comfyui.main --help"
            echo "  - pytest                          # Run tests"
            echo "  - black src/                      # Format code"
            echo "  - isort src/                      # Sort imports"
            echo "  - mypy src/                       # Type checking"
            echo ""
          '';
        };
        
      in {
        # Package output
        packages = {
          default = darkwall-comfyui;
          darkwall-comfyui = darkwall-comfyui;
        };
        
        # Development shell
        devShells.default = devShell;
        
        # App entry point for convenience
        apps.default = {
          type = "app";
          program = "${darkwall-comfyui}/bin/generate-wallpaper-once";
        };
      });
}
