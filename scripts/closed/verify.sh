#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.offline.yml}"

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

services=(postgres portal-postgres redis web)

for service in "${services[@]}"; do
  container_id=$(docker compose -f "$COMPOSE_FILE" ps -q "$service")
  if [[ -z "$container_id" ]]; then
    echo "Service '$service' is not running." >&2
    exit 1
  fi

  status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id")
  if [[ "$status" != "healthy" && "$status" != "running" ]]; then
    echo "Service '$service' is not healthy (status: $status)." >&2
    exit 1
  fi
  echo "Service '$service' status: $status"

done

echo "Checking HTTP endpoint..."
if ! curl -fsS http://localhost:8000/help >/dev/null; then
  echo "Web endpoint check failed: http://localhost:8000/help" >&2
  exit 1
fi

echo "Verify OK."
