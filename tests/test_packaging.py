import unittest

from agentflow import __version__


class PackagingTests(unittest.TestCase):
    def test_version_is_0_4(self) -> None:
        self.assertEqual(__version__, "0.4.0")

    def test_pyproject_exposes_flow_command(self) -> None:
        import tomllib
        from pathlib import Path

        data = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
        scripts = data["project"]["scripts"]
        self.assertEqual(scripts["flow"], "agentflow.cli:main")
        self.assertEqual(scripts["agentflow"], "agentflow.cli:main")


if __name__ == "__main__":
    unittest.main()
