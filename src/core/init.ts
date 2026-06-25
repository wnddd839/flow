import { join, resolve } from "node:path";
import {
  applyEditors,
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

  const editorNames =
    editors === null
      ? []
      : normalizeEditorNames(editors);

  const config = loadEditorConfig(home);
  saveEditorConfig(editorNames, config.custom, home);

  for (const [relative, factory] of Object.entries(SKELETON_FILES)) {
    const status = writeText(join(root, relative), factory(), force);
    if (status === "created") {
      created.push(relative);
    } else {
      skipped.push(relative);
    }
  }

  const editorResult = applyEditors(root, home, force);
  created.push(...editorResult.created);
  skipped.push(...editorResult.kept);

  return {
    created,
    skipped,
    editorsRemoved: editorResult.removed,
  };
}
