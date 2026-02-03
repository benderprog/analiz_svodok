#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PREWARM_FLAG="--no-prewarm"

usage() {
  cat <<'USAGE'
Usage: make_release_bundle.sh [--prewarm|--no-prewarm]

Options:
  --prewarm     Prewarm the semantic model during build
  --no-prewarm  Do not prewarm the semantic model (default)
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --prewarm)
      PREWARM_FLAG="--prewarm"
      ;;
    --no-prewarm)
      PREWARM_FLAG="--no-prewarm"
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

"$SCRIPT_DIR/build_closed.sh" "$PREWARM_FLAG"

BUNDLE_DIR="$REPO_ROOT/dist/release_${VERSION}"
mkdir -p "$BUNDLE_DIR/images"

IMAGES=(
  "analiz_svodok_web:${VERSION}"
  "analiz_svodok_celery:${VERSION}"
  "postgres:15-alpine"
  "redis:7-alpine"
)

docker save "${IMAGES[@]}" -o "$BUNDLE_DIR/images/images_${VERSION}.tar"

cp "$REPO_ROOT/docker-compose.offline.yml" "$BUNDLE_DIR/"
cp "$REPO_ROOT/.env.example" "$BUNDLE_DIR/"
mkdir -p "$BUNDLE_DIR/configs"
cp "$REPO_ROOT/configs/portal_queries.yaml" "$BUNDLE_DIR/configs/portal_queries.yaml"

mkdir -p "$BUNDLE_DIR/docs"
cp "$REPO_ROOT/docs/INSTALL_CLOSED.md" "$BUNDLE_DIR/docs/"

if [[ -d "$REPO_ROOT/scripts/closed" ]]; then
  mkdir -p "$BUNDLE_DIR/scripts"
  cp -R "$REPO_ROOT/scripts/closed" "$BUNDLE_DIR/scripts/"
fi

if [[ -d "$REPO_ROOT/seed" ]]; then
  mkdir -p "$BUNDLE_DIR/seed"
  cp -R "$REPO_ROOT/seed"/*.sql "$BUNDLE_DIR/seed/"
fi

if [[ -d "$REPO_ROOT/fixtures" ]]; then
  mkdir -p "$BUNDLE_DIR/fixtures"
  cp -R "$REPO_ROOT/fixtures"/* "$BUNDLE_DIR/fixtures/"
fi

(
  cd "$BUNDLE_DIR"
  files=(
    "images/images_${VERSION}.tar"
    "docker-compose.offline.yml"
    ".env.example"
    "configs/portal_queries.yaml"
    "docs/INSTALL_CLOSED.md"
  )

  if [[ -d scripts/closed ]]; then
    while IFS= read -r -d '' file; do
      files+=("${file#./}")
    done < <(find scripts/closed -type f -print0)
  fi

  if [[ -d seed ]]; then
    while IFS= read -r -d '' file; do
      files+=("${file#./}")
    done < <(find seed -type f -print0)
  fi

  if [[ -d fixtures ]]; then
    while IFS= read -r -d '' file; do
      files+=("${file#./}")
    done < <(find fixtures -type f -print0)
  fi

  printf '%s\n' "${files[@]}" | sort -u | xargs -r sha256sum > SHA256SUMS
)

echo "Release bundle created at $BUNDLE_DIR"
