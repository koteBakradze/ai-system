from __future__ import annotations

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ALLOWED_READ_SUFFIXES = {".md", ".py", ".json"}
BLOCKED_DIRS = {
    ".git",
    ".ssh",
    ".aws",
    ".config",
    ".gnupg",
    "__pycache__",
    "venv",
    "node_modules",
}
BLOCKED_FILENAMES = {
    ".env",
    ".env.local",
    ".envrc",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "known_hosts",
}
SENSITIVE_KEY_RE = re.compile(
    r"(?i)(^|[_-])"
    r"(api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|token|"
    r"secret|password|passwd|authorization|bearer|private[_-]?key)"
    r"($|[_-])"
)
SECRET_VALUE_REPLACEMENTS = (
    (
        re.compile(
            r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*['\"]?[^'\"\s,}]+"
        ),
        r"\1=<redacted>",
    ),
    (re.compile(r"(?i)bearer\s+[a-z0-9._\-]+"), "Bearer <redacted>"),
    (
        re.compile(
            r"(?i)(sk-[a-z0-9_-]{12,}|or-[a-z0-9_-]{12,}|[a-z0-9]{32,})"
        ),
        "<redacted>",
    ),
)


class SafeFileError(ValueError):
    pass


def project_root() -> Path:
    return PROJECT_ROOT


def list_project_files(max_depth: int = 4, max_files: int = 300) -> list[str]:
    root = PROJECT_ROOT.resolve()
    files: list[str] = []

    for path in sorted(root.rglob("*")):
        if len(files) >= max_files:
            break
        if not path.is_file():
            continue
        if _is_blocked_path(path):
            continue

        relative = path.relative_to(root)
        if len(relative.parts) > max_depth:
            continue
        files.append(relative.as_posix())

    return files


def read_project_file(relative_path: str, max_bytes: int = 80_000) -> str:
    path = _safe_project_path(relative_path)

    if path.suffix.lower() not in ALLOWED_READ_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_READ_SUFFIXES))
        raise SafeFileError(f"File type blocked. Allowed extensions: {allowed}.")

    if path.stat().st_size > max_bytes:
        raise SafeFileError(f"File is too large to read safely ({max_bytes} byte limit).")

    if path.suffix.lower() == ".json":
        return _read_redacted_json(path)

    return redact_secrets(path.read_text(encoding="utf-8", errors="replace"))


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern, replacement in SECRET_VALUE_REPLACEMENTS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def _safe_project_path(relative_path: str) -> Path:
    if not relative_path or Path(relative_path).is_absolute():
        raise SafeFileError("Only relative project paths are allowed.")

    root = PROJECT_ROOT.resolve()
    path = (root / relative_path).resolve()

    if not _is_relative_to(path, root):
        raise SafeFileError("Path escapes the project root.")
    if not path.exists() or not path.is_file():
        raise SafeFileError("File does not exist.")
    if _is_blocked_path(path):
        raise SafeFileError("Path is blocked by the local safety policy.")

    return path


def _is_blocked_path(path: Path) -> bool:
    root = PROJECT_ROOT.resolve()
    parts = set(path.relative_to(root).parts) if _is_relative_to(path, root) else set(path.parts)
    filename = path.name.lower()

    if parts & BLOCKED_DIRS:
        return True
    if filename in BLOCKED_FILENAMES:
        return True
    if filename.endswith(".pem") or filename.endswith(".key"):
        return True

    return False


def _read_redacted_json(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return redact_secrets(path.read_text(encoding="utf-8", errors="replace"))

    return json.dumps(_redact_json_value(data), indent=2, sort_keys=True)


def _redact_json_value(value):
    if isinstance(value, dict):
        redacted = {}
        for key, child in value.items():
            if SENSITIVE_KEY_RE.search(str(key)):
                redacted[key] = "<redacted>"
            else:
                redacted[key] = _redact_json_value(child)
        return redacted
    if isinstance(value, list):
        return [_redact_json_value(item) for item in value]
    if isinstance(value, str):
        return redact_secrets(value)
    return value


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
