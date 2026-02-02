#!/usr/bin/env bash
set -euo pipefail

MODEL_NAME="intfloat/multilingual-e5-large"
MODEL_DIR_MAIN="models--intfloat--multilingual-e5-large"
MODEL_DIR_ST="models--sentence-transformers--intfloat__multilingual-e5-large"
TORCH_ST_DIR="intfloat_multilingual-e5-large"

DRY_RUN=true

usage() {
  cat <<'USAGE'
Usage: purge_heavy_model_cache.sh [--yes]

Options:
  --yes   реально удалить кэш (по умолчанию dry-run)
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --yes)
      DRY_RUN=false
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage
      exit 1
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

maybe_add_target() {
  local path="$1"
  if [[ -n "$path" && -d "$path" ]]; then
    TARGETS+=("$path")
  fi
}

report_size() {
  local path="$1"
  du -sh "$path" 2>/dev/null | awk '{print $1}'
}

TARGETS=()

for cache_root in "${HF_HOME:-}" "${TRANSFORMERS_CACHE:-}"; do
  if [[ -n "$cache_root" ]]; then
    if [[ "$cache_root" = ".hf" || "$cache_root" = "./.hf" ]]; then
      cache_root="$ROOT_DIR/.hf"
    fi
    if [[ "$cache_root" = "$ROOT_DIR/.hf" || "$cache_root" = "$ROOT_DIR/.hf/" ]]; then
      maybe_add_target "$ROOT_DIR/.hf/hub/$MODEL_DIR_MAIN"
      maybe_add_target "$ROOT_DIR/.hf/hub/$MODEL_DIR_ST"
      maybe_add_target "$ROOT_DIR/.hf/torch/sentence_transformers/$TORCH_ST_DIR"
    fi
  fi
done

maybe_add_target "$HOME/.cache/huggingface/hub/$MODEL_DIR_MAIN"
maybe_add_target "$HOME/.cache/huggingface/hub/$MODEL_DIR_ST"
maybe_add_target "$HOME/.cache/torch/sentence_transformers/$TORCH_ST_DIR"

maybe_add_target "/models/hf/hub/$MODEL_DIR_MAIN"
maybe_add_target "/models/hf/hub/$MODEL_DIR_ST"
maybe_add_target "/models/hf/$MODEL_DIR_MAIN"
maybe_add_target "/models/hf/$MODEL_DIR_ST"
maybe_add_target "/models/hf/torch/sentence_transformers/$TORCH_ST_DIR"

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  echo "No cache directories found for $MODEL_NAME"
  exit 0
fi

echo "Found ${#TARGETS[@]} cache directories for $MODEL_NAME"

for target in "${TARGETS[@]}"; do
  before_size=$(report_size "$target")
  if $DRY_RUN; then
    after_size=$(report_size "$target")
    echo "[dry-run] Would remove: $target (size before: ${before_size:-unknown}, size after: ${after_size:-unknown})"
    continue
  fi

  echo "Removing: $target (size before: ${before_size:-unknown})"
  rm -rf "$target"
  if [[ -d "$target" ]]; then
    after_size=$(report_size "$target")
    echo "Still exists: $target (size after: ${after_size:-unknown})"
  else
    echo "Removed: $target"
  fi

done
