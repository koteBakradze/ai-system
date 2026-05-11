import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs) -> None:
        return None

from core.models.usage_manager import UsageManager


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "models" / "openrouter_models.json"
OPENROUTER_CHAT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_ENDPOINT = "https://openrouter.ai/api/v1/models"
OPENROUTER_KEY_ENDPOINT = "https://openrouter.ai/api/v1/key"

FREE_ROUTER_MODEL = "openrouter/free"
FREE_PRICING_FIELDS = (
    "prompt",
    "completion",
    "request",
    "image",
    "web_search",
    "internal_reasoning",
    "input_cache_read",
    "input_cache_write",
)

DEFAULT_REVIEW_PERSPECTIVES = [
    {
        "name": "correctness",
        "purpose": "review_correctness",
        "system_prompt": (
            "You are reviewing for correctness. Identify behavioral bugs, "
            "edge cases, missing tests, and unclear assumptions. Be concise."
        ),
    },
    {
        "name": "security",
        "purpose": "review_security",
        "system_prompt": (
            "You are reviewing for security and safety. Focus on secret leaks, "
            "paid API risk, unsafe retries, injection risks, and data handling. "
            "Be concise."
        ),
    },
    {
        "name": "maintainability",
        "purpose": "review_maintainability",
        "system_prompt": (
            "You are reviewing maintainability. Focus on API boundaries, "
            "configuration clarity, operability, and future debugging. Be concise."
        ),
    },
]

PURPOSE_HINTS = {
    "coding": ("code", "coder", "qwen", "deepseek", "dev"),
    "fast": ("mini", "small", "flash", "lite", "nano"),
    "reasoning": ("reason", "thinking", "r1", "large"),
    "review": ("reason", "thinking", "qwen", "llama", "mistral"),
    "review_correctness": ("reason", "thinking", "qwen", "llama", "deepseek"),
    "review_security": ("reason", "llama", "mistral", "qwen"),
    "review_maintainability": ("qwen", "llama", "mistral", "gemma"),
}


class OpenRouterClient:
    def __init__(
        self,
        config_path: Path = CONFIG_PATH,
        usage_manager: UsageManager | None = None,
    ):
        load_dotenv(PROJECT_ROOT / ".env")
        self.config_path = config_path
        self.config = self._load_config()
        self.usage_manager = usage_manager or UsageManager(config_path=config_path)
        self.last_usage_metadata: dict | None = None

    def run_model(
        self,
        prompt: str,
        model_name: str | None = None,
        system_prompt: str | None = None,
        purpose: str = "api",
    ) -> str:
        result = self.run_model_result(
            prompt=prompt,
            model_name=model_name,
            system_prompt=system_prompt,
            purpose=purpose,
        )
        return result["content"] if result["ok"] else result["error"]

    def run_model_result(
        self,
        prompt: str,
        model_name: str | None = None,
        system_prompt: str | None = None,
        purpose: str = "api",
    ) -> dict:
        self.reload_config()

        if not self.config.get("enabled", False):
            return self._error_result(
                "OpenRouter is disabled in configs/models/openrouter_models.json."
            )

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return self._error_result(
                "OpenRouter is disabled: OPENROUTER_API_KEY is not set."
            )

        model = model_name or self.resolve_model_for_purpose(purpose)
        is_valid, validation_message = self._validate_model(model)
        if not is_valid:
            return self._error_result(validation_message, model_requested=model)

        can_call, reason = self.can_call_free_model(planned_requests=1)
        if not can_call:
            return self._error_result(
                "OpenRouter call skipped: daily, minute, or remote free limit "
                f"is close or reached. Use local model instead. Reason: {reason}.",
                model_requested=model,
            )

        payload = self._build_chat_payload(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
        )
        headers = self._headers(api_key)

        try:
            response = requests.post(
                OPENROUTER_CHAT_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=int(self.config.get("request_timeout_seconds", 45)),
            )
        except requests.Timeout:
            self.usage_manager.record_openrouter_request(
                model_requested=model,
                purpose=purpose,
                success=False,
                error="timeout",
            )
            return self._error_result(
                "OpenRouter request timed out. Local models are still available.",
                model_requested=model,
            )
        except requests.RequestException as exc:
            self.usage_manager.record_openrouter_request(
                model_requested=model,
                purpose=purpose,
                success=False,
                error=str(exc),
            )
            return self._error_result(
                f"OpenRouter request failed safely: {exc}",
                model_requested=model,
            )

        if response.status_code != 200:
            error = self._format_error(response)
            self.usage_manager.record_openrouter_request(
                model_requested=model,
                purpose=purpose,
                success=False,
                error=error,
            )
            return self._error_result(error, model_requested=model)

        try:
            data = response.json()
        except json.JSONDecodeError:
            error = "OpenRouter returned a non-JSON response."
            self.usage_manager.record_openrouter_request(
                model_requested=model,
                purpose=purpose,
                success=False,
                error=error,
            )
            return self._error_result(error, model_requested=model)

        usage = data.get("usage")
        self.last_usage_metadata = usage
        model_used = data.get("model") or model

        if self._reported_cost(usage) > 0:
            error = (
                "OpenRouter safety warning: response reported non-zero cost. "
                "The request was not retried, and future calls should use local "
                "models until configuration is checked."
            )
            self.usage_manager.record_openrouter_request(
                usage=usage,
                model_requested=model,
                model_used=model_used,
                purpose=purpose,
                success=False,
                error=error,
            )
            return self._error_result(error, model_requested=model, usage=usage)

        choices = data.get("choices") or []
        if not choices:
            error = "OpenRouter returned no message choices."
            self.usage_manager.record_openrouter_request(
                usage=usage,
                model_requested=model,
                model_used=model_used,
                purpose=purpose,
                success=False,
                error=error,
            )
            return self._error_result(error, model_requested=model, usage=usage)

        message = choices[0].get("message") or {}
        content = message.get("content")

        if not content:
            error = "OpenRouter returned an empty message."
            self.usage_manager.record_openrouter_request(
                usage=usage,
                model_requested=model,
                model_used=model_used,
                purpose=purpose,
                success=False,
                error=error,
            )
            return self._error_result(error, model_requested=model, usage=usage)

        self.usage_manager.record_openrouter_request(
            usage=usage,
            model_requested=model,
            model_used=model_used,
            purpose=purpose,
            success=True,
        )

        return {
            "ok": True,
            "content": content,
            "error": None,
            "model_requested": model,
            "model_used": model_used,
            "usage": usage,
        }

    def run_multi_model_review(
        self,
        prompt: str,
        perspectives: list[dict] | None = None,
    ) -> dict:
        self.reload_config()
        review_perspectives = perspectives or self._review_perspectives_from_config()
        max_reviews = max(int(self.config.get("max_review_models", 3)), 1)
        selected = review_perspectives[:max_reviews]

        can_call, reason = self.can_call_free_model(planned_requests=len(selected))
        if not can_call:
            return {
                "ok": False,
                "content": "",
                "error": (
                    "OpenRouter multi-model review skipped: local or remote "
                    f"free budget is close or reached. Reason: {reason}."
                ),
                "reviews": [],
            }

        reviews = []
        for perspective in selected:
            name = perspective.get("name") or perspective.get("purpose") or "review"
            purpose = perspective.get("purpose") or f"review_{name}"
            result = self.run_model_result(
                prompt=prompt,
                model_name=perspective.get("model"),
                system_prompt=perspective.get("system_prompt"),
                purpose=purpose,
            )
            reviews.append(
                {
                    "name": name,
                    "purpose": purpose,
                    "ok": result["ok"],
                    "content": result.get("content") or "",
                    "error": result.get("error"),
                    "model_requested": result.get("model_requested"),
                    "model_used": result.get("model_used"),
                    "usage": result.get("usage"),
                }
            )

            if (
                not result["ok"]
                and result.get("error", "").startswith("OpenRouter call skipped")
            ):
                break

        successful = [review for review in reviews if review["ok"]]
        if not successful:
            first_error = reviews[0]["error"] if reviews else "no reviews ran"
            return {
                "ok": False,
                "content": "",
                "error": f"OpenRouter multi-model review unavailable: {first_error}",
                "reviews": reviews,
            }

        return {
            "ok": True,
            "content": self._format_multi_review(reviews),
            "error": None,
            "reviews": reviews,
        }

    def discover_free_models(self, persist: bool = True) -> dict:
        self.reload_config()

        try:
            response = requests.get(
                OPENROUTER_MODELS_ENDPOINT,
                params={"output_modalities": "text"},
                timeout=int(self.config.get("discovery_timeout_seconds", 30)),
            )
        except requests.Timeout:
            return {
                "ok": False,
                "error": "OpenRouter model discovery timed out.",
                "models": [],
            }
        except requests.RequestException as exc:
            return {
                "ok": False,
                "error": f"OpenRouter model discovery failed safely: {exc}",
                "models": [],
            }

        if response.status_code != 200:
            return {
                "ok": False,
                "error": self._format_error(response),
                "models": [],
            }

        try:
            data = response.json()
        except json.JSONDecodeError:
            return {
                "ok": False,
                "error": "OpenRouter model discovery returned non-JSON data.",
                "models": [],
            }

        free_models = self._extract_free_models(data.get("data") or [])

        if persist:
            self.config["discovered_at"] = datetime.now(timezone.utc).isoformat()
            self.config["discovered_free_models"] = free_models
            self._save_config()

        return {
            "ok": True,
            "error": None,
            "count": len(free_models),
            "models": free_models,
        }

    def get_remote_key_status(self, force: bool = False) -> dict:
        self.reload_config()

        if not self.config.get("check_remote_key_usage", True):
            return {"available": False, "error": "remote key usage check disabled"}

        cache_seconds = int(self.config.get("remote_key_cache_seconds", 300))
        if not force:
            cached = self.usage_manager.get_cached_remote_key_status(cache_seconds)
            if cached:
                return cached

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return {"available": False, "error": "OPENROUTER_API_KEY is not set"}

        status = {
            "available": False,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "status_code": None,
            "data": None,
            "error": None,
        }

        try:
            response = requests.get(
                OPENROUTER_KEY_ENDPOINT,
                headers=self._headers(api_key),
                timeout=int(self.config.get("remote_key_timeout_seconds", 15)),
            )
        except requests.Timeout:
            status["error"] = "remote key usage check timed out"
            self.usage_manager.record_remote_key_status(status)
            return status
        except requests.RequestException as exc:
            status["error"] = f"remote key usage check failed safely: {exc}"
            self.usage_manager.record_remote_key_status(status)
            return status

        if response.status_code != 200:
            status["status_code"] = response.status_code
            status["error"] = self._format_error(response)
            self.usage_manager.record_remote_key_status(status)
            return status

        try:
            data = response.json().get("data") or {}
        except json.JSONDecodeError:
            status["error"] = "remote key usage check returned non-JSON data"
            self.usage_manager.record_remote_key_status(status)
            return status

        status["available"] = True
        status["status_code"] = response.status_code
        status["data"] = self._sanitize_key_data(data)
        self.usage_manager.record_remote_key_status(status)
        return status

    def can_call_free_model(
        self,
        planned_requests: int = 1,
    ) -> tuple[bool, str]:
        self.reload_config()

        if not self.config.get("enabled", False):
            return False, "OpenRouter is disabled in config"

        if not os.getenv("OPENROUTER_API_KEY"):
            return False, "OPENROUTER_API_KEY is not set"

        remote_status = None
        if self.config.get("check_remote_key_usage", True):
            remote_status = self.get_remote_key_status()

        return self.usage_manager.can_call_openrouter(
            planned_requests=planned_requests,
            remote_key_status=remote_status,
        )

    def resolve_model_for_purpose(self, purpose: str = "api") -> str:
        purpose = (purpose or "api").strip().lower()
        purpose_models = self.config.get("purpose_models") or {}
        candidates = list(purpose_models.get(purpose) or [])

        if not candidates and purpose.startswith("review_"):
            candidates = list(purpose_models.get("review") or [])

        candidates.extend(self.config.get("fallback_models") or [])
        candidates.append(self.config.get("default", FREE_ROUTER_MODEL))
        candidates.append(FREE_ROUTER_MODEL)

        for candidate in self._dedupe(candidates):
            resolved = self._resolve_candidate(candidate, purpose)
            if not resolved:
                continue
            is_valid, _ = self._validate_model(resolved)
            if is_valid:
                return resolved

        return FREE_ROUTER_MODEL

    def reload_config(self) -> None:
        self.config = self._load_config()

    def _build_chat_payload(
        self,
        model: str,
        prompt: str,
        system_prompt: str | None,
    ) -> dict:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                    or "You are a concise, helpful assistant.",
                },
                {"role": "user", "content": prompt},
            ],
        }

        max_tokens = self.config.get("max_completion_tokens")
        if max_tokens:
            payload["max_completion_tokens"] = int(max_tokens)

        temperature = self.config.get("temperature")
        if temperature is not None:
            payload["temperature"] = float(temperature)

        return payload

    def _validate_model(self, model_name: str) -> tuple[bool, str]:
        if not model_name:
            return False, "OpenRouter model blocked: missing model name."

        if model_name != FREE_ROUTER_MODEL and not model_name.endswith(":free"):
            return (
                False,
                (
                    "OpenRouter model blocked: only openrouter/free or model IDs "
                    "ending in ':free' are allowed."
                ),
            )

        metadata = self._discovered_model_by_id().get(model_name)
        if metadata and not self._model_metadata_is_free(metadata):
            return (
                False,
                (
                    "OpenRouter model blocked: discovered pricing metadata is not "
                    "zero-cost."
                ),
            )

        require_discovered = bool(
            self.config.get("require_discovered_free_models", False)
        )
        if (
            require_discovered
            and model_name != FREE_ROUTER_MODEL
            and model_name not in self._discovered_model_by_id()
        ):
            return (
                False,
                (
                    "OpenRouter model blocked: specific free model was not found "
                    "in the discovery cache."
                ),
            )

        return True, "free model allowed"

    def _extract_free_models(self, models: list[dict]) -> list[dict]:
        free_models = []
        for model in models:
            if not self._model_metadata_is_free(model):
                continue
            if not self._model_supports_text_chat(model):
                continue
            if self._is_expired_model(model):
                continue
            free_models.append(self._summarize_model(model))

        return sorted(free_models, key=lambda item: item["id"])

    def _model_metadata_is_free(self, model: dict) -> bool:
        pricing = model.get("pricing") or {}
        return all(
            self._is_zero_price(pricing.get(field))
            for field in FREE_PRICING_FIELDS
        )

    def _model_supports_text_chat(self, model: dict) -> bool:
        architecture = model.get("architecture") or {}
        input_modalities = architecture.get("input_modalities") or []
        output_modalities = architecture.get("output_modalities") or []

        has_text_input = not input_modalities or "text" in input_modalities
        has_text_output = not output_modalities or "text" in output_modalities
        return has_text_input and has_text_output

    def _is_expired_model(self, model: dict) -> bool:
        expiration_date = model.get("expiration_date")
        if not expiration_date:
            return False

        try:
            expires = datetime.fromisoformat(
                expiration_date.replace("Z", "+00:00")
            )
        except ValueError:
            return False

        return expires <= datetime.now(timezone.utc)

    def _is_zero_price(self, value: Any) -> bool:
        if value is None:
            return False
        try:
            return float(value) == 0.0
        except (TypeError, ValueError):
            return False

    def _summarize_model(self, model: dict) -> dict:
        top_provider = model.get("top_provider") or {}
        return {
            "id": model.get("id"),
            "name": model.get("name"),
            "context_length": model.get("context_length"),
            "pricing": model.get("pricing") or {},
            "supported_parameters": model.get("supported_parameters") or [],
            "top_provider": {
                "context_length": top_provider.get("context_length"),
                "max_completion_tokens": top_provider.get("max_completion_tokens"),
                "is_moderated": top_provider.get("is_moderated"),
            },
            "created": model.get("created"),
            "expiration_date": model.get("expiration_date"),
        }

    def _discovered_model_by_id(self) -> dict[str, dict]:
        models = self.config.get("discovered_free_models") or []
        return {
            model["id"]: model
            for model in models
            if isinstance(model, dict) and model.get("id")
        }

    def _resolve_candidate(self, candidate: str, purpose: str) -> str | None:
        if not candidate:
            return None

        if not candidate.startswith("auto:"):
            return candidate

        hint_name = candidate.split(":", 1)[1] or purpose
        return self._select_discovered_model_for_purpose(hint_name)

    def _select_discovered_model_for_purpose(self, purpose: str) -> str | None:
        models = self.config.get("discovered_free_models") or []
        hints = PURPOSE_HINTS.get(purpose) or PURPOSE_HINTS.get("review", ())
        scored = []

        for model in models:
            model_id = str(model.get("id") or "").lower()
            name = str(model.get("name") or "").lower()
            haystack = f"{model_id} {name}"
            score = sum(1 for hint in hints if hint in haystack)
            if score <= 0:
                continue
            scored.append((score, int(model.get("context_length") or 0), model["id"]))

        if not scored:
            return None

        scored.sort(reverse=True)
        return scored[0][2]

    def _format_multi_review(self, reviews: list[dict]) -> str:
        sections = ["=== OPENROUTER MULTI-MODEL REVIEW ==="]

        for review in reviews:
            sections.append("")
            sections.append(f"## {review['name'].upper()}")
            sections.append(
                f"Model requested: {review.get('model_requested') or 'n/a'}"
            )
            sections.append(f"Model used: {review.get('model_used') or 'n/a'}")

            if review["ok"]:
                sections.append("")
                sections.append(review["content"])
            else:
                sections.append("")
                sections.append(f"Skipped or failed: {review.get('error')}")

        return "\n".join(sections)

    def _headers(self, api_key: str) -> dict:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "local-ai-system"),
        }

    def _sanitize_key_data(self, data: dict) -> dict:
        return {
            "label": data.get("label"),
            "limit": data.get("limit"),
            "limit_reset": data.get("limit_reset"),
            "limit_remaining": data.get("limit_remaining"),
            "include_byok_in_limit": data.get("include_byok_in_limit"),
            "usage": data.get("usage"),
            "usage_daily": data.get("usage_daily"),
            "usage_weekly": data.get("usage_weekly"),
            "usage_monthly": data.get("usage_monthly"),
            "byok_usage": data.get("byok_usage"),
            "byok_usage_daily": data.get("byok_usage_daily"),
            "byok_usage_weekly": data.get("byok_usage_weekly"),
            "byok_usage_monthly": data.get("byok_usage_monthly"),
            "is_free_tier": data.get("is_free_tier"),
        }

    def _reported_cost(self, usage: dict | None) -> float:
        if not usage:
            return 0.0

        try:
            return float(usage.get("cost") or usage.get("total_cost") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _format_error(self, response: requests.Response) -> str:
        details = self._response_error_details(response)
        status_messages = {
            401: "OpenRouter authentication failed. Check OPENROUTER_API_KEY.",
            402: (
                "OpenRouter rejected the request for billing or credits. "
                "Paid models are not allowed here."
            ),
            408: "OpenRouter request timed out. Local models are still available.",
            413: "OpenRouter request was too large for the selected free model.",
            429: "OpenRouter rate limit reached. Use a local model and try later.",
            500: "OpenRouter server error. Use a local model and try later.",
            502: "OpenRouter server error. Use a local model and try later.",
            503: "OpenRouter server error. Use a local model and try later.",
        }
        message = status_messages.get(
            response.status_code,
            f"OpenRouter request failed with HTTP {response.status_code}.",
        )

        if details:
            return f"{message} Details: {details}"

        return message

    def _response_error_details(self, response: requests.Response) -> str:
        try:
            data = response.json()
        except json.JSONDecodeError:
            return response.text[:300]

        error = data.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)
        if error:
            return str(error)

        return ""

    def _error_result(
        self,
        error: str,
        model_requested: str | None = None,
        usage: dict | None = None,
    ) -> dict:
        return {
            "ok": False,
            "content": "",
            "error": error,
            "model_requested": model_requested,
            "model_used": None,
            "usage": usage,
        }

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            return {
                "enabled": False,
                "default": FREE_ROUTER_MODEL,
                "fallback_models": [FREE_ROUTER_MODEL],
                "daily_request_limit": 50,
                "minute_request_limit": 20,
            }

        with open(self.config_path, "r", encoding="utf-8") as f:
            return self._normalize_config(json.load(f))

    def _normalize_config(self, config: dict) -> dict:
        default_model = config.get("default") or config.get(
            "default_model", FREE_ROUTER_MODEL
        )
        config.setdefault("default", default_model)
        config.setdefault("default_model", default_model)
        config.setdefault("fallback_models", [default_model, FREE_ROUTER_MODEL])
        config.setdefault("discovered_free_models", [])
        config.setdefault("discovered_at", None)

        limits = config.get("limits") or {}
        if "max_review_models" not in config and limits.get(
            "max_parallel_review_models"
        ):
            config["max_review_models"] = int(limits["max_parallel_review_models"])

        if "purpose_models" not in config:
            config["purpose_models"] = self._purpose_models_from_seed_config(config)

        if "review_perspectives" not in config:
            config["review_perspectives"] = self._review_perspectives_from_profiles(
                config
            )

        return config

    def _purpose_models_from_seed_config(self, config: dict) -> dict:
        seeds = config.get("seed_models") or {}
        default_model = config.get("default", FREE_ROUTER_MODEL)

        return {
            "api": self._dedupe([seeds.get("general"), default_model]),
            "review": self._dedupe([seeds.get("balanced_review"), default_model]),
            "review_correctness": self._dedupe(
                [seeds.get("balanced_review"), "auto:review_correctness", default_model]
            ),
            "review_security": self._dedupe(
                [seeds.get("code_review"), "auto:review_security", default_model]
            ),
            "review_maintainability": self._dedupe(
                [seeds.get("reasoning_alt"), "auto:review_maintainability", default_model]
            ),
            "reasoning": self._dedupe(
                [seeds.get("reasoning"), "auto:reasoning", default_model]
            ),
            "fast": self._dedupe(["auto:fast", default_model]),
            "coding": self._dedupe([seeds.get("code_review"), "auto:coding", default_model]),
        }

    def _review_perspectives_from_config(self) -> list[dict]:
        perspectives = self.config.get("review_perspectives")
        if perspectives:
            return perspectives
        return DEFAULT_REVIEW_PERSPECTIVES

    def _review_perspectives_from_profiles(self, config: dict) -> list[dict]:
        profiles = config.get("multi_review_profiles") or {}
        perspectives = []

        for name, profile in profiles.items():
            perspectives.append(
                {
                    "name": name,
                    "purpose": f"review_{name}",
                    "model": profile.get("model"),
                    "system_prompt": profile.get("system_prompt"),
                }
            )

        return perspectives or DEFAULT_REVIEW_PERSPECTIVES

    def _save_config(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)
            f.write("\n")

    def _dedupe(self, values: list[str | None]) -> list[str]:
        seen = set()
        deduped = []
        for value in values:
            if not value:
                continue
            if value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        return deduped
