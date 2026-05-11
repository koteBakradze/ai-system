import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.tools import file_tools, memory_writer
from core.tools.safe_shell import SafeShellError, run_safe_command
from core.tools.tool_registry import ToolRegistry


class SafeToolTests(unittest.TestCase):
    def test_read_project_file_blocks_env(self):
        with self.assertRaises(file_tools.SafeFileError):
            file_tools.read_project_file(".env")

    def test_read_project_file_blocks_path_escape(self):
        with self.assertRaises(file_tools.SafeFileError):
            file_tools.read_project_file("../outside.md")

    def test_json_read_redacts_sensitive_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "safe.json"
            target.write_text(
                json.dumps(
                    {
                        "OPENROUTER_API_KEY": "or-secret-value",
                        "nested": {"token": "abc123"},
                        "safe": "visible",
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(file_tools, "PROJECT_ROOT", root):
                result = file_tools.read_project_file("safe.json")

        self.assertIn('"safe": "visible"', result)
        self.assertIn("<redacted>", result)
        self.assertNotIn("or-secret-value", result)
        self.assertNotIn("abc123", result)

    def test_safe_shell_rejects_unlisted_command(self):
        with self.assertRaises(SafeShellError):
            run_safe_command("rm")

    def test_tool_registry_can_run_named_system_check(self):
        registry = ToolRegistry()
        result = registry.call_tool("run_system_check", name="platform_summary")

        self.assertTrue(result["ok"])
        self.assertEqual(result["command"], "platform_summary")

    def test_memory_writer_restricts_writes_to_markdown_memory(self):
        with self.assertRaises(memory_writer.MemoryWriteError):
            memory_writer.save_markdown("core/unsafe.md", "blocked")

        with self.assertRaises(memory_writer.MemoryWriteError):
            memory_writer.save_markdown("memory/context/unsafe.txt", "blocked")


if __name__ == "__main__":
    unittest.main()
