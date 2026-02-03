#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

IMAGES_DIR="${IMAGES_DIR:-$REPO_ROOT/images}"

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

TAG="${TAG:-}"
if [[ -z "${TAG:-}" ]]; then
  echo "TAG is not set. Add TAG=... to .env before running this script." >&2
  exit 1
fi

if [[ ! -d "$IMAGES_DIR" ]]; then
  echo "Images directory not found: $IMAGES_DIR" >&2
  exit 1
fi

mapfile -t image_archives < <(find "$IMAGES_DIR" -maxdepth 1 -type f -name "*.tar" -print)
if [[ "${#image_archives[@]}" -eq 0 ]]; then
  echo "No image archives found in $IMAGES_DIR" >&2
  exit 1
fi

for archive in "${image_archives[@]}"; do
  echo "Loading $archive"
  docker load -i "$archive"
done

required_images=(
  "analiz_svodok_web:${TAG}"
  "analiz_svodok_celery:${TAG}"
  "postgres:15-alpine"
  "redis:7-alpine"
)

missing=0
for image in "${required_images[@]}"; do
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "Missing image after load: $image" >&2
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

echo "All required images are loaded."
