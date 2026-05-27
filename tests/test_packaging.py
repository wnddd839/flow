import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_pyproject_exposes_flow_and_agentflow_commands(self) -> None:
        data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        scripts = data["project"]["scripts"]
        dependencies = data["project"]["dependencies"]
        optional_dependencies = data["project"]["optional-dependencies"]

        self.assertEqual(scripts["agentflow"], "agentflow.cli:main")
        self.assertEqual(scripts["flow"], "agentflow.cli:main")
        self.assertIn("prompt_toolkit>=3.0.0", dependencies)
        self.assertIn("pytest>=8.0.0", optional_dependencies["dev"])


if __name__ == "__main__":
    unittest.main()
