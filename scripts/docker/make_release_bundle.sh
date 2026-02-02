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
mkdir -p "$BUNDLE_DIR"

IMAGES=$(docker compose -f "$REPO_ROOT/docker-compose.closed.yml" config --images | sort -u)
if [[ -z "$IMAGES" ]]; then
  echo "No images found in docker-compose.closed.yml" >&2
  exit 1
fi

docker save $IMAGES -o "$BUNDLE_DIR/analiz_svodok_images_${VERSION}.tar"

cp "$REPO_ROOT/docker-compose.closed.yml" "$BUNDLE_DIR/"
cp "$REPO_ROOT/.env.example" "$BUNDLE_DIR/"

if [[ -f "$REPO_ROOT/docs/CLOSED_CONTOUR_DEPLOY.md" ]]; then
  mkdir -p "$BUNDLE_DIR/docs"
  cp "$REPO_ROOT/docs/CLOSED_CONTOUR_DEPLOY.md" "$BUNDLE_DIR/docs/"
fi

if [[ -d "$REPO_ROOT/scripts/closed" ]]; then
  mkdir -p "$BUNDLE_DIR/scripts"
  cp -R "$REPO_ROOT/scripts/closed" "$BUNDLE_DIR/scripts/"
fi

if [[ -d "$REPO_ROOT/scripts/docker" ]]; then
  mkdir -p "$BUNDLE_DIR/scripts"
  cp -R "$REPO_ROOT/scripts/docker" "$BUNDLE_DIR/scripts/"
fi

(
  cd "$BUNDLE_DIR"
  files=(
    "analiz_svodok_images_${VERSION}.tar"
    "docker-compose.closed.yml"
    ".env.example"
  )

  if [[ -f "docs/CLOSED_CONTOUR_DEPLOY.md" ]]; then
    files+=("docs/CLOSED_CONTOUR_DEPLOY.md")
  fi

  if [[ -d scripts/closed ]]; then
    while IFS= read -r -d '' file; do
      files+=("${file#./}")
    done < <(find scripts/closed -type f -print0)
  fi

  if [[ -d scripts/docker ]]; then
    while IFS= read -r -d '' file; do
      files+=("${file#./}")
    done < <(find scripts/docker -type f -print0)
  fi

  printf '%s\n' "${files[@]}" | sort -u | xargs -r sha256sum > SHA256SUMS
)

echo "Release bundle created at $BUNDLE_DIR"
