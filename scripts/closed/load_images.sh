#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

IMAGES_DIR="${IMAGES_DIR:-$REPO_ROOT/images}"

if [[ ! -d "$IMAGES_DIR" ]]; then
  echo "Images directory not found: $IMAGES_DIR" >&2
  exit 1
fi

if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a
  . "$REPO_ROOT/.env"
  set +a
fi

detect_tag_from_archive() {
  mapfile -t tag_archives < <(find "$IMAGES_DIR" -maxdepth 1 -type f -name "images_*.tar" -print)
  if [[ "${#tag_archives[@]}" -eq 0 ]]; then
    echo "No release image archive found in $IMAGES_DIR (expected images_<TAG>.tar)." >&2
    exit 1
  fi
  if [[ "${#tag_archives[@]}" -gt 1 ]]; then
    echo "Multiple release image archives found in $IMAGES_DIR; expected one." >&2
    printf ' - %s\n' "${tag_archives[@]}" >&2
    exit 1
  fi

  local archive_name
  archive_name="$(basename "${tag_archives[0]}")"
  local detected_tag="${archive_name#images_}"
  detected_tag="${detected_tag%.tar}"
  if [[ -z "$detected_tag" || "$detected_tag" == "$archive_name" ]]; then
    echo "Unable to detect TAG from archive name: $archive_name" >&2
    exit 1
  fi
  echo "$detected_tag"
}

TAG="${TAG:-${APP_VERSION:-}}"
if [[ -z "${TAG:-}" ]]; then
  TAG="$(detect_tag_from_archive)"
  echo "Detected TAG=$TAG"
fi

if [[ -f "$REPO_ROOT/.env" ]]; then
  if ! rg -q '^TAG=' "$REPO_ROOT/.env"; then
    printf '\nTAG=%s\n' "$TAG" >> "$REPO_ROOT/.env"
    echo "Added TAG=$TAG to $REPO_ROOT/.env"
  fi
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
