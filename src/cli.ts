import { existsSync } from "node:fs";
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
import { pickEditors } from "./init-ui.js";
import { AGENT_INSTRUCTIONS } from "./templates.js";
import { VERSION } from "./version.js";

const program = new Command();

program
  .name("flow")
  .description(
    "Initialize strict project specification docs for AI coding tools.",
  )
  .version(VERSION, "-V, --version", "Show version");

program
  .command("init")
  .description("Create .agentflow specification skeleton.")
  .argument("[editors...]", "Editors to enable, e.g. flow init cursor claude")
  .option("--force", "Overwrite existing files.")
  .option(
    "--editors <names>",
    "Comma-separated editors (same as positional names).",
  )
  .option(
    "--skeleton-only",
    "Only create .agentflow/; do not generate any thin entrypoints.",
  )
  .action(async (positional: string[], options) => {
    const cwd = resolve(process.cwd());
    let editorList: string[];

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
        editorList = await pickEditors();
      }
    } catch (err) {
      console.error(err instanceof Error ? err.message : String(err));
      process.exitCode = 1;
      return;
    }

    const result = initProject(cwd, { editors: editorList, force: options.force });
    console.log(`Initialized specification skeleton in ${cwd}`);
    if (editorList.length) {
      console.log(`Editors: ${editorList.join(", ")}`);
    } else {
      console.log("Editors: (none — .agentflow/ skeleton only)");
    }
    console.log(`Created: ${result.created.length}`);
    console.log(`Skipped: ${result.skipped.length}`);
    if (result.editorsRemoved.length) {
      console.log(
        `Removed disabled editor entrypoints: ${result.editorsRemoved.join(", ")}`,
      );
    }
  });

function runCheck(label: "check" | "doctor"): void {
  const cwd = resolve(process.cwd());
  const report = doctorProject(cwd);
  if (report.ok) {
    console.log(`AgentFlow ${label}: OK`);
  } else {
    console.log(`AgentFlow ${label}: missing files`);
    for (const relative of report.missing) {
      console.log(`- ${relative}`);
    }
    process.exitCode = 1;
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
  .description("Show agent instructions summary.")
  .action(() => {
    const cwd = resolve(process.cwd());
    if (!existsSync(join(cwd, ".agentflow", "AGENTS.md"))) {
      console.log("Project not initialized. Run `flow init` first.");
      process.exitCode = 1;
      return;
    }
    console.log(AGENT_INSTRUCTIONS);
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
      console.log(`- [${tool.status}] ${tool.display} (${tool.command}): ${location}`);
    }
  });

const editors = program
  .command("editors")
  .description("Manage editor entrypoints.");

editors
  .command("list")
  .description("Show editors and their enabled state.")
  .action(() => {
    const catalog = allEditors();
    const enabled = new Set(getEnabledEditors().map((s) => s.name));
    for (const name of Object.keys(catalog).sort()) {
      const spec = catalog[name];
      const mark = enabled.has(name) ? "[x]" : "[ ]";
      const tag = spec.custom ? " (custom)" : "";
      console.log(`${mark} ${name.padEnd(14)}${tag} -> ${spec.entrypoint}`);
    }
  });

editors
  .command("add <name>")
  .description("Enable a known editor.")
  .action((name: string) => {
    const spec = enableEditor(name);
    applyEditors(process.cwd());
    console.log(`Enabled editor: ${spec.name} -> ${spec.entrypoint}`);
  });

editors
  .command("remove <name>")
  .description("Disable an editor.")
  .action((name: string) => {
    disableEditor(name);
    const result = applyEditors(process.cwd());
    console.log(`Disabled editor: ${name}`);
    if (result.removed.length) {
      console.log(`Removed entrypoints: ${result.removed.join(", ")}`);
    }
  });

editors
  .command("add-custom <name> <path>")
  .description("Register a custom editor entrypoint path.")
  .option("--display <label>", "Display name")
  .action((name: string, entryPath: string, options) => {
    try {
      const spec = addCustomEditor(name, entryPath, options.display);
      applyEditors(process.cwd());
      console.log(`Added custom editor: ${spec.name} -> ${spec.entrypoint}`);
    } catch (err) {
      console.error(err instanceof Error ? err.message : String(err));
      process.exitCode = 1;
    }
  });

editors
  .command("remove-custom <name>")
  .description("Remove a custom editor.")
  .action((name: string) => {
    removeCustomEditor(name);
    const result = applyEditors(process.cwd());
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
    const result = applyEditors(process.cwd(), undefined, options.force);
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
