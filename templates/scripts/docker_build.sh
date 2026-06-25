#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_TAG="cra-repro-$(basename "$ROOT" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_.-')"
IMAGE="${CRA_IMAGE:-$DEFAULT_TAG:latest}"
DOCKERFILE="${CRA_DOCKERFILE:-$ROOT/docker/Dockerfile.repro}"

mkdir -p "$ROOT/runs" "$ROOT/outputs" "$ROOT/patches"

echo "Building image: $IMAGE"
echo "Dockerfile: $DOCKERFILE"
docker build -f "$DOCKERFILE" -t "$IMAGE" "$ROOT"
printf '%s\n' "$IMAGE" > "$ROOT/.cra_image"
