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

- **模块**：`src/` 下单文件单职责；文件名小写驼峰或目录索引（`init-ui.ts`、`editors/config.ts`）。
- **公开 API**：函数用动词短语（`initProject`、`doctorProject`、`applyEditors`）；类型/接口用 PascalCase（`DoctorReport`、`EditorSpec`）。
- **常量**：全大写蛇形（`BASE_REQUIRED_FILES`、`AGENTFLOW_GENERATED_MARKER`、`DEFAULT_PLATFORMS`）。
- **CLI 程序名**：对外品牌为 `flow`；npm 包名为 `@wnddd8339/flow`。

## 代码结构

| 放什么 | 放哪里 |
|--------|--------|
| 磁盘写入 / 检查逻辑 | `src/core/` |
| 纯字符串模板（骨架、薄入口） | `src/templates.ts` |
| 用户级编辑器配置、名称校验、入口 reconcile | `src/editors/` |
| `flow init` 编辑器多选 | `src/init-ui.ts` + `src/terminal.ts` |
| 环境探测（PATH 工具） | `src/diagnostics/tools.ts` |
| Commander 命令注册与分发 | `src/cli.ts` |
| 版本号 | `src/version.ts` |

**新增 CLI 子命令**：在 `src/cli.ts` 用 Commander 注册 handler。

**新增内置编辑器**：在 `src/templates.ts` 同步更新 `DEFAULT_PLATFORMS`、`PLATFORM_DISPLAY`、`PLATFORM_ENTRYPOINTS`，并补充测试。

**editors 与 tools 是两个独立清单**：`DEFAULT_PLATFORMS`（薄入口写入目标）与 `KNOWN_TOOLS`（PATH 上可探测的 AI CLI）回答不同问题，不必逐一对应。

**测试**：`tests/` 下按模块分 `*.test.ts`；临时目录用 `mkdtempSync`；CLI 集成测试通过 `execFileSync` 调用 `dist/cli.js`。

## 风格与格式

- 使用 Biome 做 lint 与 format（`npm run lint` / `npm run format`）。
- 严格 TypeScript（`strict: true`）；ESM 模块，导入带 `.js` 扩展名（Node16/bundler 约定）。
- 文件读写显式 `utf8`。
- 用户可见输出用 `console.log` / `console.error`；交互用 `@clack/prompts`。
- 模板正文用 `util/dedent.ts`，保持生成 Markdown 可读。
- 文档与模板正文不使用 emoji；边界声明用「只写 / 不写」纯文本。

## 禁用模式

- **不引入新运行时依赖**：保持离线、轻量；新能力优先 Node 内置 API。
- **不在 `templates.ts` 写盘**：模板模块只返回字符串；持久化集中在 `core/` / `editors/`。
- **不在骨架模板里预填目标项目内容**：`tests/templates.test.ts` 禁止骨架出现项目专属描述。
- **不恢复 Python 主线**：历史实现仅保留在 `archive/python/`，新功能只加在 `src/`。
