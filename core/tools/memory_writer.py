from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from core.tools.file_tools import PROJECT_ROOT, redact_secrets


ALLOWED_WRITE_ROOTS = (
    PROJECT_ROOT / "memory" / "context",
    PROJECT_ROOT / "memory" / "observations",
    PROJECT_ROOT / "workspace" / "reports" / "environment",
)


class MemoryWriteError(ValueError):
    pass


def save_markdown(relative_path: str, content: str, append: bool = False) -> Path:
    path = _safe_markdown_path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    safe_content = redact_secrets(content).rstrip() + "\n"
    if append and path.exists():
        existing = path.read_text(encoding="utf-8", errors="replace")
        path.write_text(existing.rstrip() + "\n\n" + safe_content, encoding="utf-8")
    else:
        path.write_text(safe_content, encoding="utf-8")

    return path


def save_observation(title: str, body: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = _slugify(title)
    content = (
        f"# {title}\n\n"
        f"- Captured: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"{body.strip()}\n"
    )
    return save_markdown(f"memory/observations/{timestamp}-{slug}.md", content)


def save_context_memory(filename: str, title: str, body: str) -> Path:
    name = Path(filename).name
    if not name.endswith(".md"):
        raise MemoryWriteError("Context memory files must be markdown.")

    content = f"# {title}\n\n{body.strip()}\n"
    return save_markdown(f"memory/context/{name}", content)


def save_environment_report(title: str, body: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = _slugify(title)
    content = f"# {title}\n\n{body.strip()}\n"
    return save_markdown(f"workspace/reports/environment/{timestamp}-{slug}.md", content)


def _safe_markdown_path(relative_path: str) -> Path:
    if not relative_path or Path(relative_path).is_absolute():
        raise MemoryWriteError("Only relative markdown paths are allowed.")

    path = (PROJECT_ROOT / relative_path).resolve()
    if path.suffix.lower() != ".md":
        raise MemoryWriteError("Only markdown memory files can be written.")
    if not any(_is_relative_to(path, root) for root in ALLOWED_WRITE_ROOTS):
        raise MemoryWriteError(
            "Writes are restricted to memory/context, memory/observations, "
            "and workspace/reports/environment."
        )

    return path


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:80] or "observation"


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
