import unittest

from agentflow import __version__


class PackagingTests(unittest.TestCase):
    def _pyproject(self) -> dict:
        import tomllib
        from pathlib import Path

        return tomllib.loads(
            (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
        )

    def test_version_matches_pyproject(self) -> None:
        # 防止 __init__.py 与 pyproject.toml 版本漂移。
        self.assertEqual(__version__, self._pyproject()["project"]["version"])

    def test_pyproject_exposes_flow_command(self) -> None:
        scripts = self._pyproject()["project"]["scripts"]
        self.assertEqual(scripts["flow"], "agentflow.cli:main")
        self.assertEqual(scripts["agentflow"], "agentflow.cli:main")


if __name__ == "__main__":
    unittest.main()
