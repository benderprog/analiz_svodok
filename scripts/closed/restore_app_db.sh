#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.closed.yml}"
DUMP_PATH="${1:-}"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

TAG="${TAG:-}"
if [[ -z "${TAG:-}" ]]; then
  echo "TAG is not set. Add TAG=... to .env before running this script." >&2
  exit 1
fi

if [[ -z "$DUMP_PATH" ]]; then
  echo "Usage: $0 <dump_path>" >&2
  exit 1
fi

if [[ ! -f "$DUMP_PATH" ]]; then
  echo "Dump file not found: $DUMP_PATH" >&2
  exit 1
fi

docker compose -f "$COMPOSE_FILE" exec -T app-postgres \
  pg_restore --clean --if-exists -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" < "$DUMP_PATH"

printf 'Restore completed from %s\n' "$DUMP_PATH"
