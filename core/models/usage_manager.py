import json
import time
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "models" / "openrouter_models.json"
USAGE_PATH = PROJECT_ROOT / "configs" / "usage" / "openrouter_usage.json"

DEFAULT_USAGE = {
    "date": "",
    "requests_today": 0,
    "request_timestamps": [],
    "successful_requests_today": 0,
    "failed_requests_today": 0,
    "total_prompt_tokens": 0,
    "total_completion_tokens": 0,
    "total_tokens": 0,
    "estimated_cost": 0.0,
    "last_response_usage": None,
    "last_request": None,
    "model_counts": {},
    "purpose_counts": {},
    "remote_key_status": None,
}


class UsageManager:
    def __init__(self, config_path: Path = CONFIG_PATH, usage_path: Path = USAGE_PATH):
        self.config_path = config_path
        self.usage_path = usage_path
        self.config = self._load_config()
        self.usage = self._load_usage()
        self._refresh_daily_usage()

    def can_call_openrouter(
        self,
        planned_requests: int = 1,
        remote_key_status: dict | None = None,
    ) -> tuple[bool, str]:
        self.config = self._load_config()
        self._refresh_daily_usage()
        self._prune_old_timestamps()

        planned_requests = max(int(planned_requests or 1), 1)
        budget = self._request_budget_config(remote_key_status)
        daily_limit = budget["daily_limit"]
        minute_limit = budget["minute_limit"]
        daily_buffer = budget["daily_buffer"]
        minute_buffer = budget["minute_buffer"]
        daily_usable = max(daily_limit - daily_buffer, 0)
        minute_usable = max(minute_limit - minute_buffer, 0)

        if self.usage["requests_today"] + planned_requests > daily_usable:
            self._save_usage()
            return False, "daily free request limit is close or reached"

        if len(self.usage["request_timestamps"]) + planned_requests > minute_usable:
            self._save_usage()
            return False, "per-minute free request limit is close or reached"

        remote_allowed, remote_reason = self._remote_key_allows_call(
            remote_key_status
        )
        if not remote_allowed:
            self._save_usage()
            return False, remote_reason

        self._save_usage()
        return True, "OpenRouter free request is allowed"

    def record_openrouter_request(
        self,
        usage: dict | None = None,
        model_requested: str | None = None,
        model_used: str | None = None,
        purpose: str | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        self._refresh_daily_usage()
        self._prune_old_timestamps()

        self.usage["requests_today"] += 1
        self.usage["request_timestamps"].append(time.time())
        self.usage["last_response_usage"] = usage
        self.usage["last_request"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model_requested": model_requested,
            "model_used": model_used,
            "purpose": purpose,
            "success": success,
            "error": error,
        }

        if success:
            self.usage["successful_requests_today"] = (
                int(self.usage.get("successful_requests_today") or 0) + 1
            )
        else:
            self.usage["failed_requests_today"] = (
                int(self.usage.get("failed_requests_today") or 0) + 1
            )

        if model_used or model_requested:
            model_key = model_used or model_requested
            model_counts = self.usage.setdefault("model_counts", {})
            model_counts[model_key] = int(model_counts.get(model_key) or 0) + 1

        if purpose:
            purpose_counts = self.usage.setdefault("purpose_counts", {})
            purpose_counts[purpose] = int(purpose_counts.get(purpose) or 0) + 1

        if usage:
            self.usage["total_prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
            self.usage["total_completion_tokens"] += int(
                usage.get("completion_tokens") or 0
            )
            self.usage["total_tokens"] += int(usage.get("total_tokens") or 0)
            self.usage["estimated_cost"] += float(
                usage.get("cost") or usage.get("total_cost") or 0.0
            )

        self._save_usage()

    def record_remote_key_status(self, status: dict) -> None:
        self.usage["remote_key_status"] = status
        self._save_usage()

    def get_cached_remote_key_status(self, max_age_seconds: int) -> dict | None:
        status = self.usage.get("remote_key_status")
        if not status:
            return None

        checked_at = status.get("checked_at")
        if not checked_at:
            return None

        try:
            checked = datetime.fromisoformat(checked_at)
        except ValueError:
            return None

        age = datetime.now(timezone.utc) - checked
        if age.total_seconds() > max_age_seconds:
            return None

        return status

    def get_openrouter_status(self) -> dict:
        self.config = self._load_config()
        self._refresh_daily_usage()
        self._prune_old_timestamps()

        remote_key_status = self.usage.get("remote_key_status")
        budget = self._request_budget_config(remote_key_status)
        daily_limit = budget["daily_limit"]
        minute_limit = budget["minute_limit"]
        allowed, reason = self.can_call_openrouter(
            remote_key_status=remote_key_status
        )

        return {
            "enabled": bool(self.config.get("enabled", False)),
            "date_utc": self.usage["date"],
            "requests_today": self.usage["requests_today"],
            "successful_requests_today": self.usage.get(
                "successful_requests_today", 0
            ),
            "failed_requests_today": self.usage.get("failed_requests_today", 0),
            "daily_request_limit": daily_limit,
            "daily_request_safety_buffer": budget["daily_buffer"],
            "daily_requests_remaining": max(
                daily_limit - self.usage["requests_today"], 0
            ),
            "requests_last_minute": len(self.usage["request_timestamps"]),
            "minute_request_limit": minute_limit,
            "minute_request_safety_buffer": budget["minute_buffer"],
            "minute_requests_remaining": max(
                minute_limit - len(self.usage["request_timestamps"]), 0
            ),
            "total_prompt_tokens": self.usage["total_prompt_tokens"],
            "total_completion_tokens": self.usage["total_completion_tokens"],
            "total_tokens": self.usage["total_tokens"],
            "estimated_cost": self.usage["estimated_cost"],
            "last_response_usage": self.usage["last_response_usage"],
            "last_request": self.usage.get("last_request"),
            "model_counts": self.usage.get("model_counts", {}),
            "purpose_counts": self.usage.get("purpose_counts", {}),
            "cached_remote_key_status": self.usage.get("remote_key_status"),
            "can_call": allowed,
            "reason": reason,
        }

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            return {
                "enabled": False,
                "daily_request_limit": 50,
                "minute_request_limit": 20,
                "daily_request_safety_buffer": 0,
                "minute_request_safety_buffer": 0,
            }

        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _request_budget_config(self, remote_key_status: dict | None = None) -> dict:
        limits = self.config.get("limits") or {}
        if "daily_request_limit" in self.config:
            daily_limit = int(self.config["daily_request_limit"])
        else:
            daily_limit = int(limits.get("free_tier_daily_request_limit", 50))
            remote_data = (remote_key_status or {}).get("data") or {}
            if remote_data.get("is_free_tier") is False:
                daily_limit = int(
                    limits.get(
                        "paid_account_free_model_daily_request_limit",
                        daily_limit,
                    )
                )
        minute_limit = int(
            self.config.get(
                "minute_request_limit",
                limits.get("minute_request_limit", 20),
            )
        )
        daily_buffer = max(
            int(
                self.config.get(
                    "daily_request_safety_buffer",
                    limits.get("reserve_requests", 0),
                )
            ),
            0,
        )
        minute_buffer = max(
            int(
                self.config.get(
                    "minute_request_safety_buffer",
                    limits.get("minute_request_safety_buffer", 0),
                )
            ),
            0,
        )

        return {
            "daily_limit": daily_limit,
            "minute_limit": minute_limit,
            "daily_buffer": daily_buffer,
            "minute_buffer": minute_buffer,
        }

    def _load_usage(self) -> dict:
        self.usage_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.usage_path.exists():
            self.usage_path.write_text(
                json.dumps(DEFAULT_USAGE, indent=2), encoding="utf-8"
            )

        with open(self.usage_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        usage = DEFAULT_USAGE.copy()
        usage.update(loaded)
        return usage

    def _refresh_daily_usage(self) -> None:
        today = datetime.now(timezone.utc).date().isoformat()

        if self.usage.get("date") != today:
            lifetime_prompt_tokens = int(self.usage.get("total_prompt_tokens") or 0)
            lifetime_completion_tokens = int(
                self.usage.get("total_completion_tokens") or 0
            )
            lifetime_total_tokens = int(self.usage.get("total_tokens") or 0)
            lifetime_cost = float(self.usage.get("estimated_cost") or 0.0)
            last_response_usage = self.usage.get("last_response_usage")
            model_counts = self.usage.get("model_counts", {})
            remote_key_status = self.usage.get("remote_key_status")

            self.usage = DEFAULT_USAGE.copy()
            self.usage["date"] = today
            self.usage["total_prompt_tokens"] = lifetime_prompt_tokens
            self.usage["total_completion_tokens"] = lifetime_completion_tokens
            self.usage["total_tokens"] = lifetime_total_tokens
            self.usage["estimated_cost"] = lifetime_cost
            self.usage["last_response_usage"] = last_response_usage
            self.usage["model_counts"] = model_counts
            self.usage["remote_key_status"] = remote_key_status
            self._save_usage()

    def _prune_old_timestamps(self) -> None:
        cutoff = time.time() - 60
        self.usage["request_timestamps"] = [
            timestamp
            for timestamp in self.usage.get("request_timestamps", [])
            if float(timestamp) >= cutoff
        ]

    def _save_usage(self) -> None:
        self.usage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.usage_path, "w", encoding="utf-8") as f:
            json.dump(self.usage, f, indent=2)
            f.write("\n")

    def _remote_key_allows_call(
        self, remote_key_status: dict | None
    ) -> tuple[bool, str]:
        if not remote_key_status:
            return True, "remote key status unavailable; local limits apply"

        if not remote_key_status.get("available", False):
            status_code = remote_key_status.get("status_code")
            if status_code in {401, 402}:
                return False, "remote key authentication or credit check failed"
            if self.config.get("block_on_remote_usage_error", False):
                return False, "remote key usage check failed"
            return True, "remote key status unavailable; local limits apply"

        data = remote_key_status.get("data") or {}
        limit_remaining = data.get("limit_remaining")
        minimum_remaining = float(
            self.config.get("minimum_remote_credits_remaining", 0)
        )

        if limit_remaining is not None:
            try:
                remaining = float(limit_remaining)
            except (TypeError, ValueError):
                remaining = None

            if remaining is not None and remaining <= minimum_remaining:
                return False, "remote key credit limit is close or reached"

        return True, "remote key status allows call"
