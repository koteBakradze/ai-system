import json
import tempfile
import unittest
from pathlib import Path

from scripts import export_project_context


class ProjectContextExportTests(unittest.TestCase):
    def test_manual_context_template_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "docs" / "context" / "CHATGPT_PROJECT_CONTEXT.md"
            path.parent.mkdir(parents=True)
            path.write_text("human edits stay here", encoding="utf-8")

            created = export_project_context.ensure_manual_context(path)

            self.assertFalse(created)
            self.assertEqual(path.read_text(encoding="utf-8"), "human edits stay here")

    def test_list_project_files_skips_secret_and_cache_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "main.py").write_text("print('ok')", encoding="utf-8")
            (root / ".env").write_text("OPENROUTER_API_KEY=secret", encoding="utf-8")
            (root / "venv").mkdir()
            (root / "venv" / "config.py").write_text("secret = True", encoding="utf-8")

            files = export_project_context.list_project_files(
                root,
                max_depth=3,
                max_files=20,
            )

            self.assertEqual(files, ["main.py"])

    def test_build_project_summary_redacts_secret_json_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "configs" / "models").mkdir(parents=True)
            (root / "configs" / "usage").mkdir(parents=True)
            (root / "configs" / "models" / "local_models.json").write_text(
                json.dumps({"orchestrator": "llama"}),
                encoding="utf-8",
            )
            (root / "configs" / "models" / "openrouter_models.json").write_text(
                json.dumps(
                    {
                        "enabled": True,
                        "strict_free_only": True,
                        "OPENROUTER_API_KEY": "or-secret-value",
                    }
                ),
                encoding="utf-8",
            )
            (root / "configs" / "usage" / "openrouter_usage.json").write_text(
                json.dumps({"requests_today": 0, "estimated_cost": 0.0}),
                encoding="utf-8",
            )

            summary = export_project_context.build_project_summary(
                root,
                manual_path=root / "docs" / "context" / "CHATGPT_PROJECT_CONTEXT.md",
                output_path=root
                / "docs"
                / "context"
                / "AI_SYSTEM_PROJECT_SUMMARY.generated.md",
            )

            self.assertIn("# AI_SYSTEM Generated Project Context", summary)
            self.assertIn('"enabled": true', summary)
            self.assertIn("Real research gateway", summary)
            self.assertIn("project_context_export", summary)
            self.assertNotIn("or-secret-value", summary)


if __name__ == "__main__":
    unittest.main()
