<div align="center">

<img src="docs/assets/banner.svg" alt="Flow — AI 编码规范地基" width="100%">

<br><br>

**轻巧的离线 CLI，为任意代码仓库铺设 AI 编码规范的地基**

[![version](https://img.shields.io/badge/version-0.5.0-346538?style=flat-square)](https://github.com/wnddd839/flow/releases)
[![python](https://img.shields.io/badge/python-3.11+-1f6c9f?style=flat-square)](https://www.python.org/)
[![license](https://img.shields.io/badge/license-MIT-787774?style=flat-square)](LICENSE)
[![docs](https://img.shields.io/badge/docs-GitHub%20Pages-111111?style=flat-square)](https://wnddd839.github.io/flow/)

[文档站点](https://wnddd839.github.io/flow/) · [快速开始](#快速开始) · [设计原则](#设计原则)

</div>

---

`flow init` 生成 `.agentflow/` 规范文档骨架；按需为所用 AI 工具生成薄入口指针。  
文档内容由首个接手的 AI 分析代码后填写；Flow **不**绑定特定编辑器，**不**强制模型行为。

## 一分钟了解

| | |
|---|---|
| **是什么** | 规范层的「地基」工具 — 骨架、薄入口、存在性检查 |
| **不是什么** | Agent 编排器、hook 插件、文档代写器 |
| **怎么用** | `pip install` → `flow init` → AI 读 `AGENTS.md` 填骨架 |

## 快速开始

```bash
pip install git+https://github.com/wnddd839/flow.git

flow init                      # TTY 下交互勾选编辑器
flow init --skeleton-only      # 仅 .agentflow/，不要薄入口
flow init cursor               # 骨架 + Cursor 薄入口
flow check
```

交互工作台：直接运行 `flow`，支持 `/init` `/check` `/tools` `/help`。

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

薄入口（如 `.cursor/rules/agentflow.mdc`）**按需生成** — 不选编辑器时，仓库里不会多出六个平台的文件夹。

## 命令

| 命令 | 说明 |
|------|------|
| `flow init` | 生成 `.agentflow/`；TTY 下交互选择编辑器 |
| `flow init cursor` | 生成骨架 + 指定平台薄入口 |
| `flow init --skeleton-only` | 仅 `.agentflow/`，不生成薄入口 |
| `flow check` | 检查骨架与已启用入口是否齐全 |
| `flow editors list` | 查看/管理启用的编辑器 |
| `flow tools` | 检测本机 AI 编码 CLI |
| `flow instructions` | 打印 agent 工作说明摘要 |

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
python -m pip install -e ".[dev]"
python -m compileall -f agentflow tests
python -m pytest -q
```
