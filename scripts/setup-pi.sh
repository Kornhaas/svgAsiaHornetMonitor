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
sudo apt install -y curl git

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
uv sync --locked --no-dev
bash scripts/install-service.sh
