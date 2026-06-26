import { existsSync } from "node:fs";
import { join, resolve } from "node:path";
import * as readline from "node:readline/promises";
import * as clack from "@clack/prompts";
import { doctorProject } from "./core/check.js";
import { initProject } from "./core/init.js";
import { detectTools } from "./diagnostics/tools.js";
import { getEnabledEditors } from "./editors/index.js";
import { printInitResult, printNextSteps } from "./guidance.js";
import { PickCancelledError, pickEditors } from "./init-ui.js";
import { AGENT_INSTRUCTIONS, kickoffPrompt } from "./templates.js";
import { canRunInteractivePicker, interactiveStreams } from "./terminal.js";
import {
  color,
  logo,
  panel,
  pills,
  sideBySide,
  terminalWidth,
} from "./ui/render.js";
import { VERSION } from "./version.js";

interface ProjectStatus {
  initialized: boolean;
  ok: boolean;
  missing: number;
  unfilled: number;
  editors: string[];
}

function readStatus(root: string): ProjectStatus {
  const initialized = existsSync(join(root, ".agentflow", "AGENTS.md"));
  const report = doctorProject(root);
  const editors = getEnabledEditors({ projectDir: root }).map((s) => s.name);
  return {
    initialized,
    ok: report.ok,
    missing: report.missing.length,
    unfilled: report.unfilled.length,
    editors,
  };
}

function phaseLabel(status: ProjectStatus): string {
  if (!status.initialized) return color.brightRed("not initialized");
  if (status.unfilled > 0) return color.brightYellow("initialized · 待填写");
  if (status.ok) return color.brightGreen("ready");
  return color.brightYellow("initialized");
}

function doctorLabel(status: ProjectStatus): string {
  if (!status.initialized) return color.gray("—");
  if (status.ok && status.unfilled === 0) return color.brightGreen("● OK");
  if (status.ok && status.unfilled > 0)
    return color.brightYellow(`● ${status.unfilled} 个章节待填写`);
  return color.brightYellow(`● ${status.missing} 个文件缺失`);
}

function renderDashboard(root: string, status: ProjectStatus): string {
  const total = Math.min(terminalWidth() - 2, 88);
  const label = (text: string) => color.gray(text.padStart(8));

  const statusBody = [
    `${label("Project")}  ${color.white(root)}`,
    `${label("Phase")}  ${phaseLabel(status)}`,
    `${label("Doctor")}  ${doctorLabel(status)}`,
    `${label("Editors")}  ${
      status.editors.length
        ? color.brightBlue(status.editors.join(", "))
        : color.gray("none")
    }`,
  ];

  const wizardBody = [
    `${color.brightCyan("1")}  ${color.white("Setup / init 初始化")}`,
    `${color.brightCyan("2")}  ${color.white("Doctor 健康检查")}`,
    `${color.brightCyan("3")}  ${color.white("Instructions 触发话术")}`,
    `${color.brightCyan("0")}  ${color.gray("Exit 退出")}`,
  ];

  const out: string[] = [];
  out.push("");
  out.push(logo());
  out.push("");
  out.push(`  ${color.dim(`Flow · AI 编码规范工作台 v${VERSION} · 离线 CLI`)}`);
  out.push(`  ${color.dim("用 ↑↓ 选择，回车确认；或按 /help 看全部命令")}`);
  out.push("");

  if (total >= 76) {
    const gap = 2;
    const leftW = Math.floor((total - gap) * 0.6);
    const rightW = total - gap - leftW;
    const left = panel("System Status", statusBody, leftW);
    const right = panel("Quick Wizard", wizardBody, rightW);
    for (const line of sideBySide(left, right, gap)) {
      out.push(`  ${line}`);
    }
  } else {
    for (const line of panel("System Status", statusBody, total)) {
      out.push(`  ${line}`);
    }
    for (const line of panel("Quick Wizard", wizardBody, total)) {
      out.push(`  ${line}`);
    }
  }

  out.push("");
  out.push(
    `  ${color.dim("Quick Commands:")} ${pills([
      "/init",
      "/check",
      "/instructions",
      "/tools",
      "/editors",
      "/help",
    ])}`,
  );
  out.push("");
  return out.join("\n");
}

async function actionInit(root: string): Promise<void> {
  let editors: string[] | null;
  try {
    editors = await pickEditors({ forceInteractive: true });
  } catch (err) {
    if (err instanceof PickCancelledError) {
      clack.log.info("已取消 init");
      return;
    }
    throw err;
  }
  if (editors === null) {
    clack.log.warn("当前终端无法交互选择，改用 `flow init <编辑器>`。");
    return;
  }
  const result = initProject(root, { editors });
  console.log();
  printInitResult(root, editors, result);
  printNextSteps(editors);
}

function actionCheck(root: string): void {
  const report = doctorProject(root);
  console.log();
  if (report.ok && report.unfilled.length === 0) {
    console.log(
      color.brightGreen("✓ check: 全部就绪 — 骨架与薄入口齐全且已填写"),
    );
  } else if (report.ok) {
    console.log(color.brightGreen("✓ check: 文件齐全"));
  } else {
    if (report.missing.length) {
      console.log(color.brightYellow("● 缺失文件:"));
      for (const item of report.missing) console.log(`    - ${item}`);
    }
    if (report.drift.length) {
      console.log(
        color.brightYellow("● 薄入口漂移（已不指向 .agentflow/AGENTS.md）:"),
      );
      for (const item of report.drift)
        console.log(
          `    - ${item}  ${color.dim("(修复: flow editors apply --force)")}`,
        );
    }
  }
  if (report.unfilled.length) {
    console.log(color.brightYellow("● 骨架尚未被 AI 填写，以下章节仍为空白:"));
    for (const item of report.unfilled) console.log(`    - ${item}`);
    console.log(
      color.dim(
        "    让接手的 AI 读 .agentflow/AGENTS.md 后按边界声明填写，或用 /instructions 看触发话术。",
      ),
    );
  }
}

function actionInstructions(root: string): void {
  console.log();
  if (!existsSync(join(root, ".agentflow", "AGENTS.md"))) {
    console.log(color.brightYellow("项目尚未初始化，请先 init。"));
    return;
  }
  console.log(AGENT_INSTRUCTIONS);
  const enabled = getEnabledEditors({ projectDir: root });
  const prompts = enabled
    .map((spec) => {
      const text = kickoffPrompt(spec.name);
      return text ? { display: spec.display, text } : null;
    })
    .filter((p): p is { display: string; text: string } => p !== null);
  if (prompts.length) {
    console.log();
    console.log(color.bold("首次接手触发话术（复制到对应工具对话框）:"));
    for (const { display, text } of prompts) {
      console.log();
      console.log(color.brightCyan(`— ${display} —`));
      console.log(text);
    }
  }
}

function actionTools(): void {
  console.log();
  console.log(color.bold("本机 AI 编码工具:"));
  for (const tool of detectTools()) {
    const mark =
      tool.status === "ok" ? color.brightGreen("●") : color.gray("○");
    const where = tool.path || color.gray("不在 PATH");
    console.log(`  ${mark} ${tool.display.padEnd(14)} ${where}`);
  }
}

function actionEditors(root: string): void {
  console.log();
  const enabled = getEnabledEditors({ projectDir: root });
  if (!enabled.length) {
    console.log(
      color.gray("本项目尚未启用任何编辑器薄入口。用 1 / init 选择。"),
    );
    return;
  }
  console.log(color.bold("本项目已启用编辑器:"));
  for (const spec of enabled) {
    console.log(
      `  ${color.brightBlue("●")} ${spec.name.padEnd(14)} -> ${spec.entrypoint}`,
    );
  }
}

function printHelp(): void {
  console.log();
  console.log(color.bold("命令:"));
  const rows: [string, string][] = [
    ["1 / init", "选择编辑器并生成 .agentflow/ 骨架与薄入口"],
    ["2 / check", "检查骨架、薄入口漂移、未填写章节"],
    ["3 / instructions", "打印工作说明与各工具触发话术"],
    ["tools", "检测本机 AI 编码 CLI"],
    ["editors", "查看本项目已启用编辑器"],
    ["help", "显示本帮助"],
    ["0 / quit", "退出工作台"],
  ];
  for (const [cmd, desc] of rows) {
    console.log(`  ${color.brightCyan(cmd.padEnd(18))} ${color.gray(desc)}`);
  }
}

type Choice =
  | "init"
  | "check"
  | "instructions"
  | "tools"
  | "editors"
  | "help"
  | "exit";

function normalize(input: string): Choice | null {
  const cmd = input.trim().replace(/^\//, "").toLowerCase();
  switch (cmd) {
    case "1":
    case "init":
    case "setup":
      return "init";
    case "2":
    case "check":
    case "doctor":
      return "check";
    case "3":
    case "instructions":
      return "instructions";
    case "tools":
      return "tools";
    case "editors":
      return "editors";
    case "help":
    case "?":
      return "help";
    case "0":
    case "quit":
    case "exit":
    case "q":
      return "exit";
    default:
      return null;
  }
}

interface MenuItem {
  value: Choice;
  label: string;
  hint?: string;
}

const CANCEL = Symbol("cancel");

/**
 * Ask for the next action. Prefers the clack arrow-key menu; if the terminal
 * can't drive it (some Windows CMD), falls back to a typed numeric prompt that
 * always works via CONIN$.
 */
async function selectChoice(
  items: MenuItem[],
): Promise<Choice | typeof CANCEL> {
  try {
    const choice = await clack.select<Choice>({
      message: "选择操作（↑↓ 选择，回车确认）",
      options: items,
    });
    if (clack.isCancel(choice)) return CANCEL;
    return choice;
  } catch {
    return selectChoiceReadline(items);
  }
}

async function selectChoiceReadline(
  items: MenuItem[],
): Promise<Choice | typeof CANCEL> {
  const { input, output } = interactiveStreams();
  const rl = readline.createInterface({ input, output });
  try {
    console.log();
    console.log(color.dim("输入序号或命令（如 1 / init），回车确认："));
    const answer = (await rl.question(color.brightCyan("flow › "))).trim();
    if (!answer) return "help";
    return normalize(answer) ?? "help";
  } catch {
    return CANCEL;
  } finally {
    rl.close();
  }
}

async function confirmAgain(): Promise<boolean> {
  try {
    const again = await clack.confirm({
      message: "返回工作台？",
      initialValue: true,
    });
    if (clack.isCancel(again)) return false;
    return again;
  } catch {
    const { input, output } = interactiveStreams();
    const rl = readline.createInterface({ input, output });
    try {
      const answer = (await rl.question(color.dim("返回工作台？[Y/n] ")))
        .trim()
        .toLowerCase();
      return answer === "" || answer === "y" || answer === "yes";
    } catch {
      return false;
    } finally {
      rl.close();
    }
  }
}

/**
 * Interactive workbench shown when running bare `flow` in a terminal.
 * Renders the dashboard, then a menu, looping until exit.
 */
export async function runWorkbench(projectDir?: string): Promise<number> {
  const root = resolve(projectDir ?? process.cwd());

  for (;;) {
    const status = readStatus(root);
    console.log(renderDashboard(root, status));

    const recommended: Choice = status.initialized ? "check" : "init";
    const items: MenuItem[] = [
      {
        value: "init",
        label: "Setup / init — 选择编辑器并初始化",
        hint: status.initialized ? "已初始化，可重选编辑器" : "从这里开始",
      },
      { value: "check", label: "Check — 健康检查" },
      { value: "instructions", label: "Instructions — 触发话术" },
      { value: "tools", label: "Tools — 检测本机 AI CLI" },
      { value: "editors", label: "Editors — 已启用编辑器" },
      { value: "exit", label: "Exit — 退出" },
    ];
    items.sort((a, b) =>
      a.value === recommended ? -1 : b.value === recommended ? 1 : 0,
    );
    for (const item of items) {
      if (item.value === recommended) item.hint = item.hint ?? "推荐";
    }

    const choice = await selectChoice(items);

    if (choice === CANCEL || choice === "exit") {
      console.log(color.dim("Bye."));
      return 0;
    }

    switch (choice) {
      case "init":
        await actionInit(root);
        break;
      case "check":
        actionCheck(root);
        break;
      case "instructions":
        actionInstructions(root);
        break;
      case "tools":
        actionTools();
        break;
      case "editors":
        actionEditors(root);
        break;
      case "help":
        printHelp();
        break;
    }

    console.log();
    if (!(await confirmAgain())) {
      console.log(color.dim("Bye."));
      return 0;
    }
    console.log();
  }
}

export function canRunWorkbench(): boolean {
  return canRunInteractivePicker();
}

// Exposed for tests: pure render of the dashboard string.
export { normalize, readStatus, renderDashboard };
