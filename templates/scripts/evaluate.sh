#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -z "${CRA_EVAL_CMD:-}" ]]; then
  echo "CRA_EVAL_CMD is not set; no separate evaluation command configured." >&2
  exit 0
fi

"$ROOT/scripts/docker_exec.sh" bash -lc "set -Eeuo pipefail; cd /workspace/source; $CRA_EVAL_CMD"
