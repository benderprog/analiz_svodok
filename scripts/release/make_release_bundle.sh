#!/usr/bin/env bash
set -euo pipefail

VERSION="${APP_VERSION:-}"
if [[ -z "$VERSION" ]]; then
  if git rev-parse --short HEAD >/dev/null 2>&1; then
    VERSION="$(git rev-parse --short HEAD)"
  else
    VERSION="dev"
  fi
fi

DIST_DIR="dist"
BUNDLE_NAME="analiz_svodok_images_${VERSION}.tar"

mkdir -p "$DIST_DIR"

IMAGE_WEB="analiz_svodok_web:${VERSION}"
IMAGE_CELERY="analiz_svodok_celery:${VERSION}"

DOCKER_BUILDKIT=1 docker build --build-arg "SEMANTIC_MODEL_NAME=${SEMANTIC_MODEL_NAME:-intfloat/multilingual-e5-large}" -t "$IMAGE_WEB" .

docker tag "$IMAGE_WEB" "$IMAGE_CELERY"

docker save -o "$DIST_DIR/$BUNDLE_NAME" "$IMAGE_WEB" "$IMAGE_CELERY"

cp docker-compose.closed.yml "$DIST_DIR/"
cp .env.example "$DIST_DIR/"
cp docs/CLOSED_CONTOUR_DEPLOY.md "$DIST_DIR/"
mkdir -p "$DIST_DIR/scripts/closed"
cp scripts/closed/*.sh "$DIST_DIR/scripts/closed/"

(
  cd "$DIST_DIR"
  sha256sum "$BUNDLE_NAME" docker-compose.closed.yml .env.example CLOSED_CONTOUR_DEPLOY.md \
    scripts/closed/*.sh > SHA256SUMS
)

echo "Release bundle created at $DIST_DIR/$BUNDLE_NAME"
