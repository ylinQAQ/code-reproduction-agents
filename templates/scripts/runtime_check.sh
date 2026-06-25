#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT/scripts/docker_exec.sh" bash -lc '
set -Eeuo pipefail
pwd
python --version
python -m pip --version
python - <<"PYCODE"
import importlib
import os
import platform
import sys
print("executable=", sys.executable)
print("platform=", platform.platform())
required = [x.strip() for x in os.environ.get("CRA_REQUIRED_IMPORTS", "").split(",") if x.strip()]
for name in required:
    importlib.import_module(name)
    print(f"import_ok={name}")
PYCODE
'
