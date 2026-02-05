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
  "SELECT string_agg(name, ',') FROM (VALUES ('subdivision'), ('events'), ('offenders')) AS t(name)
   WHERE to_regclass('public.' || name) IS NULL;")"
missing_tables="$(trim "$missing_tables")"
if [[ -n "$missing_tables" ]]; then
  echo "Missing tables: $missing_tables" >&2
  exit 1
fi

subdivision_id_type="$(PGPASSWORD="$PORTAL_PASSWORD" "${psql_base[@]}" -c \
  "SELECT pg_typeof(id)::text FROM subdivision LIMIT 1;")"
subdivision_id_type="$(trim "$subdivision_id_type")"
if [[ "$subdivision_id_type" != "uuid" ]]; then
  echo "Expected subdivision.id type uuid, got: ${subdivision_id_type:-empty}" >&2
  exit 1
fi

event_subdivision_type="$(PGPASSWORD="$PORTAL_PASSWORD" "${psql_base[@]}" -c \
  "SELECT pg_typeof(find_subdivision_unit_id)::text FROM events LIMIT 1;")"
event_subdivision_type="$(trim "$event_subdivision_type")"
if [[ "$event_subdivision_type" != "uuid" ]]; then
  echo "Expected events.find_subdivision_unit_id type uuid, got: ${event_subdivision_type:-empty}" >&2
  exit 1
fi

events_missing_subdivision="$(PGPASSWORD="$PORTAL_PASSWORD" "${psql_base[@]}" -c \
  "SELECT count(*) FROM events e LEFT JOIN subdivision s ON s.id = e.find_subdivision_unit_id WHERE s.id IS NULL;")"
events_missing_subdivision="$(trim "$events_missing_subdivision")"
if [[ "$events_missing_subdivision" != "0" ]]; then
  echo "Events missing subdivision references: $events_missing_subdivision" >&2
  exit 1
fi

offenders_missing_events="$(PGPASSWORD="$PORTAL_PASSWORD" "${psql_base[@]}" -c \
  "SELECT count(*) FROM offenders o LEFT JOIN events e ON e.id = o.event_id WHERE e.id IS NULL;")"
offenders_missing_events="$(trim "$offenders_missing_events")"
if [[ "$offenders_missing_events" != "0" ]]; then
  echo "Offenders missing event references: $offenders_missing_events" >&2
  exit 1
fi

subdivision_count="$(PGPASSWORD="$PORTAL_PASSWORD" "${psql_base[@]}" -c "SELECT count(*) FROM subdivision;")"
events_count="$(PGPASSWORD="$PORTAL_PASSWORD" "${psql_base[@]}" -c "SELECT count(*) FROM events;")"
offenders_count="$(PGPASSWORD="$PORTAL_PASSWORD" "${psql_base[@]}" -c "SELECT count(*) FROM offenders;")"

echo "Subdivision count: $(trim "$subdivision_count")"
echo "Events count: $(trim "$events_count")"
echo "Offenders count: $(trim "$offenders_count")"
echo "Local portal verification completed."
