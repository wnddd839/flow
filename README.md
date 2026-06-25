# Flow

轻巧的离线 CLI，为任意代码仓库铺设 AI 编码规范的地基。

`flow init` 生成 `.agentflow/` 规范文档骨架；按需为所用 AI 工具生成薄入口指针。文档内容由首个接手的 AI 分析代码后填写；Flow 不绑定特定编辑器，也不强制模型行为。

## 定位

Flow 是辅助开发者的基础设施，不是 agent 编排器。

**只做：**

- 生成结构清晰、边界分明的规范文档骨架
- 按所选平台，在工具原生路径写入指向 `.agentflow/AGENTS.md` 的薄指针
- `check` 校验骨架与已启用入口文件是否存在
- `editors` 管理启用哪些平台的薄入口

**不做：**

- 工作流编排、handoff、状态追踪、skill 包管理
- 绑定某一 agent 或编辑器的 hook / 插件
- 代替 AI 填写或校验文档内容
- 默认在根目录堆满六个平台的文件夹

## 生成物

**始终生成**（`.agentflow/`）：

```text
.agentflow/
  AGENTS.md          总入口（文档索引 + 维护契约）
  project.md         项目是什么
  conventions.md     怎么写代码
  business.md        业务是什么
  pitfalls.md        踩过的坑
  skills/README.md   专项 skill 路由表
```

**按需生成**（所选编辑器的薄入口，例如 Cursor → `.cursor/rules/agentflow.mdc`）。  
不选任何编辑器时，仓库里不会多出 `CLAUDE.md`、`AGENTS.md`（Codex）等文件。

## 快速开始

```bash
pip install -e .

# 交互勾选编辑器（TTY 下弹出多选列表）
flow init

# 只铺骨架，不要任何薄入口
flow init --skeleton-only

# 直接指定平台（可写多个）
flow init cursor
flow init cursor claude
flow init --editors qoder,cursor

flow check
```

交互工作台：

```bash
flow
# /init  /check  /tools  /instructions  /help
```

## 命令

| 命令 | 说明 |
|------|------|
| `flow init` | 生成 `.agentflow/`；TTY 下交互选择编辑器 |
| `flow init cursor` | 生成骨架 + 指定平台薄入口 |
| `flow init --skeleton-only` | 仅 `.agentflow/`，不生成薄入口 |
| `flow init --editors a,b` | 逗号分隔，同 positional |
| `flow check` | 检查骨架与已启用入口是否齐全（`doctor` 为别名） |
| `flow editors list` | 查看/管理启用的编辑器 |
| `flow tools` | 检测本机 AI 编码 CLI |
| `flow instructions` | 打印 agent 工作说明摘要 |

## 设计原则

1. **轻巧** — 离线 CLI，最小依赖，不接管开发流程。
2. **地基优先** — 只产文档结构与入口指针，内容交给 AI 与开发者。
3. **按需铺入口** — 不默认生成六个平台目录，减少仓库杂乱。
4. **边界分明** — 每份文档有「只写 / 不写」声明，防止堆成一个大 README。
5. **契约靠提示词** — `AGENTS.md` 写明 AI 应如何维护文档；Flow 不拦截、不强制。
6. **平台中立** — 支持多编辑器薄入口，但不绑定任一平台做深度集成。

## 开发

```bash
python -m pip install -e ".[dev]"
python -m compileall -f agentflow tests
python -m pytest -q
```
