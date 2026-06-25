#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -z "${CRA_OFFICIAL_CMD:-}" ]]; then
  cat >&2 <<'EOF'
CRA_OFFICIAL_CMD is not set.
Set it to the repository official entry command, for example:
  export CRA_OFFICIAL_CMD="python main.py --config configs/example.yaml"
Then rerun scripts/launcher.sh or cra run.
EOF
  exit 2
fi

"$ROOT/scripts/docker_exec.sh" bash -lc "set -Eeuo pipefail; cd /workspace/source; $CRA_OFFICIAL_CMD"
