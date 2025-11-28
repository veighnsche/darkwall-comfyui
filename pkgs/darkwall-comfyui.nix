{ pkgs, system ? "x86_64-linux" }:
let
  flake = builtins.getFlake "/home/vince/Projects/darkwall-comfyui";
in
flake.packages.${system}.default
