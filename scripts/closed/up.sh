#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.offline.yml}"

if [[ -f .env ]]; then
  set -a
  . .env
  set +a
fi

TAG="${TAG:-${APP_VERSION:-}}"
if [[ -z "${TAG:-}" ]]; then
  echo "TAG is not set. Export TAG or add TAG=... to .env." >&2
  exit 1
fi

required_images=(
  "analiz_svodok_web:${TAG}"
  "analiz_svodok_celery:${TAG}"
  "postgres:15-alpine"
  "redis:7-alpine"
)

missing=0
for image in "${required_images[@]}"; do
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "Missing image: $image"
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  echo "Required images are missing. Run ./scripts/closed/load_images.sh first." >&2
  exit 1
fi

docker compose -f "$COMPOSE_FILE" up -d --pull=never "$@"
