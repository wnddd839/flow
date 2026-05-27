# AgentFlow Skill Index

This is the single source of truth for workflow skills in this project.
Platform-specific skill files should stay thin and point back here.

## Always Start Here

1. Read `.agentflow/constitution.md`.
2. Read `.agentflow/state.yaml`.
3. Restate the task, scope, non-goals, and acceptance criteria.
4. Select the skill that matches the current phase and request.
5. Keep implementation scoped to the active change.
6. End with verification evidence or explicit unresolved risk.

## Available Skills

- `brainstorm`: clarify goals, scope, non-goals, and success criteria.
- `spec`: create proposal/design artifacts before risky or ambiguous work.
- `plan`: turn an approved design into small executable tasks.
- `implement`: execute one scoped task at a time.
- `verify`: run tests, inspect output, and collect acceptance evidence.
- `finish`: summarize changes, risks, evidence, and next action.

## Routing Rules

- New project or unclear goal: use `brainstorm`, then `spec`.
- Security, architecture, data model, or cross-module work: use `spec`.
- Small localized bugfix: use `implement`, then `verify`.
- Compiler, typecheck, lint, CI, or GitHub Actions failure: reproduce
  locally if possible, then use `verify` before broad edits.
- UI change: use `implement`, then run the closest UI or browser smoke.
- CLI change: use `implement`, then run a command-level smoke test.
- Testing, hardening, or regression work: use `verify`.
- End of a session: use `finish`.

## Verification Rules

- Prefer focused checks first, then broader checks when shared behavior changed.
- If a check fails, fix the root cause or report the exact blocker.
- Do not mark work complete from visual inspection alone when tests exist.

## Quality Cleanup Rules

- Do a deslop pass before `finish`: remove unused code, debug output,
  stale comments, accidental duplication, and needless abstractions.
- Preserve existing style and module boundaries.
- Do not leave TODOs unless the user explicitly accepted them.
