import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import main as cli


class ResponseReportTests(unittest.TestCase):
    def test_save_response_report_writes_markdown_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_dir = root / "workspace" / "reports" / "responses"

            with (
                patch.object(cli, "PROJECT_ROOT", root),
                patch.object(cli, "RESPONSE_REPORT_DIR", report_dir),
            ):
                path = cli.save_response_report(
                    task_type="system_review",
                    prompt="focus on safety",
                    response="## Finding\n\nLong response body",
                )

            self.assertEqual(path.parent, report_dir)
            self.assertTrue(path.name.endswith("-system-review.md"))

            content = path.read_text(encoding="utf-8")
            self.assertIn("# AI Response: system_review", content)
            self.assertIn("- Task type: `system_review`", content)
            self.assertIn("## Prompt\n\nfocus on safety", content)
            self.assertIn("## Response\n\n## Finding", content)

    def test_save_response_report_handles_empty_prompt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_dir = root / "workspace" / "reports" / "responses"

            with (
                patch.object(cli, "PROJECT_ROOT", root),
                patch.object(cli, "RESPONSE_REPORT_DIR", report_dir),
            ):
                path = cli.save_response_report("general", "", "Hello")

            content = path.read_text(encoding="utf-8")
            self.assertIn("No prompt provided.", content)

    def test_one_shot_research_command_uses_topic(self):
        with patch.object(cli, "run_research") as run_research:
            status = cli.run_one_shot(["research", "fresh", "local", "AI"])

        self.assertEqual(status, 0)
        run_research.assert_called_once_with("fresh local AI", provider_name="mock")

    def test_one_shot_research_command_accepts_provider_option(self):
        with patch.object(cli, "run_research") as run_research:
            status = cli.run_one_shot(
                ["research", "fresh", "local", "AI", "--provider", "ddgs"]
            )

        self.assertEqual(status, 0)
        run_research.assert_called_once_with("fresh local AI", provider_name="ddgs")

    def test_one_shot_research_real_uses_ddgs(self):
        with patch.object(cli, "run_research") as run_research:
            status = cli.run_one_shot(["research", "fresh", "local", "AI", "--real"])

        self.assertEqual(status, 0)
        run_research.assert_called_once_with("fresh local AI", provider_name="ddgs")

    def test_one_shot_research_real_rejects_mock_provider(self):
        with patch.object(cli, "run_research") as run_research, redirect_stdout(io.StringIO()):
            status = cli.run_one_shot(
                ["research", "fresh", "local", "AI", "--provider", "mock", "--real"]
            )

        self.assertEqual(status, 2)
        run_research.assert_not_called()

    def test_one_shot_research_command_requires_topic(self):
        with patch.object(cli, "run_research") as run_research, redirect_stdout(io.StringIO()):
            status = cli.run_one_shot(["research"])

        self.assertEqual(status, 2)
        run_research.assert_not_called()

    def test_one_shot_research_context_command_uses_report_path(self):
        with patch.object(cli, "run_research_context") as run_research_context:
            status = cli.run_one_shot(
                ["research-context", "workspace/research/fake", "report.md"]
            )

        self.assertEqual(status, 0)
        run_research_context.assert_called_once_with("workspace/research/fake report.md")

    def test_one_shot_research_context_command_requires_path(self):
        with (
            patch.object(cli, "run_research_context") as run_research_context,
            redirect_stdout(io.StringIO()),
        ):
            status = cli.run_one_shot(["research-context"])

        self.assertEqual(status, 2)
        run_research_context.assert_not_called()

    def test_one_shot_project_context_export_runs_exporter(self):
        with patch.object(cli, "run_project_context_export", return_value=0) as run_export:
            status = cli.run_one_shot(["project_context_export"])

        self.assertEqual(status, 0)
        run_export.assert_called_once_with()

    def test_one_shot_project_context_export_rejects_extra_args(self):
        with (
            patch.object(cli, "run_project_context_export") as run_export,
            redirect_stdout(io.StringIO()),
        ):
            status = cli.run_one_shot(["project_context_export", "--max-depth", "2"])

        self.assertEqual(status, 2)
        run_export.assert_not_called()


if __name__ == "__main__":
    unittest.main()
