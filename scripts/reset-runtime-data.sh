#!/usr/bin/env bash
# Remove locally collected monitor data without touching configuration or source code.
set -euo pipefail

include_models=false
include_backups=false
confirmed=false

for argument in "$@"; do
  case "$argument" in
    --yes) confirmed=true ;;
    --include-models) include_models=true ;;
    --include-backups) include_backups=true ;;
    --help)
      cat <<'USAGE'
Usage: bash scripts/reset-runtime-data.sh --yes [--include-models] [--include-backups]

Deletes collected event images, captures, annotations, predictions, activity history,
background reference images, and exported datasets from this project only.

Models and backups are retained unless their explicit option is supplied.
USAGE
      exit 0
      ;;
    *)
      echo "Unknown option: $argument" >&2
      exit 2
      ;;
  esac
done

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
project_dir="$(cd "$script_dir/.." && pwd -P)"
data_dir="$project_dir/data"

if [[ ! -f "$project_dir/pyproject.toml" || ! -d "$data_dir" ]]; then
  echo "Refusing to run outside an Asia Hornet Monitor project." >&2
  exit 1
fi

targets=(
  "$data_dir/events"
  "$data_dir/captures"
  "$data_dir/datasets"
  "$data_dir/annotations.jsonl"
  "$data_dir/predictions.jsonl"
  "$data_dir/activity.jsonl"
  "$data_dir/background.jpg"
  "$data_dir/background.json"
)

if "$include_models"; then
  targets+=("$data_dir/models")
fi
if "$include_backups"; then
  targets+=("$data_dir/backups")
fi

echo "The following local runtime data will be permanently deleted:"
printf '  %s\n' "${targets[@]}"
if ! "$confirmed"; then
  echo "Nothing was deleted. Run again with --yes to confirm." >&2
  exit 2
fi

for target in "${targets[@]}"; do
  case "$target" in
    "$data_dir"/*) rm -rf -- "$target" ;;
    *)
      echo "Unsafe deletion target refused: $target" >&2
      exit 1
      ;;
  esac
done

echo "Runtime data reset completed. Configuration, source code, models, and backups were retained."
