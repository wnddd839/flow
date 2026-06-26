import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { Command } from "commander";
import { doctorProject } from "./core/check.js";
import { initProject } from "./core/init.js";
import { detectTools } from "./diagnostics/tools.js";
import {
  addCustomEditor,
  allEditors,
  applyEditors,
  disableEditor,
  enableEditor,
  getEnabledEditors,
  normalizeEditorNames,
  removeCustomEditor,
} from "./editors/index.js";
import { printInitResult, printNextSteps } from "./guidance.js";
import {
  interactivePickerHint,
  PickCancelledError,
  pickEditors,
} from "./init-ui.js";
import {
  AGENT_INSTRUCTIONS,
  BUILTIN_EDITOR_IDS,
  kickoffPrompt,
} from "./templates.js";
import { VERSION } from "./version.js";
import { canRunWorkbench, runWorkbench } from "./workbench.js";

const program = new Command();

program
  .name("flow")
  .description(
    "Initialize strict project specification docs for AI coding tools.",
  )
  .version(VERSION, "-V, --version", "Show version")
  .action(async () => {
    if (canRunWorkbench()) {
      await runWorkbench();
      return;
    }
    program.outputHelp();
    console.log();
    console.log(
      "在交互终端（Windows Terminal / Cursor 终端）里直接运行 `flow` 可进入工作台。",
    );
    console.log(
      "或：`flow init <编辑器>`、`flow check`、`flow instructions`。",
    );
  });

program
  .command("init")
  .description("Create .agentflow specification skeleton.")
  .argument(
    "[editors...]",
    `Editors to enable (${BUILTIN_EDITOR_IDS}). Examples: flow init claude | flow init cursor codex`,
  )
  .option("--force", "Overwrite existing files.")
  .option(
    "--editors <names>",
    "Comma-separated editors (same as positional names).",
  )
  .option(
    "--skeleton-only",
    "Only create .agentflow/; do not generate any thin entrypoints.",
  )
  .option(
    "-i, --interactive",
    "Force interactive editor picker (requires a TTY terminal).",
  )
  .action(async (positional: string[], options) => {
    const cwd = resolve(process.cwd());
    let editorList: string[] | null = null;

    try {
      if (options.skeletonOnly) {
        editorList = [];
      } else if (positional.length > 0) {
        editorList = normalizeEditorNames(positional);
      } else if (options.editors !== undefined) {
        editorList = normalizeEditorNames(
          String(options.editors)
            .split(",")
            .map((s: string) => s.trim())
            .filter(Boolean),
        );
      } else {
        editorList = await pickEditors({
          forceInteractive: Boolean(options.interactive),
        });
        if (editorList === null) {
          console.error(
            "无法启动交互式选择器（当前不是交互终端，或 stdin/stdout 未连接 TTY）。",
          );
          console.error(`  诊断: ${interactivePickerHint()}`);
          console.error();
          console.error("请任选一种方式：");
          console.error("  flow init cursor          # 直接指定编辑器");
          console.error("  flow init cursor claude   # 多个编辑器");
          console.error("  flow init --skeleton-only # 仅骨架");
          console.error();
          console.error(
            "提示：在 Windows Terminal / Cursor 终端里直接运行 `flow init` 可 ↑↓ 选择。",
          );
          process.exitCode = 1;
          return;
        }
      }
    } catch (err) {
      if (err instanceof PickCancelledError) {
        return;
      }
      console.error(err instanceof Error ? err.message : String(err));
      process.exitCode = 1;
      return;
    }

    const result = initProject(cwd, {
      editors: editorList,
      force: options.force,
    });
    printInitResult(cwd, editorList, result);
    printNextSteps(editorList);
  });

function runCheck(label: "check" | "doctor"): void {
  const cwd = resolve(process.cwd());
  const report = doctorProject(cwd);
  if (report.ok) {
    console.log(`AgentFlow ${label}: OK`);
  } else {
    if (report.missing.length) {
      console.log(`AgentFlow ${label}: missing files`);
      for (const relative of report.missing) {
        console.log(`- ${relative}`);
      }
    }
    if (report.drift.length) {
      console.log(
        `AgentFlow ${label}: drifted entrypoints (no longer point to .agentflow/AGENTS.md)`,
      );
      for (const relative of report.drift) {
        console.log(`- ${relative}  (fix: flow editors apply --force)`);
      }
    }
    process.exitCode = 1;
  }
  if (report.unfilled.length) {
    console.log(
      `AgentFlow ${label}: skeleton not yet filled by an AI — sections still empty:`,
    );
    for (const entry of report.unfilled) {
      console.log(`- ${entry}`);
    }
    console.log(
      "  让接手的 AI 读 .agentflow/AGENTS.md，按边界声明分析代码后填写，或运行 `flow instructions` 查看触发话术。",
    );
  }
  printDiagnostics(cwd);
}

function printDiagnostics(cwd: string): void {
  console.log();
  console.log("Local diagnostics:");
  const report = doctorProject(cwd);
  if (report.ok) {
    console.log("- [ok] AgentFlow spec skeleton: all required files exist");
  } else {
    for (const missing of report.missing) {
      console.log(
        `- [missing] AgentFlow ${missing}: run \`flow init\` or \`flow check\``,
      );
    }
    for (const drift of report.drift) {
      console.log(
        `- [drift] AgentFlow ${drift}: run \`flow editors apply --force\``,
      );
    }
  }
  for (const entry of report.unfilled) {
    console.log(`- [unfilled] AgentFlow ${entry}`);
  }
  for (const tool of detectTools()) {
    const message = tool.path || "not found on PATH";
    console.log(`- [${tool.status}] ${tool.display}: ${message}`);
  }
}

program
  .command("check")
  .description("Check specification skeleton files.")
  .action(() => runCheck("check"));

program
  .command("doctor")
  .description("Alias for check.")
  .action(() => runCheck("doctor"));

program
  .command("instructions")
  .description("Show agent work summary (full prompts: flow prompts).")
  .action(() => {
    const cwd = resolve(process.cwd());
    if (!existsSync(join(cwd, ".agentflow", "AGENTS.md"))) {
      console.log("Project not initialized. Run `flow init` first.");
      process.exitCode = 1;
      return;
    }
    const promptsPath = join(cwd, ".agentflow", "prompts.md");
    if (existsSync(promptsPath)) {
      console.log(
        "常用可复制话术见 .agentflow/prompts.md — 运行 `flow prompts` 查看全文。\n",
      );
    }
    console.log(AGENT_INSTRUCTIONS);
    const enabled = getEnabledEditors({ projectDir: cwd });
    const prompts = enabled
      .map((spec) => {
        const text = kickoffPrompt(spec.name);
        return text ? { display: spec.display, text } : null;
      })
      .filter((p) => p !== null);
    if (prompts.length) {
      console.log();
      console.log("（可选）各工具简短版首次接手话术：");
      for (const { display, text } of prompts) {
        console.log();
        console.log(`— ${display} —`);
        console.log(text);
      }
    }
  });

program
  .command("prompts")
  .description("Print copy-paste prompts from .agentflow/prompts.md.")
  .action(() => {
    const cwd = resolve(process.cwd());
    const promptsPath = join(cwd, ".agentflow", "prompts.md");
    if (!existsSync(promptsPath)) {
      console.log("Project not initialized. Run `flow init` first.");
      process.exitCode = 1;
      return;
    }
    console.log(readFileSync(promptsPath, "utf8"));
  });

program
  .command("tools")
  .description("Show local AI coding tool availability.")
  .option("--json", "Output JSON")
  .action((options) => {
    const tools = detectTools();
    if (options.json) {
      console.log(JSON.stringify({ tools }, null, 2));
      return;
    }
    console.log("Local AI coding tools:");
    for (const tool of tools) {
      const location = tool.path || "not found on PATH";
      console.log(
        `- [${tool.status}] ${tool.display} (${tool.command}): ${location}`,
      );
    }
  });

const editors = program
  .command("editors")
  .description("Manage editor entrypoints.");

editors
  .command("list")
  .description("Show editors and their enabled state.")
  .action(() => {
    const cwd = resolve(process.cwd());
    const catalog = allEditors({ projectDir: cwd });
    const enabled = new Set(
      getEnabledEditors({ projectDir: cwd }).map((s) => s.name),
    );
    for (const name of Object.keys(catalog).sort()) {
      const spec = catalog[name];
      const mark = enabled.has(name) ? "[x]" : "[ ]";
      const tag = spec.custom ? " (custom)" : "";
      console.log(`${mark} ${name.padEnd(14)}${tag} -> ${spec.entrypoint}`);
    }
  });

editors
  .command("add <name>")
  .description("Enable a known editor for this project.")
  .action((name: string) => {
    const cwd = resolve(process.cwd());
    const spec = enableEditor(name, { projectDir: cwd });
    applyEditors(cwd, { projectDir: cwd });
    console.log(`Enabled editor: ${spec.name} -> ${spec.entrypoint}`);
  });

editors
  .command("remove <name>")
  .description("Disable an editor for this project.")
  .action((name: string) => {
    const cwd = resolve(process.cwd());
    disableEditor(name, { projectDir: cwd });
    const result = applyEditors(cwd, { projectDir: cwd });
    console.log(`Disabled editor: ${name}`);
    if (result.removed.length) {
      console.log(`Removed entrypoints: ${result.removed.join(", ")}`);
    }
  });

editors
  .command("add-custom <name> <path>")
  .description("Register a custom editor entrypoint path for this project.")
  .option("--display <label>", "Display name")
  .action((name: string, entryPath: string, options) => {
    const cwd = resolve(process.cwd());
    try {
      const spec = addCustomEditor(name, entryPath, options.display, {
        projectDir: cwd,
      });
      applyEditors(cwd, { projectDir: cwd });
      console.log(`Added custom editor: ${spec.name} -> ${spec.entrypoint}`);
    } catch (err) {
      console.error(err instanceof Error ? err.message : String(err));
      process.exitCode = 1;
    }
  });

editors
  .command("remove-custom <name>")
  .description("Remove a custom editor from this project.")
  .action((name: string) => {
    const cwd = resolve(process.cwd());
    removeCustomEditor(name, { projectDir: cwd });
    const result = applyEditors(cwd, { projectDir: cwd });
    console.log(`Removed custom editor: ${name}`);
    if (result.removed.length) {
      console.log(`Removed entrypoints: ${result.removed.join(", ")}`);
    }
  });

editors
  .command("apply")
  .description("Reconcile editor entrypoints with the config.")
  .option("--force", "Overwrite existing entrypoints")
  .action((options) => {
    const cwd = resolve(process.cwd());
    const result = applyEditors(cwd, { projectDir: cwd }, options.force);
    console.log(`Created:  ${result.created.length}`);
    console.log(`Kept:     ${result.kept.length}`);
    console.log(`Removed:  ${result.removed.length}`);
  });

async function main(): Promise<void> {
  await program.parseAsync(process.argv);
}

main().catch((err: unknown) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(1);
});
