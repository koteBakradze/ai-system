import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
