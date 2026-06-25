#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_NAME="cra-$(basename "$ROOT" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_.-')"
CONTAINER="${CRA_CONTAINER:-$DEFAULT_NAME}"
IMAGE="${CRA_IMAGE:-$(cat "$ROOT/.cra_image" 2>/dev/null || true)}"
if [[ -z "$IMAGE" ]]; then
  IMAGE="$DEFAULT_NAME:latest"
fi

ENV_ARGS=()
if [[ -f "$ROOT/.cra_env" ]]; then
  ENV_ARGS+=(--env-file "$ROOT/.cra_env")
fi

EXTRA_ARGS=()
if [[ -n "${CRA_DOCKER_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  EXTRA_ARGS=(${CRA_DOCKER_ARGS})
fi

mkdir -p "$ROOT/runs" "$ROOT/outputs" "$ROOT/patches"

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

echo "Starting container: $CONTAINER"
echo "Image: $IMAGE"
docker run -d \
  --name "$CONTAINER" \
  --workdir /workspace/source \
  -v "$ROOT:/workspace" \
  -e HOME=/tmp/cra-home \
  "${ENV_ARGS[@]}" \
  "${EXTRA_ARGS[@]}" \
  "$IMAGE" \
  sleep infinity

printf '%s\n' "$CONTAINER" > "$ROOT/.cra_container"
