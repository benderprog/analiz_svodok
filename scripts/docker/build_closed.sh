#!/usr/bin/env bash
set -euo pipefail

PREWARM_MODEL="false"

usage() {
  cat <<'USAGE'
Usage: build_closed.sh [--prewarm|--no-prewarm]

Options:
  --prewarm     Prewarm the semantic model during build (PREWARM_MODEL=true)
  --no-prewarm  Do not prewarm the semantic model (default)
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --prewarm)
      PREWARM_MODEL="true"
      ;;
    --no-prewarm)
      PREWARM_MODEL="false"
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

docker compose -f docker-compose.closed.yml build \
  --build-arg PREWARM_MODEL="${PREWARM_MODEL}"

docker compose -f docker-compose.closed.yml images
