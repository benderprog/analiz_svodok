#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.offline.yml}"

docker compose -f "$COMPOSE_FILE" logs -f --tail=200 ${*:-web celery}
