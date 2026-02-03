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

required_images=(
  "analiz_svodok_web:${TAG}"
  "postgres:15-alpine"
  "redis:7-alpine"
)

missing=0
for image in "${required_images[@]}"; do
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "Missing image: $image" >&2
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  echo "Required images are missing. Run ./scripts/closed/load_images.sh first." >&2
  exit 1
fi

wait_for_health() {
  local service="$1"
  local timeout="${2:-60}"
  local elapsed=0
  local container_id

  container_id=$(docker compose -f "$COMPOSE_FILE" ps -q "$service")
  if [[ -z "$container_id" ]]; then
    echo "Container for service '$service' not found." >&2
    exit 1
  fi

  while true; do
    local status
    status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id")
    if [[ "$status" == "healthy" ]]; then
      echo "Service '$service' is healthy."
      break
    fi
    if [[ "$elapsed" -ge "$timeout" ]]; then
      echo "Timed out waiting for '$service' to become healthy (last status: $status)." >&2
      exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done
}

echo "Starting database and redis services..."
docker compose -f "$COMPOSE_FILE" up -d postgres portal-postgres redis

wait_for_health postgres
wait_for_health portal-postgres
wait_for_health redis

echo "Running Django migrations..."
docker compose -f "$COMPOSE_FILE" run --rm web python manage.py migrate

echo "Ensuring admin user exists..."
docker compose -f "$COMPOSE_FILE" run --rm web python manage.py shell -c "from django.contrib.auth import get_user_model; import os; User=get_user_model(); login=os.environ.get('APP_ADMIN_LOGIN'); password=os.environ.get('APP_ADMIN_PASSWORD'); user=User.objects.filter(login=login).first();
if user:
    print('Admin already exists:', login)
else:
    user=User.objects.create_superuser(login=login, password=password)
    print('Admin created:', login)"

echo "Bootstrapping application reference data..."
docker compose -f "$COMPOSE_FILE" run --rm web python manage.py bootstrap_local_app

if [[ -d seed ]]; then
  if [[ -f seed/portal_schema.sql ]]; then
    echo "Seeding portal database schema..."
    docker compose -f "$COMPOSE_FILE" exec -T portal-postgres psql -U "$PORTAL_USER" -d "$PORTAL_DB" -f /seed/portal_schema.sql
  fi

  if [[ -f seed/portal_data.sql ]]; then
    echo "Seeding portal database data..."
    docker compose -f "$COMPOSE_FILE" exec -T portal-postgres psql -U "$PORTAL_USER" -d "$PORTAL_DB" -f /seed/portal_data.sql
  fi
else
  echo "Seed directory not found; skipping portal seed SQL."
fi

echo "Seed completed."
