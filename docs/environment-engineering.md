# Environment Engineering

CRA uses the Humanize loop for planning and iteration, but the task workspace must be engineered so a reproduction run is inspectable, bounded, and recoverable. These requirements are adapted for code reproduction from environment-engineered agent systems such as EurekAgent, without adopting their `prepare -> propose -> implement` controller loop.

## 1. Permissions Engineering

Goal: make the allowed action surface explicit and prevent accidental host-dependent or evidence-destroying behavior.

Required practices:

- Run setup, official entry, validation, and evaluation commands inside Docker.
- Record whether Claude Code itself is host-side or container-side.
- Keep the target repository under `source/`; keep references under `references/`; keep generated outputs under `outputs/` or `runs/`.
- Use wrapper scripts for Docker build, Docker run, runtime check, official run, and evaluation.
- Treat archived result files, metric logs, and checklist files as append-only after finalization.
- Do not modify hidden/private evaluator files when a task provides them.
- Do not write secrets into repository files or archives.
- Avoid global host installs. Dependency changes belong in the container, repository lock files, or archived setup scripts.

Recommended controls:

- Mount references and large immutable datasets read-only.
- Use a non-root container user when compatible with the target repository.
- Use explicit environment-variable allowlists for provider credentials.
- Archive a non-sensitive env summary instead of full `env` output.

## 2. Artifact Engineering

Goal: make every milestone verifiable from files, not from memory or narrative.

Required artifacts:

- `docs/run-contract.md`: repository URL, revision, requirement, dataset/task, official command, success criterion, Docker execution mode.
- `docs/draft.md`: initial plan draft before edits.
- `docs/plan.md`: executable Humanize plan.
- `docs/environment-engineering.md`: task-specific permissions, artifacts, budgets, and human input policy.
- Docker files and wrapper script snapshots.
- Runtime check log from inside Docker.
- Official entry log from inside Docker.
- Intermediate artifact path for M3.
- Main output or blocker evidence for M4.
- Patch or diff for modified repository files.
- Completed checklist copied from `docs/reproduction-checklist.md`.

Use stable paths. If a run creates many files, add an `artifact_index.md` or `artifact_index.json` in the run archive.

## 3. Budget Engineering

Goal: prevent indefinite exploration and make partial results meaningful.

Each run contract should define:

- Setup budget.
- Main execution budget.
- Evaluation budget.
- Retry budget.
- Token or cost budget if applicable.
- Storage budget for datasets, checkpoints, logs, and outputs.
- GPU or CPU budget if relevant.

Each wrapper should enforce or record budgets. Use `timeout` or an equivalent mechanism for long-running commands when feasible. If a command exceeds budget, archive the timeout command, elapsed time, partial logs, and any partial artifacts.

Humanize loop iterations should end with one of these decisions:

- Continue: evidence improved or a concrete next step remains within budget.
- Revise: the current plan failed but a bounded repair is available.
- Archive blocker: the next step depends on external access, missing data, unavailable hardware, or a user decision.
- Stop: M2, M4, or M5 cannot be satisfied within budget.

## 4. Human-In-The-Loop Engineering

Goal: ask humans only for decisions that materially affect correctness, access, or budget.

Ask the user when:

- Required dataset, checkpoint, credential, or license access is missing.
- The success criterion is ambiguous or conflicts with the repository/reference material.
- Multiple official entry commands conflict and choosing one changes the result.
- A risky repair would change the task scope.
- The run needs more time, storage, GPU, money, or external service access than the contract allows.

Do not ask for routine implementation choices that can be inferred from the repository. Record each human question and answer in `docs/human-questions.md` and copy it into the archive.

A useful question record format:

```markdown
## Q1

- Time:
- Blocking issue:
- Question:
- Options considered:
- User answer:
- Resulting action:
```

If no human input was needed, write `N/A` in the artifact checklist.

## Task-Specific Environment Engineering Note

Each task workspace should create `docs/environment-engineering.md` with this structure:

```markdown
# Environment Engineering Note

## Permissions
- Docker execution mode:
- Workspace mount policy:
- Secret handling:
- Protected artifacts:

## Artifacts
- Archive directory:
- Required M0-M5 evidence paths:
- Patch/diff path:

## Budgets
- Setup budget:
- Execution budget:
- Evaluation budget:
- Retry budget:
- Token/cost/storage/GPU budget:

## Human Input
- Questions asked:
- Open decisions:
- Scope changes approved:
```
