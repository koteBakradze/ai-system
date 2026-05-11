import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from core.models.openrouter_client import OpenRouterClient
from core.models.usage_manager import UsageManager


class OpenRouterSafetyTests(unittest.TestCase):
    def make_client(self, config: dict, usage: dict | None = None) -> OpenRouterClient:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        root = Path(temp_dir.name)
        config_path = root / "openrouter_models.json"
        usage_path = root / "openrouter_usage.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        if usage is not None:
            usage_path.write_text(json.dumps(usage), encoding="utf-8")

        usage_manager = UsageManager(
            config_path=config_path,
            usage_path=usage_path,
        )
        return OpenRouterClient(
            config_path=config_path,
            usage_manager=usage_manager,
        )

    def test_paid_model_is_blocked_even_if_config_is_loose(self):
        client = self.make_client(
            {
                "enabled": True,
                "strict_free_only": False,
                "default": "openrouter/free",
            }
        )

        allowed, reason = client._validate_model("openai/gpt-4")

        self.assertFalse(allowed)
        self.assertIn("only openrouter/free", reason)

    def test_discovery_keeps_only_zero_cost_text_models(self):
        client = self.make_client({"enabled": True, "default": "openrouter/free"})
        models = [
            {
                "id": "free/model:free",
                "name": "Free Model",
                "pricing": {field: "0" for field in client_module_pricing_fields()},
                "architecture": {
                    "input_modalities": ["text"],
                    "output_modalities": ["text"],
                },
            },
            {
                "id": "paid/model",
                "name": "Paid Model",
                "pricing": {
                    **{field: "0" for field in client_module_pricing_fields()},
                    "prompt": "0.000001",
                },
                "architecture": {
                    "input_modalities": ["text"],
                    "output_modalities": ["text"],
                },
            },
        ]

        discovered = client._extract_free_models(models)

        self.assertEqual([model["id"] for model in discovered], ["free/model:free"])

    def test_budget_safety_buffer_blocks_close_daily_limit(self):
        client = self.make_client(
            {
                "enabled": True,
                "daily_request_limit": 3,
                "daily_request_safety_buffer": 1,
                "minute_request_limit": 20,
            },
            usage={
                "date": datetime.now(timezone.utc).date().isoformat(),
                "requests_today": 2,
                "request_timestamps": [],
            },
        )

        allowed, reason = client.usage_manager.can_call_openrouter()

        self.assertFalse(allowed)
        self.assertIn("daily free request limit", reason)

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False)
    @patch("core.models.openrouter_client.requests.post")
    def test_invalid_model_does_not_make_post_request(self, mock_post):
        client = self.make_client(
            {
                "enabled": True,
                "default": "openrouter/free",
                "check_remote_key_usage": False,
            }
        )

        result = client.run_model_result(
            "hello",
            model_name="anthropic/claude-sonnet-4.5",
        )

        self.assertFalse(result["ok"])
        self.assertIn("model blocked", result["error"])
        mock_post.assert_not_called()

    def test_remote_key_zero_remaining_blocks_call(self):
        client = self.make_client(
            {
                "enabled": True,
                "daily_request_limit": 50,
                "minute_request_limit": 20,
                "minimum_remote_credits_remaining": 0,
            }
        )

        allowed, reason = client.usage_manager.can_call_openrouter(
            remote_key_status={
                "available": True,
                "data": {"limit_remaining": 0},
            }
        )

        self.assertFalse(allowed)
        self.assertIn("remote key credit limit", reason)

    def test_remote_key_auth_failure_blocks_call(self):
        client = self.make_client(
            {
                "enabled": True,
                "daily_request_limit": 50,
                "minute_request_limit": 20,
                "block_on_remote_usage_error": False,
            }
        )

        allowed, reason = client.usage_manager.can_call_openrouter(
            remote_key_status={
                "available": False,
                "status_code": 401,
                "error": "auth failed",
            }
        )

        self.assertFalse(allowed)
        self.assertIn("authentication", reason)


def client_module_pricing_fields() -> tuple[str, ...]:
    from core.models.openrouter_client import FREE_PRICING_FIELDS

    return FREE_PRICING_FIELDS


if __name__ == "__main__":
    unittest.main()
