# Docker Execution Model

CRA keeps the Humanize-driven agent loop, but task execution must happen inside Docker. The agent may be controlled from the host or from inside a dev container; either way, setup, runtime checks, official entry commands, validation, and evaluation must be executed through archived Docker wrappers.

## Execution Boundary

Use three roles:

- Controller: the human, Claude Code session, and Humanize loop that inspect plans, ask questions, and decide next actions.
- Task workspace: the mounted working directory containing the cloned target repository, references, scripts, logs, outputs, and archive.
- Execution container: the Docker environment that runs repository commands and produces evidence.

The target repository should not rely on undeclared host state. If a command matters for M1-M4, run it inside the execution container and archive the exact wrapper command plus log.

## Required Workspace Files

Each task workspace should create or archive these files before the main run:

```text
task-workspace/
  source/
  references/
  docs/
    run-contract.md
    draft.md
    plan.md
    environment-engineering.md
    human-questions.md
  scripts/
    docker_build.sh
    docker_run.sh
    docker_exec.sh
    runtime_check.sh
    launcher.sh
    evaluate.sh
  docker/
    Dockerfile.repro
    docker-compose.yml        # optional
  runs/
    YYYYMMDD-HHMMSS/
      docker_build.log
      docker_run.log
      runtime_check.log
      launcher.log
      eval.log
      env_summary.txt
      command_log.tsv
      checklist.md
      artifacts/
  outputs/
  patches/
```

Names can change when the target repository has a better convention, but the archive must preserve the same evidence.

## Dockerfile Rule

Prefer the target repository's official Dockerfile, container image, devcontainer, or environment file when one exists. If none exists, create `docker/Dockerfile.repro` as the smallest faithful runtime that can run the repository's documented commands.

A reproduction Dockerfile should record:

- Base image and OS.
- Python, CUDA, compiler, system package, and package-manager choices.
- Dependency installation command.
- Non-root user choice when feasible.
- Working directory, usually `/workspace/source`.

Do not hide dependency fixes in an interactive shell. Put durable environment fixes into `Dockerfile.repro`, a requirements lock, or an archived setup script.

## Wrapper Rule

All important commands should be wrapped and logged. Recommended pattern:

```bash
# scripts/docker_exec.sh
# Usage: scripts/docker_exec.sh <command...>
docker exec <container_name> "$@"
```

```bash
# scripts/runtime_check.sh
set -eu
python --version
python -m pip --version
python - <<'PYCODE'
import sys
print(sys.executable)
PYCODE
```

```bash
# scripts/launcher.sh
set -eu
cd /workspace/source
# Replace with the official repository entry command.
python main.py
```

The exact scripts should be generated inside the task workspace and copied into the run archive. Logs must include exit codes.

## Mounts And Secrets

Recommended mounts:

- Workspace: read-write at `/workspace`.
- References: read-only when feasible.
- Large datasets/checkpoints: read-only when the task does not require mutation.
- Cache directories: named Docker volumes or explicit cache mounts.

Secrets must be passed by environment allowlist or Docker secret mechanism, never written into archived logs. If an API key, token, cookie, or private header appears in output, redact it before archiving and record the redaction.

## GPU And Hardware

If GPU execution is required, record:

- Requested GPU devices.
- Container GPU flags, such as `--gpus`.
- CUDA, driver-visible runtime, framework, and device check output.
- Whether the official command used GPU, CPU fallback, or failed due to device access.

GPU availability alone is not success evidence. M4 still requires output and metric evidence, or precise blocker evidence.

## Failure Handling

When Docker setup fails, archive:

- Docker build command and log.
- Docker run command and log.
- Image name or digest if available.
- Failing command, exit code, stderr tail, and likely owner.

Classify Docker/image/runtime failures using the CRA checklist: usually `ENV`, `DEP`, `CFG`, `PATH`, or `INFRA`.

## Troubleshooting

For proxy, mirror, offline image transfer, Docker permission, GPU runtime, and secret-leakage issues, see `assets/TROUBLESHOOTING.md`.
