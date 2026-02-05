#!/usr/bin/env bash
set -euo pipefail

if [[ -f .env.local ]]; then
  set -a
  . ./.env.local
  set +a
elif [[ -f .env ]]; then
  set -a
  . ./.env
  set +a
fi

if [[ -z "${PORTAL_DB:-}" || -z "${PORTAL_USER:-}" || -z "${PORTAL_PASSWORD:-}" ]]; then
  echo "PORTAL_DB/PORTAL_USER/PORTAL_PASSWORD must be set (see .env.local.example)." >&2
  exit 1
fi

PORTAL_HOST="${PORTAL_HOST:-127.0.0.1}"
PORTAL_PORT="${PORTAL_PORT:-5432}"

psql_base=(
  psql
  -h "$PORTAL_HOST"
  -p "$PORTAL_PORT"
  -U "$PORTAL_USER"
  -d "$PORTAL_DB"
  -v ON_ERROR_STOP=1
  -t
  -A
)

trim() {
  echo "$1" | xargs
}

missing_tables="$(PGPASSWORD="$PORTAL_PASSWORD" "${psql_base[@]}" -c \
  "SELECT string_agg(name, ',') FROM (VALUES ('portal_events')) AS t(name)
   WHERE to_regclass('public.' || name) IS NULL;")"
missing_tables="$(trim "$missing_tables")"
if [[ -n "$missing_tables" ]]; then
  echo "Missing tables: $missing_tables" >&2
  exit 1
fi

portal_id_type="$(PGPASSWORD="$PORTAL_PASSWORD" "${psql_base[@]}" -c \
  "SELECT pg_typeof(id)::text FROM portal_events LIMIT 1;")"
portal_id_type="$(trim "$portal_id_type")"
if [[ "$portal_id_type" != "uuid" ]]; then
  echo "Expected portal_events.id type uuid, got: ${portal_id_type:-empty}" >&2
  exit 1
fi

portal_subdivision_type="$(PGPASSWORD="$PORTAL_PASSWORD" "${psql_base[@]}" -c \
  "SELECT pg_typeof(subdivision_id)::text FROM portal_events LIMIT 1;")"
portal_subdivision_type="$(trim "$portal_subdivision_type")"
if [[ "$portal_subdivision_type" != "uuid" ]]; then
  echo "Expected portal_events.subdivision_id type uuid, got: ${portal_subdivision_type:-empty}" >&2
  exit 1
fi

portal_offenders_type="$(PGPASSWORD="$PORTAL_PASSWORD" "${psql_base[@]}" -c \
  "SELECT pg_typeof(offenders)::text FROM portal_events LIMIT 1;")"
portal_offenders_type="$(trim "$portal_offenders_type")"
if [[ "$portal_offenders_type" != "jsonb" ]]; then
  echo "Expected portal_events.offenders type jsonb, got: ${portal_offenders_type:-empty}" >&2
  exit 1
fi

events_count="$(PGPASSWORD="$PORTAL_PASSWORD" "${psql_base[@]}" -c "SELECT count(*) FROM portal_events;")"

echo "Portal events count: $(trim "$events_count")"
echo "Local portal verification completed."
