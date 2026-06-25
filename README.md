# Code Reproduction Agents

Code Reproduction Agents (CRA) is an agent-centric workflow for using coding agents to reproduce, adapt, verify, and archive results from existing code repositories.

This repository is a small workflow reference. It does not contain task-specific repositories, datasets, private credentials, reproduced outputs, or generated experiment artifacts. Use it as prompt and process material, then do the actual reproduction work in a separate implementation workspace.

## Contents

| Path | Purpose |
|---|---|
| `docs/agent-flow.md` | Minimal end-to-end CRA workflow. |
| `docs/controller.md` | Lightweight controller commands for scaffold, Docker execution, archive, and gate checks. |
| `docs/docker-execution.md` | Docker execution boundary and wrapper guidance. |
| `docs/environment-engineering.md` | Permissions, artifacts, budgets, and human-in-the-loop requirements. |
| `docs/reproduction-checklist.md` | Fillable evaluation and archive checklist for a reproduction run. |
| `prompts/README.md` | How to use prompt templates. |
| `prompts/basic-flow.md` | Generic starter prompt for a new reproduction task. |
| `CLAUDE.md` | Repository-facing agent instructions. |
| `assets/TROUBLESHOOTING.md` | Docker troubleshooting for proxy, mirrors, offline images, permissions, and GPU runtime issues. |
| `skills/` | Optional local skills. This directory may be empty. |
| `templates/` | Docker, script, and document templates copied by `cra init`. |
| `src/cra_controller/` | Lightweight controller implementation. |

## Task Scope

A CRA task starts from:

- A target GitHub repository.
- An implementation requirement, such as reproducing the original repository, changing the dataset, changing the method, or changing the downstream task while reusing the current codebase.
- Optional reference material, such as a paper, technical report, slides, poster, blog post, issue thread, model card, dataset card, or benchmark page.

The agent must turn those inputs into a fixed run contract, an executable plan, a validated implementation or clearly evidenced blocker, and an archive that another evaluator can inspect.

## Minimal Flow

1. Create a separate implementation workspace for the target repository.
2. Define the run contract: repository URL and commit, reproduction objective, dataset or task, official entry command, expected output, and success criterion.
3. Start an agent session in the implementation workspace.
4. Give the agent `prompts/basic-flow.md`, filled in with the task-specific details and reference paths.
5. Ask the agent to read the repository and references before writing `docs/draft.md`.
6. Convert the draft into an executable Humanize plan in `docs/plan.md`.
7. Create or select the Docker execution environment and archive the Docker wrappers.
8. Run runtime checks, official entry commands, validation, and evaluation inside Docker.
9. Produce intermediate artifacts, final outputs or precise blocking evidence, and a completed archive.
10. Evaluate the run with `docs/reproduction-checklist.md`.

## Controller Quick Start

CRA now includes a lightweight controller. It keeps the Humanize loop, but makes Docker scaffolding, execution logs, archiving, and gate checks repeatable.

From this repository:

```bash
PYTHONPATH=src python -m cra_controller init /path/to/task-workspace \
  --repo https://github.com/org/repo \
  --revision <commit-or-tag> \
  --requirement "reproduce the original repository" \
  --success-criterion "official metric is produced"
```

Then clone or copy the target repository into `/path/to/task-workspace/source`, start Claude/Humanize in the task workspace, and fill `docs/draft.md` and `docs/plan.md`.

To execute the archived Docker wrappers after setting task-specific commands:

```bash
export CRA_OFFICIAL_CMD="python main.py"
export CRA_EVAL_CMD="python evaluate.py"
PYTHONPATH=/workspace/yelin/code-reproduction-agents/src python -m cra_controller run /path/to/task-workspace
```

Use `cra check`, `cra archive`, `cra validate-gates`, and `cra report` to inspect completeness. Resume an interrupted run with `cra run /path/to/task-workspace --resume <run-id>`. See `docs/controller.md` for details.

## Recommended Workspace Layout

Use this repository as reference material, then do implementation work elsewhere:

```text
task-workspace/
  source/                     # cloned target repository or checked-out source tree
  references/                 # optional papers, slides, posters, blogs, notes
  docs/
    draft.md
    plan.md
    run-contract.md
    final-evaluation.md
  docker/
    Dockerfile.repro
  scripts/
    docker_build.sh
    docker_run.sh
    docker_exec.sh
    launcher.sh
    runtime_check.sh
    evaluate.sh
  runs/
    YYYYMMDD-HHMMSS/
      docker_build.log
      docker_run.log
      launcher.log
      runtime_check.log
      main_run.log
      eval.log
      env_summary.txt
      command_log.tsv
      checklist.md
      artifacts/
  outputs/
  patches/
  reproduction-notes.md
```

The exact files can change by domain. The important rule is that the workspace records enough context for another engineer or evaluator to understand what repository was used, what was changed, what ran, what failed or passed, and where the evidence is stored.

## Environment Engineering Requirements

CRA keeps the Humanize loop: the agent writes `docs/draft.md`, turns it into `docs/plan.md`, and iterates with validation. The execution boundary is stricter than the original lightweight flow: all task setup, official run, validation, and evaluation commands must run inside Docker or through archived Docker wrapper scripts.

Each task must address four environment engineering dimensions:

- Permissions engineering: define Docker mounts, secret handling, host/container boundary, and protected artifacts.
- Artifact engineering: produce direct M0-M5 evidence, wrapper snapshots, logs, patches, outputs, and checklist.
- Budget engineering: set setup, execution, evaluation, retry, storage, token/cost, and hardware budgets.
- Human-in-the-loop engineering: record only material user questions, answers, and approved scope or budget changes.

See `docs/docker-execution.md` and `docs/environment-engineering.md` for the reusable policy.

## Checklist Alignment

Each reproduction attempt should copy `docs/reproduction-checklist.md` into the run archive and preserve evidence for these gates:

- M0: fixed run contract.
- M1: usable runtime.
- M2: official entry launched.
- M3: intermediate artifact exists.
- M4: output and outcome evidenced, or exact blocking command and error captured.
- M5: archive complete.

Success requires more than a clean narrative. It requires commands, logs, paths, artifacts, metrics, and a final judgment that can be checked directly.
