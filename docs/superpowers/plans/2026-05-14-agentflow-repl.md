# AgentFlow Interactive Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users run `agentflow` with no arguments and use a simple interactive shell instead of remembering subcommands.

**Architecture:** Keep existing CLI commands intact. Add `agentflow/repl.py` as a thin interactive layer that calls existing `core.py` functions. Update `cli.py` so no arguments enter the shell while explicit subcommands keep their current behavior.

**Tech Stack:** Python standard library only: `sys`, `shlex`, `pathlib`, `typing`.

---

## File Structure

- Create `agentflow/repl.py`: banner, help text, slash command parser, menu command aliases, and input loop.
- Modify `agentflow/cli.py`: route empty argv to `run_repl()`.
- Modify `tests/test_cli.py`: process-level tests for no-arg REPL, `/ask`, `/handoff`, `/quit`.
- Modify `README.md`: explain `agentflow` interactive mode.

## Tasks

### Task 1: RED Tests

- [ ] Add a test that starts `python -m agentflow.cli` with stdin `/quit` and expects a banner and exit code 0.
- [ ] Add a test that sends `/ask fix pagination bug` then `/quit` and expects `Recommended workflow: simple-change`.
- [ ] Add a test that sends `/handoff codex fix pagination bug` then `/quit` and expects `# Handoff for Codex`.
- [ ] Run unittest and confirm failure because no-arg CLI currently exits with argparse error.

### Task 2: GREEN Implementation

- [ ] Implement `run_repl()` in `agentflow/repl.py`.
- [ ] Support `/help`, `/init`, `/scan`, `/ask`, `/handoff`, `/status`, `/doctor`, `/menu`, `/quit`, and numeric aliases.
- [ ] Modify `cli.py` so empty argv enters `run_repl()`.
- [ ] Run unittest and confirm all tests pass.

### Task 3: Docs and Smoke

- [ ] Update README with `agentflow` interactive examples.
- [ ] Run full unittest.
- [ ] Run a smoke command with `/help` and `/quit` piped through stdin.
