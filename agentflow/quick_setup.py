"""One-shot interactive setup: pick agents, then initialize in a single step.

This wraps the existing editor selection and project init into a single flow
so the user does not need to call ``/editors`` (toggle one by one) followed by
``/init`` (separate step). It uses ``prompt_toolkit``'s ``checkboxlist_dialog``
for arrow-key + space-bar multiselect, which is already a project dependency.

Public entry points:

- :func:`pick_editors_interactive` -- show the multiselect dialog and return the
  chosen editor names (or ``None`` when cancelled).
- :func:`run_quick_setup` -- orchestrate the full "select -> persist -> init ->
  sync" flow and return a small result dict for the caller to render.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from .core import init_project
from .editors import (
    all_editors,
    get_enabled_editors,
    load_editor_config,
    save_editor_config,
)


# A picker returns either a list of editor names or ``None`` (cancelled).
Picker = Callable[[list[str]], "list[str] | None"]


def run_quick_setup(
    project_dir: str | Path,
    project_name: str | None = None,
    force: bool = False,
    home: str | Path | None = None,
    picker: Picker | None = None,
) -> dict[str, object]:
    """Run the one-shot interactive setup flow.

    Steps:
    1. Determine the default-checked editors from the current user config.
    2. Ask the user (via ``picker``) to confirm or change the selection.
    3. On cancel, return ``{"cancelled": True}`` without writing anything.
    4. On confirm, persist the selection, run :func:`init_project`, and
       refresh the project's skill index.

    ``picker`` lets tests inject a fake dialog; when it is ``None`` and there
    is no real TTY, the flow returns cancelled instead of crashing.
    """

    root = Path(project_dir)
    defaults = [spec.name for spec in get_enabled_editors(home=home)]

    if picker is None:
        picker = pick_editors_interactive

    chosen = picker(defaults)
    if chosen is None:
        return {"cancelled": True}

    # Normalize + validate against the catalog so unknown names are dropped.
    catalog = all_editors(home=home)
    valid_names: list[str] = []
    seen: set[str] = set()
    for name in chosen:
        key = str(name).strip().lower()
        if key in catalog and key not in seen:
            valid_names.append(key)
            seen.add(key)

    if not valid_names:
        return {"cancelled": True, "empty": True}

    config = load_editor_config(home=home)
    save_editor_config(valid_names, config.get("custom", {}), home=home)

    init_result = init_project(
        root,
        project_name=project_name,
        editors=valid_names,
        force=force,
        home=home,
    )
    return {
        "cancelled": False,
        "editors": valid_names,
        "init": init_result,
    }


def pick_editors_interactive(
    defaults: Iterable[str] | None = None,
) -> "list[str] | None":
    """Show a full-screen multiselect dialog for choosing agents.

    Returns the list of selected editor names, or ``None`` when the user
    cancels (Cancel button or Esc). When no real TTY is available, the
    function returns ``None`` rather than attempting to render the dialog.
    """

    import sys

    # checkboxlist_dialog needs a real terminal; in tests / pipes we bail out.
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return None

    try:
        from prompt_toolkit.shortcuts import checkboxlist_dialog
        from prompt_toolkit.styles import Style
    except ImportError:  # pragma: no cover - dependency fallback
        return None

    default_set = {str(name).strip().lower() for name in (defaults or [])}
    catalog = all_editors()

    # Stable, readable order: built-ins first (in the catalog's natural order),
    # then custom ones alphabetically.
    ordered_names = sorted(
        catalog.keys(),
        key=lambda name: (not _is_builtin(name), name),
    )
    values = [
        (name, f"{catalog[name].display}  ({catalog[name].entrypoint})")
        for name in ordered_names
    ]

    style = Style.from_dict({
        "dialog": "bg:#0f172a",
        "dialog frame label": "fg:#06b6d4 bold",
        "dialog.body": "bg:#0f172a fg:#e2e8f0",
        "checkbox": "fg:#06b6d4",
        "checkbox-checked": "fg:#10b981 bold",
        "button": "bg:#1e293b fg:#cbd5e1",
        "button.focused": "bg:#4f46e5 fg:#ffffff bold",
        "button.arrow": "fg:#06b6d4",
    })

    result = checkboxlist_dialog(
        title="AgentFlow Setup",
        text=(
            "Select agents to set up. Checked agents become your global default; "
            "unchecking one disables it everywhere. (Space toggles, Enter confirms)"
        ),
        values=values,
        default_values=[name for name in ordered_names if name in default_set],
        ok_text="Initialize",
        cancel_text="Cancel",
        style=style,
    ).run()

    if result is None:
        return None
    return [str(name) for name in result]


def _is_builtin(name: str) -> bool:
    """True when ``name`` is one of the six built-in agents."""

    from .editors import KNOWN_EDITORS

    return name in KNOWN_EDITORS
