#!/usr/bin/env bash
set -euo pipefail

PREWARM="false"
DEFAULT_MODEL_NAME="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

usage() {
  cat <<'USAGE'
Usage: build_closed.sh [--prewarm|--no-prewarm]

Options:
  --prewarm     Prewarm the semantic model during build (PREWARM=true)
  --no-prewarm  Do not prewarm the semantic model (default)
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --prewarm)
      PREWARM="true"
      ;;
    --no-prewarm)
      PREWARM="false"
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

VERSION="${APP_VERSION:-}"
if [[ -z "$VERSION" ]]; then
  if git rev-parse --short HEAD >/dev/null 2>&1; then
    VERSION="$(git rev-parse --short HEAD)"
  else
    VERSION="dev"
  fi
fi

export APP_VERSION="$VERSION"

MODEL_NAME="${SEMANTIC_MODEL_NAME:-$DEFAULT_MODEL_NAME}"

docker compose -f docker-compose.closed.yml build \
  --build-arg PREWARM="${PREWARM}" \
  --build-arg SEMANTIC_MODEL_NAME="${MODEL_NAME}"

docker compose -f docker-compose.closed.yml images
