#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER="${CRA_CONTAINER:-$(cat "$ROOT/.cra_container" 2>/dev/null || true)}"
if [[ -z "$CONTAINER" ]]; then
  echo "CRA container is not known. Run scripts/docker_run.sh first or set CRA_CONTAINER." >&2
  exit 2
fi

if [[ $# -eq 0 ]]; then
  set -- bash
fi

docker exec -w /workspace/source "$CONTAINER" "$@"
