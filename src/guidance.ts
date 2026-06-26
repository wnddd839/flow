import type { InitResult } from "./core/init.js";
import { DEFAULT_PLATFORMS, PLATFORM_DISPLAY } from "./templates.js";
import { color } from "./ui/render.js";

/** Print the result of an init run in a consistent way. */
export function printInitResult(
  cwd: string,
  editorList: string[],
  result: InitResult,
): void {
  console.log(color.green(`✓ 已在 ${cwd} 生成规范骨架`));
  if (editorList.length) {
    console.log(`  编辑器: ${color.bold(editorList.join(", "))}`);
  } else {
    console.log("  编辑器: (无 — 仅 .agentflow/ 骨架)");
  }
  console.log(
    `  新建 ${color.bold(String(result.created.length))} 个 · 跳过 ${result.skipped.length} 个`,
  );
  if (result.editorsRemoved.length) {
    console.log(`  移除已禁用入口: ${result.editorsRemoved.join(", ")}`);
  }
}

/** Print the "what to do next" guidance after init. */
export function printNextSteps(editorList: string[]): void {
  console.log();
  console.log(color.bold("下一步:"));
  console.log(
    `  ${color.cyan("1.")} 打开 ${color.bold(".agentflow/prompts.md")}，复制「项目首次接手」整段到 AI 对话框（或运行 ${color.bold("flow prompts")}）。`,
  );
  console.log(
    `  ${color.cyan("2.")} 让 AI 按边界声明填写 project.md 等骨架，填完运行 ${color.bold("flow check")}。`,
  );
  console.log(
    `  ${color.cyan("3.")} 日常开发 / 大更新 / 完成自检等场景，也在 ${color.bold("prompts.md")} 里找对应话术。`,
  );
  if (editorList.length === 0) {
    console.log();
    console.log("按需添加薄入口（任选一个或多个）：");
    for (const name of DEFAULT_PLATFORMS) {
      console.log(
        `  ${color.cyan(`flow init ${name.padEnd(12)}`)} ${PLATFORM_DISPLAY[name]}`,
      );
    }
    console.log(
      `  ${color.cyan("flow init cursor claude codex")}   # 多平台一次配置`,
    );
  }
}
