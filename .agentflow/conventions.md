# 编码规范

<!-- ═══════════════════════════════════════════════════════════
     本文件边界（不可删除，不可改写）
     只写：这个项目【怎么写代码】：命名、结构、风格、禁用模式
     不写：项目是什么/怎么运行（→ project.md）、业务规则（→ business.md）、历史踩坑（→ pitfalls.md）
     判断标准：如果一段内容换到别的项目还能用，它就不属于这里。
     ═══════════════════════════════════════════════════════════ -->

<!-- 维护契约：由首个接触本项目的 AI 编码助手分析代码后填写；
     后续每次接手时核对，与代码不符就修正。不要删除章节标题。 -->

## 命名约定

- **包与模块**：`agentflow/` 下单文件单职责；文件名小写蛇形（`core.py`、`editors.py`）。
- **公开 API**：模块级函数用动词短语（`init_project`、`doctor_project`、`apply_editors`）；CLI 子命令处理函数以 `_cmd_` 前缀（`_cmd_init`）。
- **常量**：全大写蛇形（`BASE_REQUIRED_FILES`、`AGENTFLOW_GENERATED_MARKER`、`DEFAULT_PLATFORMS`）。
- **内部辅助**：单下划线前缀（`_write_text`、`_safe_project_path`、`_is_agentflow_entrypoint`）。
- **数据类**：`@dataclass(frozen=True)` 表示不可变值对象（`EditorSpec`、`DiagnosticItem`、`ToolInfo`）。
- **CLI 程序名**：对外品牌为 `flow`；包名保持 `agentflow`，两个入口脚本等价。

## 代码结构

| 放什么 | 放哪里 |
|--------|--------|
| 磁盘写入 / 检查逻辑 | `core.py` |
| 纯字符串模板（骨架、薄入口） | `templates.py` |
| 用户级编辑器配置、名称校验、入口 reconcile | `editors.py` |
| `flow init` 编辑器多选（交互 / 回退） | `init_ui.py` |
| 环境探测（PATH 工具、诊断项） | `diagnostics.py` |
| argparse 与命令分发 | `cli.py` |
| 交互 REPL | `repl.py` |
| 版本号 | `__init__.py` |

**新增 CLI 子命令**：在 `cli.py` 的 `_build_parser` 注册 → 实现 `_cmd_*` → 加入 `COMMANDS` 字典。

**新增内置编辑器**：在 `templates.py` 同步更新 `PLATFORM_DISPLAY`、`PLATFORM_ENTRYPOINTS`（`editors.py` 从中派生内置目录），并补充 `tests/test_init.py` 断言。

**editors 与 tools 是两个独立清单**：`editors`（薄入口写入目标，源自 `templates.PLATFORM_*`）与 `diagnostics.KNOWN_TOOLS`（PATH 上可探测的 AI CLI）回答不同问题，不必逐一对应，改其一不要顺手改另一个。

**避免循环导入**：`editors.apply_editors` 等对 `templates` 使用函数内局部 import。

**测试**：`tests/` 下按模块分文件；临时目录用 `tempfile.TemporaryDirectory`；CLI 集成测试通过 `subprocess` 调用 `python -m agentflow.cli`。

## 风格与格式

- 文件头使用中文模块 docstring，说明模块职责。
- 全项目 `from __future__ import annotations`。
- 类型标注覆盖公开函数参数与返回值；`Path` 统一来自 `pathlib`。
- 文件读写显式 `encoding="utf-8"`。
- 用户可见输出：CLI 用 `print`；REPL 用 `rich`（`Console`、`Panel`、`Table`）。
- 无项目级 ruff/black 配置；遵循现有 4 空格缩进与 `import` 分组习惯（标准库 → 第三方 → 本地）。
- 模板正文用 `textwrap.dedent`，保持生成 Markdown 可读。
- 文档与模板正文不使用 emoji；边界声明用「只写 / 不写」纯文本。

## 禁用模式

- **不引入新运行时依赖**：保持离线、轻量；新能力优先标准库，确有必要再改 `pyproject.toml` 并说明理由。
- **不在 `templates.py` 写盘**：模板模块只返回字符串；持久化集中在 `core` / `editors`。
- **不在骨架模板里预填目标项目内容**：`test_templates.py` 禁止骨架出现 `agentflow-mvp` 等项目专属描述；首个接手的 AI 填 `.agentflow/*.md`，不是改 `templates.py`。
- **不删除用户自有编辑器配置**：禁用编辑器时仅删除带 `AGENTFLOW_GENERATED_MARKER` 或可识别的薄入口，不删 `.cursor/` 等顶层目录及其他用户文件。
- **不接受越界路径**：自定义编辑器入口必须是项目内相对路径，禁止 `..` 与绝对路径（见 `editors._validate_relative_entrypoint`）。
- **不在业务逻辑层调用 AI API**：`diagnostics` 只做本地 PATH 检测，不做网络请求。
- **不做平台绑定式集成**：不添加某一 agent/编辑器的 hook、插件或会话编排；保持地基工具定位。
