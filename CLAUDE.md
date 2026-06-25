# Agent Instructions

This repository is the generic Code Reproduction Agents workflow reference. It should stay small, English-only, and task-agnostic.

## Repository Rules

- Use English for repository-facing files, comments, documentation, prompts, and commit messages.
- Keep cloned target repositories, datasets, generated outputs, model weights, benchmark logs, credentials, and task-specific artifacts out of this repository.
- Put generated outputs in `runs/`, `outputs/`, `archives/`, `logs/`, or `patches/`; these paths are ignored by git.
- Treat papers, slides, posters, blogs, and benchmark pages as task inputs for the implementation workspace, not as permanent content for this generic workflow repository.
- Prefer documenting reusable reproduction mechanics over documenting one paper, one benchmark, or one private evaluator.
- Preserve the Humanize loop as the default workflow; do not replace it with a fixed controller state machine unless explicitly requested.
- Require Docker for task execution commands. Host-side Claude/Humanize control is acceptable, but setup, official entry, validation, and evaluation commands must run through archived Docker wrappers.

## Expected Agent Workflow

For a new reproduction task:

1. Create or enter a separate implementation workspace.
2. Record the target GitHub repository URL, resolved commit, task requirement, optional references, expected output, and success criterion.
3. Use `prompts/basic-flow.md` as the starter prompt.
4. Read local code, README files, setup files, examples, tests, scripts, issues or docs included with the target repository, and any provided reference material before proposing implementation changes.
5. Write the initial plan draft to `docs/draft.md` inside the task workspace.
6. Convert the draft into an executable plan in `docs/plan.md`.
7. Write a task-specific environment engineering note covering permissions, artifacts, budgets, and human input policy.
8. Prepare the Docker runtime and run import or version checks inside Docker before long execution.
9. Launch the repository's official entry point, wrapper script, or tests inside Docker before relying on custom code.
10. If the requirement changes the dataset, method, or task, make the smallest coherent change that preserves the repository's existing interfaces and evaluation path.
11. Validate each meaningful candidate inside Docker and record commands, logs, outputs, metrics, and blockers.
12. Complete the reproduction checklist and archive the trajectory, scripts, Docker evidence, logs, patch, outputs, and final note.

## Checklist Expectations

The implementation workspace should preserve evidence for:

- M0: run contract fixed.
- M1: runtime usable.
- M2: official entry launched.
- M3: intermediate artifact exists.
- M4: output and outcome evidenced, or precise blocking evidence.
- M5: archive complete.

Use the checklist's error classification when recording failures:

- Outcome code: `COMPLETE`, `IF`, `IA`, `TLE`, or `OTHER`.
- Phase: `SETUP`, `EXECUTION`, or `EVAL`.
- Impact: `I0`, `I1`, `I2`, or `I3`.
- Recovery status: `RECOVERED` or `NOT_RECOVERED`.
- Attribution: `AGENT`, `REPO`, `INFRA`, `PROVIDER`, `EXTERNAL`, `MIXED`, or `UNCONFIRMED`.
- Error type: `ENV`, `DEP`, `PATH`, `CFG`, `PROVIDER`, `TOOLING`, `LOGIC`, `CONTROL`, or `DATA`.

## Optional Skills

Use external skills only when they are relevant to the active task:

- A paper-reading or literature skill for dense reference material.
- A domain knowledge skill for the target method or benchmark.
- A profiling, debugging, or log-analysis skill for runtime evidence.
- A dataset or model-card skill for data access and licensing checks.


## Environment Engineering

Every reproduction task should explicitly cover four dimensions:

- Permissions: Docker boundary, mounts, credentials, protected files, and host/container responsibilities.
- Artifacts: run contract, plan, Docker wrappers, logs, intermediate files, outputs, patch, checklist, and final note.
- Budgets: setup, execution, evaluation, retry, token/cost, storage, and hardware limits.
- Human input: blocker questions, user answers, and approved scope or budget changes.

Use `docs/docker-execution.md` and `docs/environment-engineering.md` as the source of truth for these requirements.
