# AgentFlow MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small local CLI that initializes and guides an AI coding workflow for any project.

**Architecture:** The tool is a lightweight Python package with no required network calls. It writes a `.agentflow/` workflow folder, creates thin agent entrypoints, scans repository signals, recommends a route for a user request, and generates handoff prompts for different coding agents.

**Tech Stack:** Python 3.11+ standard library, `argparse`, `pathlib`, `json`, `unittest`/`pytest` compatible tests.

---

## File Structure

- Create `agentflow_mvp/agentflow/__init__.py`: package marker and version.
- Create `agentflow_mvp/agentflow/templates.py`: all file templates for `.agentflow/`, `AGENTS.md`, and thin skill entrypoints.
- Create `agentflow_mvp/agentflow/core.py`: pure functions for init, scan, route recommendation, prompt rendering, and doctor checks.
- Create `agentflow_mvp/agentflow/cli.py`: command-line interface for `init`, `scan`, `ask`, `handoff`, `status`, and `doctor`.
- Create `agentflow_mvp/pyproject.toml`: install metadata and console script.
- Create `agentflow_mvp/README.md`: usage and workflow description.
- Create `agentflow_mvp/tests/test_core.py`: tests for the pure functions.
- Create `agentflow_mvp/tests/test_cli.py`: tests for CLI behavior.

## Tasks

### Task 1: Tests for Workflow Initialization

**Files:**
- Create: `agentflow-mvp/tests/test_core.py`
- Create: `agentflow-mvp/tests/test_cli.py`

- [ ] Write tests that initialize a temporary project and assert `.agentflow/constitution.md`, `.agentflow/state.yaml`, `.agentflow/skills/SKILL.md`, `AGENTS.md`, and platform entrypoint files exist.
- [ ] Run `python -m pytest agentflow-mvp/tests -q` and confirm the tests fail because implementation files do not exist yet.

### Task 2: Implement Initialization

**Files:**
- Create: `agentflow-mvp/agentflow/__init__.py`
- Create: `agentflow-mvp/agentflow/templates.py`
- Create: `agentflow-mvp/agentflow/core.py`
- Create: `agentflow-mvp/agentflow/cli.py`
- Create: `agentflow-mvp/pyproject.toml`

- [ ] Implement `init_project()` to create the workflow skeleton idempotently.
- [ ] Implement the `init` CLI command.
- [ ] Run initialization tests and confirm they pass.

### Task 3: Tests for Scan, Ask, Handoff, Doctor

**Files:**
- Modify: `agentflow-mvp/tests/test_core.py`
- Modify: `agentflow-mvp/tests/test_cli.py`

- [ ] Add tests for detecting Python/Node project signals.
- [ ] Add tests for classifying small bugfix, safety/security change, new feature, and project-start requests.
- [ ] Add tests for platform-specific handoff prompts.
- [ ] Add tests for doctor missing-file reporting.
- [ ] Run tests and confirm the new tests fail before implementation.

### Task 4: Implement Guide Commands

**Files:**
- Modify: `agentflow-mvp/agentflow/core.py`
- Modify: `agentflow-mvp/agentflow/cli.py`
- Create: `agentflow-mvp/README.md`

- [ ] Implement `scan_project()`.
- [ ] Implement `recommend_route()`.
- [ ] Implement `render_handoff_prompt()`.
- [ ] Implement `doctor_project()`.
- [ ] Implement `scan`, `ask`, `handoff`, `status`, and `doctor` CLI commands.
- [ ] Document the workflow and examples.

### Task 5: Verification

**Files:**
- No new files.

- [ ] Run `python -m pytest agentflow-mvp/tests -q`.
- [ ] Run `python -m agentflow.cli --help`.
- [ ] Run a smoke test in a temporary sample project: `init`, `ask`, `handoff codex`, and `doctor`.
- [ ] Report exact commands and outcomes.
