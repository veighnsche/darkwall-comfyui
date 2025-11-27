#!/bin/bash
# Installation script for DarkWall ComfyUI systemd service and timer

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_error "This script should not be run as root. Run as a regular user."
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

print_status "Installing DarkWall ComfyUI systemd service..."

# Check if generate-wallpaper-once is available
if ! command -v generate-wallpaper-once &> /dev/null; then
    print_error "generate-wallpaper-once command not found."
    print_error "Please install the package first using: nix build .#darkwall-comfyui"
    exit 1
fi

# Create systemd user directory
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

# Copy service and timer files
print_status "Installing systemd files to $SYSTEMD_USER_DIR"
cp "$PROJECT_DIR/systemd/darkwall-comfyui.service" "$SYSTEMD_USER_DIR/"
cp "$PROJECT_DIR/systemd/darkwall-comfyui.timer" "$SYSTEMD_USER_DIR/"

# Update service file with correct user
sed -i "s/User=%i/User=$USER/g" "$SYSTEMD_USER_DIR/darkwall-comfyui.service"
sed -i "s/Group=%i/Group=$(id -gn)/g" "$SYSTEMD_USER_DIR/darkwall-comfyui.service"

# Reload systemd daemon
print_status "Reloading systemd daemon"
systemctl --user daemon-reload

# Enable and start the timer
print_status "Enabling and starting timer"
systemctl --user enable darkwall-comfyui.timer
systemctl --user start darkwall-comfyui.timer

# Check status
print_status "Checking timer status"
if systemctl --user is-active --quiet darkwall-comfyui.timer; then
    print_status "Timer is active and running"
    systemctl --user list-timers --all darkwall-comfyui.timer
else
    print_error "Timer failed to start"
    systemctl --user status darkwall-comfyui.timer
    exit 1
fi

print_status "Installation complete!"
print_status "The wallpaper will now rotate automatically."
print_status ""
print_status "To check the timer status: systemctl --user status darkwall-comfyui.timer"
print_status "To check the service logs: journalctl --user -u darkwall-comfyui.service"
print_status "To disable automatic rotation: systemctl --user disable darkwall-comfyui.timer"
print_status ""
print_status "To manually generate a wallpaper: generate-wallpaper-once generate"
print_status "To generate for all monitors: generate-wallpaper-once generate-all"
