#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.closed.yml}"

docker compose -f "$COMPOSE_FILE" down "$@"
