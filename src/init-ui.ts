import * as readline from "node:readline/promises";
import * as p from "@clack/prompts";
import { detectTools } from "./diagnostics/tools.js";
import { normalizeEditorNames } from "./editors/index.js";
import {
  DEFAULT_PLATFORMS,
  PLATFORM_DISPLAY,
  PLATFORM_ENTRYPOINTS,
  type PlatformName,
} from "./templates.js";
import {
  canRunInteractivePicker,
  describeTtyState,
  interactiveStreams,
} from "./terminal.js";

export { canRunInteractivePicker } from "./terminal.js";

export class PickCancelledError extends Error {
  override name = "PickCancelledError";
}

function editorsOnPath(): Set<PlatformName> {
  const onPath = new Set<string>(
    detectTools()
      .filter((t) => t.status === "ok")
      .map((t) => t.name),
  );
  return new Set(DEFAULT_PLATFORMS.filter((name) => onPath.has(name)));
}

function editorChoices(onPath: Set<PlatformName>) {
  return DEFAULT_PLATFORMS.map((name) => {
    const display = PLATFORM_DISPLAY[name];
    const pathHint = onPath.has(name) ? "on PATH" : "not on PATH";
    return {
      value: name,
      label: `${display} (${name})`,
      hint: `${PLATFORM_ENTRYPOINTS[name]} · ${pathHint}`,
    };
  });
}

async function pickEditorsReadline(
  onPath: Set<PlatformName>,
): Promise<string[]> {
  const { input, output } = interactiveStreams();
  const rl = readline.createInterface({ input, output });
  console.log();
  console.log("选择编辑器（输入序号，多个用逗号分隔；直接回车 = 仅骨架）：");
  console.log();
  for (const [index, name] of DEFAULT_PLATFORMS.entries()) {
    const pathMark = onPath.has(name) ? " [on PATH]" : "";
    console.log(
      `  ${String(index + 1).padStart(2)}. ${PLATFORM_DISPLAY[name].padEnd(14)} ${name}${pathMark}`,
    );
  }
  console.log("   0. 仅骨架");
  console.log();

  const answer = (await rl.question("> ")).trim();
  rl.close();

  if (!answer || answer === "0") {
    return [];
  }

  const indices = answer
    .split(/[,，\s]+/)
    .map((s) => Number.parseInt(s.trim(), 10))
    .filter((n) => !Number.isNaN(n) && n >= 1 && n <= DEFAULT_PLATFORMS.length);

  if (!indices.length) {
    return [];
  }

  const picked = [...new Set(indices.map((i) => DEFAULT_PLATFORMS[i - 1]))];
  return normalizeEditorNames(picked);
}

async function runClackWizard(onPath: Set<PlatformName>): Promise<string[]> {
  const pathSummary =
    onPath.size > 0 ? [...onPath].join(", ") : "未检测到 PATH 上的工具";

  p.intro("Flow init");

  const mode = await p.select({
    message: "如何初始化？",
    options: [
      {
        value: "pick",
        label: "选择编辑器",
        hint: "↑↓ 移动 · 回车确认",
      },
      {
        value: "auto-path",
        label: "自动启用 PATH 上的工具",
        hint: pathSummary,
      },
      {
        value: "skeleton",
        label: "仅生成 .agentflow/ 骨架",
        hint: "不创建薄入口",
      },
    ],
  });

  if (p.isCancel(mode)) {
    p.cancel("已取消");
    throw new PickCancelledError();
  }

  if (mode === "skeleton") {
    p.outro("将仅创建骨架");
    return [];
  }

  if (mode === "auto-path") {
    const editors = [...onPath];
    if (editors.length) {
      p.outro(`将启用: ${editors.join(", ")}`);
      return normalizeEditorNames(editors);
    }
    p.outro("未检测到工具，将仅创建骨架");
    return [];
  }

  const choices = editorChoices(onPath);
  const initialValues = DEFAULT_PLATFORMS.filter((name) => onPath.has(name));

  const result = await p.multiselect({
    message: "选择要生成薄入口的编辑器",
    options: choices,
    initialValues,
    required: false,
    maxItems: 8,
  });

  if (p.isCancel(result)) {
    p.cancel("已取消");
    throw new PickCancelledError();
  }

  if (!result?.length) {
    p.outro("将仅创建骨架");
    return [];
  }

  p.outro(`已选: ${result.join(", ")}`);
  return normalizeEditorNames(result);
}

/**
 * Interactive editor picker. Returns `null` when the environment cannot run
 * interactive UI (non-TTY). Returns `[]` when the user chose skeleton-only.
 */
export async function pickEditors(
  options: { isTty?: boolean; forceInteractive?: boolean } = {},
): Promise<string[] | null> {
  if (options.isTty === false) {
    return null;
  }

  const interactive =
    options.forceInteractive ?? canRunInteractivePicker(options.isTty);
  if (!interactive) {
    return null;
  }

  const onPath = editorsOnPath();

  try {
    return await runClackWizard(onPath);
  } catch (err) {
    if (err instanceof PickCancelledError) {
      throw err;
    }
    try {
      console.log();
      console.log("↑↓ 选择器不可用，改用数字菜单：");
      const picked = await pickEditorsReadline(onPath);
      if (picked.length) {
        console.log(`已选: ${picked.join(", ")}`);
      } else {
        console.log("将仅创建骨架");
      }
      return picked;
    } catch {
      return null;
    }
  }
}

export function interactivePickerHint(): string {
  return describeTtyState();
}
