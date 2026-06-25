import * as p from "@clack/prompts";
import { detectTools } from "./diagnostics/tools.js";
import { normalizeEditorNames } from "./editors/index.js";
import {
  DEFAULT_PLATFORMS,
  PLATFORM_DISPLAY,
  PLATFORM_ENTRYPOINTS,
} from "./templates.js";

export function canRunInteractivePicker(isTty?: boolean): boolean {
  if (isTty !== undefined) return isTty;
  return Boolean(process.stdin.isTTY && process.stdout.isTTY);
}

export async function pickEditors(
  options: { isTty?: boolean } = {},
): Promise<string[]> {
  if (!canRunInteractivePicker(options.isTty)) {
    return [];
  }

  const onPath = new Set(
    detectTools()
      .filter((t) => t.status === "ok")
      .map((t) => t.name),
  );

  const choices = DEFAULT_PLATFORMS.map((name) => {
    const display = PLATFORM_DISPLAY[name];
    const entry = PLATFORM_ENTRYPOINTS[name];
    const pathLabel = onPath.has(name) ? "on PATH" : "not on PATH";
    return {
      value: name,
      label: `${display.padEnd(14)} (${name}) -> ${entry}  [${pathLabel}]`,
    };
  });

  try {
    const result = await p.multiselect({
      message: "选择要生成薄入口的编辑器（空格切换，回车确认；不选则仅骨架）",
      options: choices,
      required: false,
    });

    if (p.isCancel(result) || !result?.length) {
      return [];
    }
    return normalizeEditorNames(result);
  } catch {
    return [];
  }
}
