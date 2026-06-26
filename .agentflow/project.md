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

轻巧的离线 TypeScript CLI（`flow`，npm 包 `@wnddd8339/flow`），为任意代码仓库铺设 AI 编码规范的地基：生成 `.agentflow/` 文档骨架，并按需写入各 AI 工具的薄入口指针。不编排工作流，不绑定特定 agent。

## 产品边界

| Flow 负责 | Flow 不负责 |
|-----------|-------------|
| 规范文档骨架与薄入口 | 文档正文（由 AI / 开发者填写） |
| 文件存在性与薄入口漂移检查（`check`） | 文档内容质量或是否填完 |
| 多平台入口路径管理（`editors`） | 绑定某一编辑器做 hook 或深度集成 |
| 本地 AI CLI 探测（`tools`） | 强制模型遵守维护契约 |

## 技术栈

| 项 | 版本 / 说明 |
|----|------------|
| 语言 | TypeScript（Node.js ≥ 18） |
| 运行时依赖 | `commander`（CLI）、`@clack/prompts` 1.6（交互 ↑↓ 选择） |
| 开发依赖 | `vitest`、`tsup`、`typescript`、`@biomejs/biome` |
| 打包 | `tsup` 单文件 ESM → `dist/cli.js`，`bin.flow` 指向该入口 |
| 当前版本 | `0.6.2`（见 `src/version.ts` 与 `package.json`） |
| 分发 | npm：`@wnddd8339/flow`（`npx @wnddd8339/flow`） |
| 网络 | 无 API 调用、无网络依赖 |

## 架构概览

```
src/
  cli.ts              命令行入口（init / check / editors / tools / instructions）
  core/               initProject、doctorProject、writeText
  templates.ts        规范文档与薄入口的字符串模板（只产字符串，不写盘）
  editors/            编辑器配置（项目级 `.agentflow/editors.yaml`）、校验与 reconcile
  init-ui.ts          flow init 分步向导（@clack/prompts multiselect）
  terminal.ts         TTY 检测、Windows CONIN$ 回退
  diagnostics/tools.ts 本地 AI CLI 检测
  util/dedent.ts      模板缩进处理
tests/                vitest 单元与 CLI 集成测试
archive/python/       v0.5 及更早 Python 实现（已归档，不参与 CI）
```

**数据流（`flow init`）：**

1. `init-ui.pickEditors`（终端交互）或命令行参数决定本次启用哪些平台；无参数且非交互环境会报错并提示显式指定。
2. `templates.ts` 生成 `.agentflow/` 下 6 个规范文件内容。
3. `editors/config.ts` 读取/写入**项目级** `.agentflow/editors.yaml`（全局 `~/.agentflow/` 仅作回退读取）。
4. `editors/apply.ts` 为已启用平台写入薄入口（Codex 为根 `AGENTS.md` 指针，其余为单行指向 `.agentflow/AGENTS.md`），并安全移除已禁用平台的旧入口。
5. `doctorProject` 校验骨架文件 + 已启用编辑器的入口文件是否齐全，检测薄入口漂移，并报告骨架章节是否仍未填充（unfilled 不导致 exit 1）。

配置目录：项目级 `.agentflow/editors.yaml`；全局 `~/.agentflow/` 可通过 `AGENTFLOW_HOME` 覆盖（仅在没有项目级文件时使用）。

## 启动与运行

**安装（开发模式）：**

```bash
npm install
npm run build
```

**初始化当前项目规范骨架：**

```bash
flow                           # 终端 ↑↓ 快捷菜单
flow init                      # ↑↓ 分步选择编辑器；非交互环境需显式指定
flow init cursor               # 骨架 + Cursor 薄入口
flow init cursor claude        # 多个平台 positional
flow init --editors qoder,cursor
flow init --skeleton-only      # 仅 .agentflow/，不生成薄入口
flow init -i                   # 强制尝试交互选择器
flow init --force              # 覆盖已有文件
```

**健康检查与诊断：**

```bash
flow check      # doctor 为别名；缺失或漂移时 exit code 1
flow tools      # 检测本机 AI CLI 是否在 PATH
flow instructions
```

**测试与检查：**

```bash
npm run check   # lint + typecheck + build + test
```

CI（`.github/workflows/ci.yml`）在 Node 22 上执行相同流程。
