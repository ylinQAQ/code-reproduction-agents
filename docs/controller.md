# CRA Controller

The CRA controller is a lightweight helper for Docker-backed code reproduction runs. It does not replace the Humanize loop and does not impose a fixed `prepare -> propose -> implement` state machine.

## Commands

```bash
cra init <task-workspace> --repo <url> --revision <commit> --requirement "reproduce the repository"
cra check <task-workspace>
cra run <task-workspace>
cra run <task-workspace> --resume <run-id>
cra archive <task-workspace> --run-dir <task-workspace>/runs/<run-id>
cra validate-gates <task-workspace>/runs/<run-id>
cra report <task-workspace>/runs/<run-id>
```

During development, without installing the package, use:

```bash
PYTHONPATH=/path/to/code-reproduction-agents/src python -m cra_controller --help
```

## Responsibilities

- `init`: create a task workspace with Docker wrappers, docs, and checklist template.
- `check`: verify required scaffold files exist and scripts are executable.
- `run`: execute Docker wrappers in sequence, capture logs, write `run_metadata.json`, and update the archive.
- `run --resume <run-id>`: reuse an existing run directory and skip wrapper commands that already exited `0`, unless `--rerun-successful` is set.
- `archive`: snapshot docs, Docker files, scripts, outputs, checklist, metadata, and git diff.
- `validate-gates`: code-validate M0-M5 evidence using `src/cra_controller/artifacts.py`.
- `report`: generate `report.md` and `report.html` from metadata, command logs, and gate validation.

## Non-Goals

- It does not create multiple agent sessions.
- It does not hide a grader from the agent.
- It does not rank approaches.
- It does not replace Humanize planning or implementation loops.


## Run Metadata

`cra run` writes `run_metadata.json` into the run directory. It records the workspace, run ID, contract summary, controller arguments, command results, resume events, gate validation, and final archive status.

## Resume Semantics

Resume is run-level, not Claude-session-level. On `cra run --resume <run-id>`, the controller reads the existing `command_log.tsv` and skips commands with exit code `0`. Failed, missing, or unrecorded commands are rerun in order. Use `--rerun-successful` to rerun every wrapper.

## Reports

`cra report <run-dir>` writes:

- `report.md`
- `report.html`

The report summarizes contract fields, command exits, M0-M5 gate statuses, and missing evidence.
