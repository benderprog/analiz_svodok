#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.closed.yml}"
BACKUP_DIR="${BACKUP_DIR:-./artifacts}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_PATH="${1:-${BACKUP_DIR}/app_db_backup_${TIMESTAMP}.dump}"

mkdir -p "$(dirname "$OUTPUT_PATH")"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

docker compose -f "$COMPOSE_FILE" exec -T app-postgres \
  pg_dump -Fc -U "${POSTGRES_USER}" "${POSTGRES_DB}" > "$OUTPUT_PATH"

echo "Backup saved to $OUTPUT_PATH"
