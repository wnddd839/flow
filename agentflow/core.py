"""核心业务：初始化项目规范骨架与健康检查。"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from . import templates


# doctor 最小检查集：规范总入口 + 四个骨架文档 + skill 路由表
BASE_REQUIRED_FILES = [
    ".agentflow/AGENTS.md",
    ".agentflow/project.md",
    ".agentflow/conventions.md",
    ".agentflow/business.md",
    ".agentflow/pitfalls.md",
    ".agentflow/skills/README.md",
]

DEFAULT_EDITOR_NAMES = list(templates.DEFAULT_PLATFORMS)


def init_project(
    project_dir: str | Path,
    editors: Iterable[str] | None = None,
    force: bool = False,
    home: str | Path | None = None,
) -> dict[str, list[str]]:
    """在项目中生成规范文档骨架与各编辑器薄入口。

    - 默认启用全部 6 个内置编辑器并生成薄入口
    - ``editors=...`` 可缩减（非交互，供脚本使用）
    - 不弹窗、不问业务问题，只写空架子
    """

    from .editors import (
        apply_editors,
        save_editor_config,
        load_editor_config,
    )

    root = Path(project_dir)
    created: list[str] = []
    skipped: list[str] = []

    files: dict[str, str] = {
        ".agentflow/AGENTS.md": templates.agents_md(),
        ".agentflow/project.md": templates.project_skeleton(),
        ".agentflow/conventions.md": templates.conventions_skeleton(),
        ".agentflow/business.md": templates.business_skeleton(),
        ".agentflow/pitfalls.md": templates.pitfalls_skeleton(),
        ".agentflow/skills/README.md": templates.skills_readme(),
    }

    editor_names = (
        [name.strip().lower() for name in editors if str(name).strip()]
        if editors is not None
        else list(DEFAULT_EDITOR_NAMES)
    )
    config = load_editor_config(home=home)
    save_editor_config(editor_names, config.get("custom", {}), home=home)

    for relative, content in files.items():
        status = _write_text(root / relative, content, force=force)
        if status == "created":
            created.append(relative)
        else:
            skipped.append(relative)

    editor_result = apply_editors(root, home=home, force=force)
    created.extend(editor_result["created"])
    skipped.extend(editor_result["kept"])

    return {
        "created": created,
        "skipped": skipped,
        "editors_removed": editor_result["removed"],
    }


def doctor_project(
    project_dir: str | Path,
    home: str | Path | None = None,
) -> dict[str, object]:
    """检查规范骨架文件是否存在。"""

    from .editors import get_enabled_editors

    root = Path(project_dir)
    enabled = get_enabled_editors(home=home)
    required = list(BASE_REQUIRED_FILES) + [spec.entrypoint for spec in enabled]
    missing = [relative for relative in required if not (root / relative).exists()]
    return {
        "ok": not missing,
        "missing": missing,
        "checked": required,
        "editors": [spec.name for spec in enabled],
    }


REQUIRED_FILES = list(BASE_REQUIRED_FILES)


def _write_text(path: Path, content: str, force: bool) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return "skipped"
    path.write_text(content, encoding="utf-8")
    return "created"
