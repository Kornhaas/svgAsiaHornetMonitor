#!/usr/bin/env bash
# One-time installer for Raspberry Pi OS. Run as the "hornet" user.
set -euo pipefail

repo_url="https://github.com/Kornhaas/svgAsiaHornetMonitor.git"
project_dir="$HOME/svgAsiaHornetMonitor"

if [[ "$(id -un)" != "hornet" ]]; then
  echo "Please run this setup as the 'hornet' user." >&2
  exit 1
fi

sudo apt update
# System packages needed by the installer, USB camera diagnostics, and the
# OpenCV wheel. Python dependencies are installed below from uv.lock.
sudo apt install -y ca-certificates curl git libgl1 libglib2.0-0 libgomp1 v4l-utils python3-torch python3-torchvision
sudo usermod -aG video hornet

if [[ ! -x "$HOME/.local/bin/uv" ]]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

if [[ -d "$project_dir/.git" ]]; then
  git -C "$project_dir" pull --ff-only origin main
else
  git clone "$repo_url" "$project_dir"
fi

cd "$project_dir"
# install-service prepares the system-site Pi runtime, then enables the unit.
# install-service enables the unit and starts it immediately; systemd will
# consequently start it again after every Raspberry Pi reboot.
bash scripts/install-service.sh
