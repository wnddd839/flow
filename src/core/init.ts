import { join, resolve } from "node:path";
import {
  applyEditors,
  type ConfigTarget,
  loadEditorConfig,
  normalizeEditorNames,
  saveEditorConfig,
} from "../editors/index.js";
import { SKELETON_FILES } from "../templates.js";
import { writeText } from "./write.js";

export interface InitResult {
  created: string[];
  skipped: string[];
  editorsRemoved: string[];
}

export function initProject(
  projectDir: string,
  options: {
    editors?: string[] | null;
    force?: boolean;
    home?: string;
  } = {},
): InitResult {
  const { editors = null, force = false, home } = options;
  const root = resolve(projectDir);
  const created: string[] = [];
  const skipped: string[] = [];

  const editorNames = editors === null ? [] : normalizeEditorNames(editors);

  // Persist editor choices to the PROJECT-level config so enabling editors in
  // project A never silently changes what project B sees.
  const target: ConfigTarget = { projectDir: root, home };
  const config = loadEditorConfig(target);
  saveEditorConfig(editorNames, config.custom, target);

  for (const [relative, factory] of Object.entries(SKELETON_FILES)) {
    const status = writeText(join(root, relative), factory(), force);
    if (status === "created") {
      created.push(relative);
    } else {
      skipped.push(relative);
    }
  }

  const editorResult = applyEditors(root, target, force);
  created.push(...editorResult.created);
  skipped.push(...editorResult.kept);

  return {
    created,
    skipped,
    editorsRemoved: editorResult.removed,
  };
}
