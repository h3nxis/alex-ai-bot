from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "group_logs",
}

SKIP_FILES = {
    "check_public_safety.py",
}

SENSITIVE_NAMES = {
    ".env",
    "bot.log",
    "bot_state.json",
    "group_prompts.json",
}

PATTERNS = [
    # Telegram bot token shape.
    re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"),
    # Literal secret assignment, for example TOKEN="real-value".
    # This intentionally ignores os.getenv(...) and fake test values.
    re.compile(
        r"(?i)(api[_-]?key|token|secret|password)\s*=\s*[\"']"
        r"(?!put-your|your-|example|test|fake|123:fake)[^\"']{16,}[\"']"
    ),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{20,}"),
]


def should_skip(path: Path) -> bool:
    parts = set(path.relative_to(ROOT).parts)
    return bool(parts & SKIP_DIRS) or path.name in SKIP_FILES


def main() -> int:
    problems: list[str] = []

    for path in ROOT.rglob("*"):
        if should_skip(path):
            continue

        if path.name in SENSITIVE_NAMES:
            problems.append(f"Sensitive runtime file present: {path.relative_to(ROOT)}")
            continue

        if not path.is_file():
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for pattern in PATTERNS:
            if pattern.search(text):
                problems.append(f"Possible secret in {path.relative_to(ROOT)}")
                break

    if problems:
        print("Public safety check failed:")
        for item in problems:
            print(f"- {item}")
        return 1

    print("Public safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
