# Prompt Templates

This directory stores generic prompts for the Code Reproduction Agents workflow.

The templates are intentionally task-agnostic. Fill in the target GitHub repository, implementation requirement, optional references, Docker execution mode, environment engineering constraints, validation command, evaluation command, and success criterion before starting an agent session in a separate implementation workspace.

## Available Templates

| Path | Purpose |
|---|---|
| `basic-flow.md` | Minimal prompt for repository inspection, reference reading, planning, implementation, validation, and archive creation. |
| `../docs/reproduction-checklist.md` | Fillable checklist template copied into each run archive. |

## How To Use

1. Create or enter the task implementation workspace.
2. Clone or otherwise place the target repository under the workspace.
3. Copy the relevant template content into the agent session.
4. Replace placeholders with task-specific details.
5. Ask the agent to read the workspace and references before writing `docs/draft.md`.
6. Convert that draft into an executable plan in `docs/plan.md`.
7. Run the Humanize implementation loop, but execute setup/run/eval commands inside Docker through archived wrappers.
8. Complete the reproduction checklist and archive direct evidence.

Task-specific prompts should live with the task they describe. Do not add benchmark-specific datasets, paper-specific claims, private evaluator details, credentials, or generated outputs to this generic repository.
