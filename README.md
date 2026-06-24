# Flow

项目规范文档初始化器。一句话：`flow init` 生成一组边界严格、能自我维护的规范文档骨架，让 AI 编码工具读到后自动遵守、填写、维护。

## 做什么

`flow init` 在当前项目生成：

```text
.agentflow/
  AGENTS.md          总入口（纪律 + 文档索引 + 自维护契约）
  project.md         项目是什么
  conventions.md     怎么写代码
  business.md        业务是什么
  pitfalls.md        踩过的坑
  skills/README.md   专项 skill 路由表
AGENTS.md            Codex 薄指针（指向 .agentflow/AGENTS.md）
+ 各 AI 工具薄入口（默认 6 平台全开）
```

**不生成** state、handoff、skill 包管理、工作流路由等旧功能。

## 快速开始

```bash
pip install -e .
flow init
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
| `flow init` | 生成规范骨架（默认 6 平台薄入口） |
| `flow init --editors qoder,cursor` | 只生成指定平台入口 |
| `flow check` | 检查骨架文件是否齐全（`doctor` 为别名） |
| `flow editors list` | 查看/管理启用的编辑器 |
| `flow tools` | 检测本机 AI 编码 CLI |
| `flow instructions` | 打印 agent 工作说明摘要 |

## 设计原则

1. **用户不填内容** — 骨架由 Flow 生成，首个接手的 AI 分析代码后填写。
2. **文档边界严格** — 每个文件有 ✅/❌ 边界声明，防止写成 README。
3. **模型自维护** — `AGENTS.md` 里写死维护契约（祈使句）。
4. **离线** — 无 API、无网络依赖。

## 开发

```bash
python -m pip install -e ".[dev]"
python -m compileall -f agentflow tests
python -m pytest -q
```
