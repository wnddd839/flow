"""Tests for specification document templates."""

import unittest

from agentflow import templates


class TemplateTests(unittest.TestCase):
    def test_agents_md_has_maintenance_contract(self) -> None:
        content = templates.agents_md()
        self.assertIn("文档维护契约", content)
        self.assertIn("每条信息只出现在一个文档里", content)

    def test_agents_md_has_completion_gate(self) -> None:
        content = templates.agents_md()
        self.assertIn("大改动", content)
        self.assertIn("完成定义", content)
        self.assertIn("未完成同步前", content)

    def test_agent_instructions_mention_completion(self) -> None:
        instructions = templates.AGENT_INSTRUCTIONS
        self.assertIn("完成定义", instructions)
        self.assertIn("未同步", instructions)

    def test_skeletons_have_boundary_markers(self) -> None:
        for factory in (
            templates.project_skeleton,
            templates.conventions_skeleton,
            templates.business_skeleton,
            templates.pitfalls_skeleton,
        ):
            content = factory()
            self.assertIn("只写：", content)
            self.assertIn("不写：", content)
            self.assertIn("判断标准", content)

    def test_project_skeleton_has_fixed_sections(self) -> None:
        content = templates.project_skeleton()
        for heading in ("一句话定位", "技术栈", "架构概览", "启动与运行"):
            self.assertIn(f"## {heading}", content)

    def test_skeletons_have_no_prefilled_project_content(self) -> None:
        """正文除 HTML 注释外不应出现像已填好的项目描述。"""
        forbidden = ("agentflow-mvp",)
        for factory in (
            templates.project_skeleton,
            templates.conventions_skeleton,
            templates.business_skeleton,
            templates.pitfalls_skeleton,
        ):
            content = factory()
            for phrase in forbidden:
                self.assertNotIn(phrase, content)

    def test_skills_readme_has_routing_table(self) -> None:
        content = templates.skills_readme()
        self.assertIn("任务关键词", content)
        self.assertIn("必须先读对应 skill", content)

    def test_root_agents_pointer_points_to_agentflow(self) -> None:
        content = templates.root_agents_pointer()
        self.assertIn(".agentflow/AGENTS.md", content)
        self.assertIn(templates.AGENTFLOW_GENERATED_MARKER, content)

    def test_thin_entrypoint_is_one_line_pointer(self) -> None:
        content = templates.thin_entrypoint("cursor")
        self.assertIn(".agentflow/AGENTS.md", content)
        self.assertNotIn("constitution", content)


if __name__ == "__main__":
    unittest.main()
