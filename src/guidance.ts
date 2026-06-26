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
    `  ${color.cyan("1.")} 让接手的 AI 编码助手先读 ${color.bold(".agentflow/AGENTS.md")}，按各文件边界声明填写骨架。`,
  );
  console.log(
    `  ${color.cyan("2.")} 填完后运行 ${color.bold("flow check")} 校验骨架与薄入口是否齐全、是否漂移。`,
  );
  console.log(
    `  ${color.cyan("3.")} 运行 ${color.bold("flow instructions")} 查看已启用工具的触发话术（复制到对话框）。`,
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
