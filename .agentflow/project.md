# 项目说明

<!-- ═══════════════════════════════════════════════════════════
     本文件边界（不可删除，不可改写）
     ✅ 只写：这个项目【是什么】：一句话定位、技术栈、整体架构、怎么启动运行
     ❌ 不写：怎么写代码（→ conventions.md）、业务规则与术语（→ business.md）、踩过的坑（→ pitfalls.md）、专项操作流程（→ skills/）
     判断标准：如果一段内容换到别的项目还能用，它就不属于这里。
     ═══════════════════════════════════════════════════════════ -->

<!-- 维护契约：由首个接触本项目的 AI 编码助手分析代码后填写；
     后续每次接手时核对，与代码不符就修正。不要删除章节标题。 -->

## 一句话定位

离线 Python CLI（`flow` / `agentflow`），在任意代码仓库中生成边界严格、可自我维护的 AI 编码规范文档骨架，并为 Codex、Claude Code、Cursor 等 6 个平台写入薄入口指针。

## 技术栈

| 项 | 版本 / 说明 |
|----|------------|
| 语言 | Python ≥ 3.11 |
| 运行时依赖 | `rich`（终端 UI）、`prompt_toolkit`（REPL 补全） |
| 开发依赖 | `pytest` |
| 打包 | `setuptools`，入口脚本 `flow` 与 `agentflow` 均指向 `agentflow.cli:main` |
| 当前版本 | `0.4.0`（见 `agentflow/__init__.py`） |
| 网络 | 无 API 调用、无网络依赖 |

## 架构概览

```
agentflow/
  cli.py          命令行入口（init / check / editors / tools / instructions）
  core.py         init_project、doctor_project
  templates.py    规范文档与薄入口的字符串模板（只产字符串，不写盘）
  editors.py      编辑器配置（~/.agentflow/editors.yaml）与薄入口 reconcile
  diagnostics.py  本地工具检测与诊断输出
  repl.py         无参数 `flow` 时的交互工作台
tests/            unittest / pytest 兼容测试
```

**数据流（`flow init`）：**

1. `templates.py` 生成 `.agentflow/` 下 6 个规范文件内容。
2. `editors.py` 读取/写入用户级 `editors.yaml`，决定启用哪些平台。
3. `apply_editors` 在项目根写入各平台薄入口（Codex 为根 `AGENTS.md` 指针，其余为单行指向 `.agentflow/AGENTS.md`）。
4. `doctor_project` 校验骨架文件 + 已启用编辑器的入口文件是否齐全。

用户级配置目录：`~/.agentflow/`（可通过环境变量 `AGENTFLOW_HOME` 覆盖）。

## 启动与运行

**安装（开发模式）：**

```bash
python -m pip install -e ".[dev]"
```

**初始化当前项目规范骨架：**

```bash
flow init
flow init --editors qoder,cursor   # 只启用指定平台
flow init --force                  # 覆盖已有文件
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
