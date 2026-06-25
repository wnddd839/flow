# 项目说明

<!-- ═══════════════════════════════════════════════════════════
     本文件边界（不可删除，不可改写）
     只写：这个项目【是什么】：一句话定位、技术栈、整体架构、怎么启动运行
     不写：怎么写代码（→ conventions.md）、业务规则与术语（→ business.md）、踩过的坑（→ pitfalls.md）、专项操作流程（→ skills/）
     判断标准：如果一段内容换到别的项目还能用，它就不属于这里。
     ═══════════════════════════════════════════════════════════ -->

<!-- 维护契约：由首个接触本项目的 AI 编码助手分析代码后填写；
     后续每次接手时核对，与代码不符就修正。不要删除章节标题。 -->

## 一句话定位

轻巧的离线 Python CLI（`flow` / `agentflow`），为任意代码仓库铺设 AI 编码规范的地基：生成 `.agentflow/` 文档骨架，并按需写入各 AI 工具的薄入口指针。不编排工作流，不绑定特定 agent。

## 产品边界

| Flow 负责 | Flow 不负责 |
|-----------|-------------|
| 规范文档骨架与薄入口 | 文档正文（由 AI / 开发者填写） |
| 文件存在性检查（`check`） | 文档内容质量或是否填完 |
| 多平台入口路径管理（`editors`） | 绑定某一编辑器做 hook 或深度集成 |
| 本地 AI CLI 探测（`tools`） | 强制模型遵守维护契约 |

## 技术栈

| 项 | 版本 / 说明 |
|----|------------|
| 语言 | Python ≥ 3.11 |
| 运行时依赖 | `rich`（终端 UI）、`prompt_toolkit`（REPL 补全） |
| 开发依赖 | `pytest` |
| 打包 | `setuptools`，入口脚本 `flow` 与 `agentflow` 均指向 `agentflow.cli:main` |
| 当前版本 | `0.5.0`（见 `agentflow/__init__.py`） |
| 网络 | 无 API 调用、无网络依赖 |

## 架构概览

```
agentflow/
  cli.py          命令行入口（init / check / editors / tools / instructions / --version）
  core.py         init_project、doctor_project
  templates.py    规范文档与薄入口的字符串模板（只产字符串，不写盘）
  editors.py      编辑器配置（~/.agentflow/editors.yaml）、名称校验与薄入口 reconcile
  init_ui.py      flow init 的编辑器多选（交互对话框 / 文本回退 / 非 TTY 返回空）
  diagnostics.py  本地工具检测与诊断输出
  repl.py         无参数 `flow` 时的交互工作台
tests/            unittest / pytest 兼容测试
```

**数据流（`flow init`）：**

1. `init_ui.pick_editors`（仅 TTY）或命令行参数决定本次启用哪些平台；默认空（仅骨架）。
2. `templates.py` 生成 `.agentflow/` 下 6 个规范文件内容。
3. `editors.py` 读取/写入用户级 `editors.yaml`，保存启用列表。
4. `apply_editors` 为已启用平台写入薄入口（Codex 为根 `AGENTS.md` 指针，其余为单行指向 `.agentflow/AGENTS.md`），并安全移除已禁用平台的旧入口。
5. `doctor_project` 校验骨架文件 + 已启用编辑器的入口文件是否齐全。

用户级配置目录：`~/.agentflow/`（可通过环境变量 `AGENTFLOW_HOME` 覆盖）。

## 启动与运行

**安装（开发模式）：**

```bash
python -m pip install -e ".[dev]"
```

**初始化当前项目规范骨架：**

```bash
flow init                      # TTY 下交互勾选编辑器；非 TTY 仅骨架
flow init cursor               # 骨架 + Cursor 薄入口
flow init cursor claude        # 多个平台 positional
flow init --editors qoder,cursor
flow init --skeleton-only      # 仅 .agentflow/，不生成 CLAUDE.md 等
flow init --force              # 覆盖已有文件
```

**健康检查与诊断：**

```bash
flow check      # doctor 为别名；失败时 exit code 1
flow tools      # 检测本机 AI CLI 是否在 PATH
flow instructions
```

**交互工作台：**

```bash
flow            # 无参数进入 REPL：/init /check /tools /instructions /help
```

**测试：**

```bash
python -m compileall -f agentflow tests
python -m pytest -q
```

CI（`.github/workflows/ci.yml`）在 Python 3.11 / 3.12 上执行相同 compile + pytest 流程。
