# 业务说明

<!-- ═══════════════════════════════════════════════════════════
     本文件边界（不可删除，不可改写）
     只写：这个项目的【业务】：领域概念、核心流程、术语表
     不写：技术实现/架构（→ project.md）、代码风格（→ conventions.md）、技术踩坑（→ pitfalls.md）
     判断标准：如果一段内容换到别的项目还能用，它就不属于这里。
     ═══════════════════════════════════════════════════════════ -->

<!-- 维护契约：由首个接触本项目的 AI 编码助手分析代码后填写；
     后续每次接手时核对，与代码不符就修正。不要删除章节标题。 -->

## 核心概念

- **规范地基**：Flow 在项目中铺设的基础层——文档骨架、薄入口、存在性检查。不是 agent 本身，也不是工作流引擎。
- **规范骨架（spec skeleton）**：`flow init` 在 `.agentflow/` 下生成的一组文档框架，含总入口 `AGENTS.md`、四份子文档（project / conventions / business / pitfalls）及 skill 路由表。正文由首个接手的 AI 分析代码后填写，用户无需手写。
- **文档边界**：每份 `.md` 顶部的「只写 / 不写」声明定义职责范围，防止所有信息堆进一个 README。
- **维护契约**：写在 `AGENTS.md` 中的 AI 工作约定——首次接手填骨架、改动后更新文档、信息不重复、以代码为准。靠提示词传达，Flow 工具层不强制执行。
- **薄入口（thin entrypoint）**：各 AI 工具原生会读取的路径（如 `CLAUDE.md`、`.cursor/rules/agentflow.mdc`）上的极短指针，内容仅指向 `.agentflow/AGENTS.md`。
- **编辑器 / 平台**：内置六种 AI 编码环境（codex、claude、cursor、kiro、qoder、antigravity）；启用列表保存在用户级 `~/.agentflow/editors.yaml`。可缩减或自定义，但不意味 Flow 绑定某一平台。
- **Check**：校验规范骨架与已启用平台入口是否齐全；并检测薄入口内容是否仍指向 `.agentflow/AGENTS.md`（漂移）。

## 主要流程

### 1. 项目首次接入 Flow

1. 开发者在目标仓库执行 `flow init`（交互选择或 `flow init cursor` 等），默认只生成 `.agentflow/`；薄入口按需勾选。
2. Flow 写入 `.agentflow/` 规范骨架 + 已启用平台的薄入口。
3. 开发者用任意 AI 编码工具打开项目；工具读到薄入口 → `.agentflow/AGENTS.md`。
4. 首个 AI 助手通读规范、分析代码库，填写 `project.md` 等章节。

### 2. 日常 AI 协作

1. AI 开工前读 `AGENTS.md` 及索引文档，重述目标与范围。
2. AI 按请求改代码，范围最小化。
3. 改完后跑测试/lint，按契约更新受影响的规范文档。
4. 交接时报告：改动文件、验证命令、结果、风险、下一步。

以上步骤 3、4 靠提示词与开发者监督，Flow 不参与。

### 3. 编辑器配置变更

1. `flow editors list` 查看启用状态。
2. `flow editors add/remove` 或 `add-custom/remove-custom` 调整配置。
3. `flow editors apply`（add/remove 会自动 apply）在项目内创建或安全移除薄入口。
4. `flow check` 确认所需文件仍在。

### 4. 健康检查

1. `flow check` 列出缺失的骨架或入口文件。
2. 附带本地 AI CLI 是否在 PATH 的诊断（仅供参考）。

## 术语表

| 术语 | 含义 |
|------|------|
| Flow | 对外 CLI 品牌名，命令为 `flow` |
| @wnddd8339/flow | npm 包名，与 Flow 指同一工具 |
| 地基 | Flow 产出的结构层：骨架 + 薄入口 + check，不含文档正文 |
| Init | 生成规范骨架与薄入口，不询问业务问题 |
| Force | `--force` 覆盖已存在的 Flow 生成文件 |
| 骨架 | 带章节标题与 HTML 注释提示、正文待填的 `.md` 模板实例 |
| 薄入口 | 各平台目录下的单行规范指针，非完整规范正文 |
| 内置编辑器 | `templates.DEFAULT_PLATFORMS` 定义的六种平台 |
| 自定义编辑器 | 用户通过 `editors add-custom` 注册的额外平台与入口路径 |
| Reconcile | `apply_editors` 使项目内入口文件与 `editors.yaml` 启用列表一致 |
| 维护契约 | AI 应如何维护文档的提示词约定（见 `AGENTS.md`） |
| Skill 路由 | `.agentflow/skills/README.md` 中的任务关键词 → 专项 skill 映射表 |
