#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$project_dir" != "/home/hornet/svgAsiaHornetMonitor" ]]; then
  echo "This installer expects /home/hornet/svgAsiaHornetMonitor." >&2
  exit 1
fi

uv run hornet-monitor --setup-auth
sudo install -m 0644 deploy/hornet-monitor.service /etc/systemd/system/hornet-monitor.service
sudo install -m 0440 deploy/hornet-monitor-sudoers /etc/sudoers.d/hornet-monitor
sudo systemctl daemon-reload
sudo systemctl enable --now hornet-monitor.service
echo "Service installed. Open http://hornet.local:8000 and sign in."
