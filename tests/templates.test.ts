import { describe, expect, it } from "vitest";
import {
  AGENTFLOW_GENERATED_MARKER,
  AGENT_INSTRUCTIONS,
  agentsMd,
  conventionsSkeleton,
  businessSkeleton,
  pitfallsSkeleton,
  projectSkeleton,
  rootAgentsPointer,
  skillsReadme,
  thinEntrypoint,
} from "../src/templates.js";

describe("templates", () => {
  it("agents_md has maintenance contract and completion gate", () => {
    const content = agentsMd();
    expect(content).toContain("文档维护契约");
    expect(content).toContain("每条信息只出现在一个文档里");
    expect(content).toContain("大改动");
    expect(content).toContain("完成定义");
    expect(content).toContain("未完成同步前");
  });

  it("agent instructions mention completion", () => {
    expect(AGENT_INSTRUCTIONS).toContain("完成定义");
    expect(AGENT_INSTRUCTIONS).toContain("未同步");
  });

  it("skeletons have boundary markers", () => {
    for (const factory of [
      projectSkeleton,
      conventionsSkeleton,
      businessSkeleton,
      pitfallsSkeleton,
    ]) {
      const content = factory();
      expect(content).toContain("只写：");
      expect(content).toContain("不写：");
      expect(content).toContain("判断标准");
    }
  });

  it("project skeleton has fixed sections", () => {
    const content = projectSkeleton();
    for (const heading of ["一句话定位", "技术栈", "架构概览", "启动与运行"]) {
      expect(content).toContain(`## ${heading}`);
    }
  });

  it("skeletons have no prefilled project content", () => {
    const forbidden = ["agentflow-mvp"];
    for (const factory of [
      projectSkeleton,
      conventionsSkeleton,
      businessSkeleton,
      pitfallsSkeleton,
    ]) {
      const content = factory();
      for (const phrase of forbidden) {
        expect(content).not.toContain(phrase);
      }
    }
  });

  it("skills readme has routing table", () => {
    const content = skillsReadme();
    expect(content).toContain("任务关键词");
    expect(content).toContain("必须先读对应 skill");
  });

  it("root agents pointer points to agentflow", () => {
    const content = rootAgentsPointer();
    expect(content).toContain(".agentflow/AGENTS.md");
    expect(content).toContain(AGENTFLOW_GENERATED_MARKER);
  });

  it("thin entrypoint is a one-line pointer", () => {
    const content = thinEntrypoint("cursor");
    expect(content).toContain(".agentflow/AGENTS.md");
    expect(content).not.toContain("constitution");
  });
});
