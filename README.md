<div align="center">

<img src="docs/assets/banner.png" alt="Flow — spec foundation for AI coding" width="820">

<h3>好看的离线工作台 CLI，为任意代码仓库铺设 AI 编码规范的地基</h3>

<p>
<a href="https://www.npmjs.com/package/@wnddd8339/flow"><img src="https://img.shields.io/badge/version-0.6.3-346538?style=flat-square" alt="version"></a>
<a href="https://nodejs.org/"><img src="https://img.shields.io/badge/node-18+-1f6c9f?style=flat-square" alt="node"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-787774?style=flat-square" alt="license"></a>
<a href="https://wnddd839.github.io/flow/"><img src="https://img.shields.io/badge/docs-GitHub%20Pages-111111?style=flat-square" alt="docs"></a>
</p>

<p>
<a href="https://wnddd839.github.io/flow/"><b>文档站点</b></a> ·
<a href="https://www.npmjs.com/package/@wnddd8339/flow"><b>npm</b></a> ·
<a href="#工作台">工作台</a> ·
<a href="#快速开始">快速开始</a> ·
<a href="#按编辑器配置">按编辑器配置</a> ·
<a href="#命令">命令</a>
</p>

</div>

---

直接运行 `flow` 进入**交互工作台**：一屏看清项目状态，↑↓ 选择就能 init / check。  
`flow init` 生成 `.agentflow/` 规范文档骨架；按需为所用 AI 工具生成薄入口指针。  
文档内容由首个接手的 AI 分析代码后填写；Flow **不**绑定特定编辑器，**不**强制模型行为。

## 一分钟了解

| | |
|---|---|
| **是什么** | 规范层的「地基」工具 — 工作台 + 骨架 + 薄入口 + 存在性检查 |
| **不是什么** | Agent 编排器、hook 插件、文档代写器 |
| **怎么用** | 跑 `flow` 进工作台 → ↑↓ 选 init → 勾选编辑器 → AI 读 `AGENTS.md` 填骨架 |

## 工作台

在交互终端（Windows Terminal / Cursor 终端 / cmd）里直接运行 `flow`：

```text
 _____ _
|  ___| | _____      __
| |_  | |/ _ \ \ /\ / /
|  _| | | (_) \ V  V /
|_|   |_|\___/ \_/\_/

 Flow · AI 编码规范工作台 · 离线 CLI · 用 ↑↓ 选择，回车确认

 ╭─ System Status ────────────╮  ╭─ Quick Wizard ───────╮
 │  Project  D:\my-app        │  │ 1  Setup / init      │
 │    Phase  not initialized  │  │ 2  Doctor 健康检查    │
 │   Doctor  —                │  │ 3  Instructions      │
 │  Editors  none             │  │ 0  Exit              │
 ╰────────────────────────────╯  ╰──────────────────────╯

 Quick Commands:  /init  /check  /instructions  /tools  /editors  /help

 ◆ 选择操作（↑↓ 选择，回车确认）
 │ ● Setup / init — 选择编辑器并初始化   推荐
 │ ○ Check — 健康检查
 │ ○ Instructions — 触发话术
```

- **仪表盘** 实时显示项目路径、阶段、健康状况、已启用编辑器；每次操作后自动刷新。
- **↑↓ 菜单** 选择动作、回车确认；clack 不可用时自动降级为 `flow ›` 数字/命令输入。
- 选 init → **空格** 勾选编辑器（PATH 上检测到的默认勾选）→ 生成骨架 → 给出下一步指引。

## 快速开始

```bash
# 无需全局安装
flow                                # 进入交互工作台（推荐）
flow init                           # 终端里 ↑↓ 分步选择编辑器
flow init claude                    # 或直接指定平台
flow init cursor claude             # 多平台一次配置

flow check
flow instructions                   # 复制各工具的「填骨架」触发话术
```

**非交互环境**（CI、脚本、管道）：必须显式指定编辑器，或 `--skeleton-only`：

```bash
npx @wnddd8339/flow init claude
npx @wnddd8339/flow init --skeleton-only
```

## 按编辑器配置

内置六种常见 AI 编码工具，**一条命令**即可生成对应薄入口（不必只用 cursor）：

| 命令 | 工具 | 薄入口 |
|------|------|--------|
| `flow init codex` | Codex | `AGENTS.md` |
| `flow init claude` | Claude Code | `CLAUDE.md` |
| `flow init cursor` | Cursor | `.cursor/rules/agentflow.mdc` |
| `flow init kiro` | Kiro | `.kiro/steering/agentflow.md` |
| `flow init qoder` | Qoder | `.qoder/skills/agentflow/SKILL.md` |
| `flow init antigravity` | Antigravity | `.agent/skills/agentflow/SKILL.md` |

组合示例：

```bash
flow init --skeleton-only           # 只要 .agentflow/，不要任何薄入口
flow init cursor claude             # positional：多个平台
flow init --editors qoder,cursor    # 逗号分隔，同上
flow init --force claude            # 覆盖已有 Flow 生成文件
```

## 生成物

```
.agentflow/
  AGENTS.md          总入口（文档索引 + 维护契约）
  project.md         项目是什么
  conventions.md     怎么写代码
  business.md        业务是什么
  pitfalls.md        踩过的坑
  skills/README.md   专项 skill 路由表
```

薄入口**按需生成** — 不选编辑器时，仓库里不会多出六个平台的文件夹。

## 命令

| 命令 | 说明 |
|------|------|
| `flow` | 进入交互工作台（仪表盘 + ↑↓ 菜单：init / check / instructions / tools / editors） |
| `flow init [编辑器...]` | 生成 `.agentflow/`；无参数时在终端里交互选择 |
| `flow init --skeleton-only` | 仅 `.agentflow/`，不生成薄入口 |
| `flow init -i` | 强制尝试交互选择器 |
| `flow check` | 检查骨架、薄入口漂移、骨架是否已被 AI 填充（unfilled 提示） |
| `flow instructions` | 打印工作说明 + 已启用工具的触发话术 |
| `flow editors list` | 查看/管理**本项目**启用的编辑器（`.agentflow/editors.yaml`） |
| `flow tools` | 检测本机 AI 编码 CLI |

完整介绍见 **[文档站点 →](https://wnddd839.github.io/flow/)**

## 设计原则

1. **轻巧** — 离线 CLI，最小依赖，不接管开发流程
2. **地基优先** — 只产文档结构与入口指针，内容交给 AI 与开发者
3. **按需铺入口** — 不默认生成六个平台目录
4. **边界分明** — 每份文档有「只写 / 不写」声明
5. **契约靠提示词** — `AGENTS.md` 写明维护约定；Flow 不拦截、不强制
6. **平台中立** — 支持多编辑器薄入口，不做深度绑定

## 开发

```bash
npm install
npm run check          # lint + typecheck + build + test
node dist/cli.js --version
```

> **v0.6.3** 起 `flow`（无参数）进入交互工作台：仪表盘 + ↑↓ 菜单，clack 不可用时降级为数字输入。  
> **v0.6.2** 起 `flow init` 支持 ↑↓ 分步向导（`@clack/prompts` 1.6），并修复 Windows CMD 的 TTY 检测。  
> **v0.6.1** 起 CLI 为 TypeScript 实现（npm 包 [`@wnddd8339/flow`](https://www.npmjs.com/package/@wnddd8339/flow)）。v0.5 及更早的 Python 版已移至 [`archive/python/`](archive/python/)。
