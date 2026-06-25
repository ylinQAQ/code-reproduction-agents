# Agent Flow

Code Reproduction Agents is a repeatable loop for agent-driven reproduction work. The loop is useful when a task starts from an existing repository and must end with either a verified reproduction, a scoped adaptation, or a precise externally checkable blocker.

## Principle

Keep the reusable workflow separate from the task workspace. This repository explains the flow. The task workspace owns the cloned repository, reference material, datasets, runtime environment, scripts, patches, logs, outputs, and evaluation records.

A reproduction task may ask for the original repository behavior, a new dataset, a new method variant, a new downstream task, or a port of the repository to a different runtime. The same flow applies: fix the contract, inspect the source, plan, run the official entry inside Docker, modify only what the contract requires, validate inside Docker, and archive evidence.

## Minimal Loop

1. Define the run contract.
2. Let the agent inspect the target repository and reference material.
3. Make the agent write `docs/draft.md`.
4. Convert the draft into an executable plan in `docs/plan.md`.
5. Prepare and verify the Docker runtime.
6. Execute the repository's official entry point or tests inside Docker.
7. Implement the requested reproduction or adaptation candidate.
8. Validate correctness and evaluate the target metric inside Docker when applicable.
9. Record intermediate artifacts, final outputs, metrics, blockers, and errors.
10. Repeat until the success criterion is met or the remaining blocker is explicit.
11. Archive all evidence needed for checklist review.

## Run Contract

Each task should state:

- Target GitHub repository URL.
- Resolved commit, branch, tag, or release.
- Implementation requirement: original reproduction, dataset change, method change, task change, environment port, or another explicit scope.
- Optional references: paper, report, slides, poster, blog, issue, model card, dataset card, benchmark page, or local notes.
- Inputs and expected outputs.
- Dataset, model, checkpoint, or external service requirements.
- Correctness requirements and tolerated deviations.
- Metric or success criterion.
- Constraints on language, dependencies, hardware, API usage, licenses, time, or storage.
- Docker execution mode, image, mounts, and wrapper commands.
- Setup, validation, and evaluation budgets.
- Official setup, validation, and evaluation commands.
- Archive directory and naming convention.

## Evidence Records

Use simple files in the task workspace:

- `docs/run-contract.md` for M0.
- `docs/reproduction-checklist.md` as the checklist template to copy into each run archive.
- `docs/environment-engineering.md` for task-specific permissions, artifacts, budgets, and human input policy.
- `docs/draft.md` for the first plan draft.
- `docs/plan.md` for the executable plan.
- Docker wrappers and `runs/*/docker_build.log` / `runs/*/docker_run.log` for the execution boundary.
- `scripts/runtime_check.sh` and `runs/*/runtime_check.log` for M1.
- `scripts/launcher.sh` and `runs/*/launcher.log` for M2.
- `runs/*/artifacts/` for M3 intermediate artifacts.
- `outputs/`, `runs/*/eval.log`, or metric files for M4.
- `runs/*/checklist.md`, trajectory files, patches, logs, and final notes for M5.

The exact format is less important than consistency. A future reader should be able to reconstruct what changed, what command ran, what evidence was produced, and why the final judgment was `success`, `partial_success`, `blocked_external`, `blocked`, or `failed`.

## Docker Execution Rule

All setup, official run, validation, and evaluation commands must execute inside Docker. The Claude/Humanize control session may run on the host, but important task commands should go through archived wrapper scripts such as `scripts/docker_exec.sh`, `scripts/runtime_check.sh`, `scripts/launcher.sh`, and `scripts/evaluate.sh`. If Docker cannot be used, record that as a blocker or explicitly approved scope change.

## Official Entry Rule

Run the repository's documented entry path before relying on a custom workaround. Valid official entries include:

- README commands.
- `train.py`, `main.py`, `run.py`, `evaluate.py`, or equivalent scripts.
- Shell scripts shipped by the repository.
- Notebook execution wrapped in a reproducible command.
- Unit, integration, or smoke tests shipped by the repository.

If the official entry is impossible to run, record the exact command, exit code, stderr or traceback, and the source location or documentation line that led to that command.

## Adaptation Rule

When the task asks for a dataset, method, or task change, preserve the repository's existing structure unless there is a concrete reason to change it. Prefer:

- Adding a small config, adapter, or wrapper.
- Extending existing dataset loaders or model registries.
- Reusing existing training, inference, and evaluation scripts.
- Keeping metric names and output formats compatible with the original evaluation path.

Avoid unrelated refactors. Every code change should connect directly to the run contract or to a blocker discovered while satisfying it.

## Promotion Rule

Promote a candidate only when it satisfies the run contract and has evidence. If a candidate is rejected, record the reason instead of silently discarding it. If the run cannot complete, the final artifact must still identify the blocking command, exact error evidence, likely owner, and the next concrete action.


## Environment Engineering Rule

Each task plan must address four dimensions before long execution starts:

- Permissions engineering: Docker mounts, secrets, protected files, and allowed write locations.
- Artifact engineering: exact evidence paths for M0-M5, logs, outputs, patches, and checklist.
- Budget engineering: setup, execution, evaluation, retries, storage, token/cost, and hardware.
- Human-in-the-loop engineering: blocker questions, answers, and approved scope or budget changes.

Use `docs/environment-engineering.md` for the detailed policy.
