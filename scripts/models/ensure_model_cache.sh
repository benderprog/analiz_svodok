#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

CACHE_MODE="${MODEL_CACHE_MODE:-download}"
LOCK_FILE="$REPO_ROOT/models/model_lock.json"
CACHE_DIR="$REPO_ROOT/models/hf"
DEFAULT_MODEL_NAME="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

REFRESH="0"
for arg in "$@"; do
  case "$arg" in
    --refresh)
      REFRESH="1"
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: ensure_model_cache.sh [--refresh]

Options:
  --refresh    Update model revision to the latest main commit.

Environment:
  SEMANTIC_MODEL_NAME   Hugging Face repo id (e.g. sentence-transformers/...).
  MODEL_CACHE_MODE      download|local (default: download).
  REFRESH_MODEL_LOCK    Set to 1 to refresh the lock.
USAGE
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ "${REFRESH_MODEL_LOCK:-0}" == "1" ]]; then
  REFRESH="1"
fi

MODEL_NAME="${SEMANTIC_MODEL_NAME:-}"
if [[ -z "$MODEL_NAME" && -f "$REPO_ROOT/.env.example" ]]; then
  MODEL_NAME="$(grep -E '^SEMANTIC_MODEL_NAME=' "$REPO_ROOT/.env.example" | head -n1 | cut -d= -f2-)"
fi
MODEL_NAME="${MODEL_NAME:-$DEFAULT_MODEL_NAME}"

mkdir -p "$CACHE_DIR"

if [[ "$CACHE_MODE" == "download" ]]; then
  docker run --rm \
    -e HF_HUB_DISABLE_TELEMETRY=1 \
    -e MODEL_NAME="$MODEL_NAME" \
    -e MODEL_CACHE_MODE="$CACHE_MODE" \
    -e CACHE_DIR="/work/models/hf" \
    -e LOCK_FILE="/work/models/model_lock.json" \
    -e REFRESH="$REFRESH" \
    -v "$REPO_ROOT:/work" \
    -w /work \
    python:3.11-slim \
    bash -c "pip install --no-cache-dir huggingface_hub >/dev/null && python /work/scripts/models/ensure_model_cache.py"
elif [[ "$CACHE_MODE" == "local" ]]; then
  docker run --rm \
    -e MODEL_NAME="$MODEL_NAME" \
    -e MODEL_CACHE_MODE="$CACHE_MODE" \
    -e CACHE_DIR="/work/models/hf" \
    -e LOCK_FILE="/work/models/model_lock.json" \
    -e REFRESH="$REFRESH" \
    -v "$REPO_ROOT:/work" \
    -w /work \
    python:3.11-slim \
    python /work/scripts/models/ensure_model_cache.py
else
  echo "Unknown MODEL_CACHE_MODE: $CACHE_MODE" >&2
  exit 1
fi
