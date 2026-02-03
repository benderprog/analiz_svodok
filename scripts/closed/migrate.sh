#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.closed.yml}"

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

docker compose -f "$COMPOSE_FILE" exec -T web python manage.py migrate
