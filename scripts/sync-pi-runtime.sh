#!/usr/bin/env bash
# Build the Pi runtime around Debian's ARM CPU PyTorch, not PyPI's incompatible wheel.
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$project_dir" != "/home/hornet/svgAsiaHornetMonitor" ]]; then
  echo "This runtime setup expects /home/hornet/svgAsiaHornetMonitor." >&2
  exit 1
fi

if ! /usr/bin/python3 -c "import torch, torchvision"; then
  echo "Install python3-torch and python3-torchvision with apt before syncing the Pi runtime." >&2
  exit 1
fi

uv_binary="${HOME}/.local/bin/uv"
if [[ ! -x "$uv_binary" ]]; then
  echo "uv is not installed for the hornet user." >&2
  exit 1
fi

cd "$project_dir"
"$uv_binary" venv --clear --system-site-packages --python /usr/bin/python3 .venv
"$uv_binary" sync --locked --no-dev

venv_python="$project_dir/.venv/bin/python"
"$venv_python" -c '
import pathlib
import torch
import torchvision

venv = pathlib.Path(__import__("sys").prefix).resolve()
for package in (torch, torchvision):
    if venv not in pathlib.Path(package.__file__).resolve().parents:
        raise SystemExit("The PyPI Torch packages were not installed in the project environment.")
'
"$uv_binary" pip uninstall --python "$venv_python" torch torchvision

"$venv_python" -c '
import pathlib
import torch
import torchvision

system_packages = pathlib.Path("/usr/lib/python3/dist-packages")
for package in (torch, torchvision):
    if system_packages not in pathlib.Path(package.__file__).resolve().parents:
        raise SystemExit(f"Expected Debian package for {package.__name__}, got {package.__file__}")
print(f"Pi runtime uses Debian torch {torch.__version__} from {torch.__file__}")
'
