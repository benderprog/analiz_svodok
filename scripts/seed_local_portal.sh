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

seed_sql="seed/portal_data.sql"
docx_path=""
if [[ -f fixtures/test_svodka_semantic3.docx ]]; then
  docx_path="fixtures/test_svodka_semantic3.docx"
else
  for candidate in fixtures/*.docx; do
    if [[ -f "$candidate" ]]; then
      docx_path="$candidate"
      break
    fi
  done
fi

if [[ -n "$docx_path" ]]; then
  echo "Generating portal seed SQL from DOCX: $docx_path"
  python manage.py generate_portal_seed_from_docx \
    --docx "$docx_path" \
    --output "seed/portal_data_generated.sql"
  seed_sql="seed/portal_data_generated.sql"
fi

if [[ -f seed/portal_schema.sql ]]; then
  echo "Applying portal schema..."
  PGPASSWORD="$PORTAL_PASSWORD" psql \
    -h "$PORTAL_HOST" \
    -p "$PORTAL_PORT" \
    -U "$PORTAL_USER" \
    -d "$PORTAL_DB" \
    -v ON_ERROR_STOP=1 \
    -f seed/portal_schema.sql
fi

if [[ -f "$seed_sql" ]]; then
  echo "Seeding portal database data from $seed_sql..."
  PGPASSWORD="$PORTAL_PASSWORD" psql \
    -h "$PORTAL_HOST" \
    -p "$PORTAL_PORT" \
    -U "$PORTAL_USER" \
    -d "$PORTAL_DB" \
    -v ON_ERROR_STOP=1 \
    -f "$seed_sql"
else
  echo "Seed SQL not found; skipping portal data seed." >&2
  exit 1
fi

echo "Local portal seed completed."
