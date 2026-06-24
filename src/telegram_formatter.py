r"""telegram_formatter.py

Converts standard Markdown (as produced by AI models) to Telegram MarkdownV2.

Telegram MarkdownV2 special chars that must be escaped in plain text:
_ * [ ] ( ) ~ ` > # + - = | { } . ! \ (backslash too)

Key rules:
- Only escape plain text regions, NOT code blocks or inline code.
- Inside code blocks, only backslash and backtick need special handling.
- Headings -> bold (Telegram has no heading support).
- Tables -> code block (Telegram has no table rendering).
- Math formulas -> inline code / code block / unicode symbols.
"""

from __future__ import annotations

import re
from typing import List

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TELEGRAM_ESCAPE_CHARS = "_*[]()~`>#+-=|{}.!\\"

TELEGRAM_MESSAGE_LIMIT = 4096

# Simple LaTeX → unicode mapping for common symbols
LATEX_SYMBOL_MAP: dict[str, str] = {
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
    r"\epsilon": "ε", r"\zeta": "ζ", r"\eta": "η", r"\theta": "θ",
    r"\lambda": "λ", r"\mu": "μ", r"\pi": "π", r"\sigma": "σ",
    r"\phi": "φ", r"\omega": "ω", r"\sum": "Σ", r"\prod": "Π",
    r"\int": "∫", r"\infty": "∞", r"\neq": "≠", r"\leq": "≤",
    r"\geq": "≥", r"\pm": "±", r"\times": "×", r"\div": "÷",
    r"\cdot": "·", r"\approx": "≈", r"\rightarrow": "→",
    r"\leftarrow": "←", r"\Rightarrow": "⇒", r"\Leftarrow": "⇐",
    r"\forall": "∀", r"\exists": "∃", r"\neg": "¬", r"\land": "∧",
    r"\lor": "∨",
}

_SUPERSCRIPT = str.maketrans("0123456789+-=()niab", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱᵃᵇ")


# ---------------------------------------------------------------------------
# escape helpers
# ---------------------------------------------------------------------------

def escape_markdown_v2(text: str) -> str:
    """Escape all Telegram MarkdownV2 special characters in *text*.

    Applied ONLY to plain text regions, NOT inside code blocks or inline code.
    """
    out: list[str] = []
    for ch in text:
        if ch in TELEGRAM_ESCAPE_CHARS:
            out.append("\\")
        out.append(ch)
    return "".join(out)


def _escape_inline_code(text: str) -> str:
    """Escape text inside an inline code span."""
    text = text.replace("\\", "\\\\")
    text = text.replace("`", "\\`")
    return text


def _escape_code_block(text: str) -> str:
    """Escape text inside a fenced code block."""
    text = text.replace("\\", "\\\\")
    text = text.replace("```", "`\\`\\`\\`")
    return text


def _escape_link_url(url: str) -> str:
    """Escape characters inside a MarkdownV2 link URL."""
    url = url.replace("\\", "\\\\")
    url = url.replace(")", "\\)")
    return url


def _escape_link_label(label: str) -> str:
    """Escape the display label of a MarkdownV2 link."""
    return escape_markdown_v2(label)


# ---------------------------------------------------------------------------
# Table handling
# ---------------------------------------------------------------------------

def _is_table_line(line: str) -> bool:
    """Return True if *line* looks like a Markdown table row.

    A table row has pipe-separated cells: | cell | cell |
    Spoiler syntax ||text|| starts with || and is excluded.
    """
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return False
    # Spoiler: ||text|| starts with two consecutive pipes
    # Table: | cell | starts with pipe + non-pipe
    if stripped.startswith("||"):
        return False
    return True


def _is_table_separator(line: str) -> bool:
    stripped = line.strip()
    inner = stripped.strip("|").strip()
    return bool(re.match(r"^[-:]+(\s*\|\s*[-:]+)*$", inner))


def _parse_table(lines: list[str]) -> list[list[str]] | None:
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip()
        if not _is_table_line(stripped):
            return None
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        rows.append(cells)
    return rows if len(rows) >= 2 else None


def _is_table_separator_row(row: list[str]) -> bool:
    for cell in row:
        if not re.match(r"^[-:]+$", cell.strip()):
            return False
    return True


def _display_width(text: str) -> int:
    width = 0
    for ch in text:
        cp = ord(ch)
        if (0x1100 <= cp <= 0x115F or 0x2E80 <= cp <= 0x303E or
                0x3040 <= cp <= 0x9FFF or 0xAC00 <= cp <= 0xD7AF or
                0xF900 <= cp <= 0xFAFF or 0xFE30 <= cp <= 0xFE4F or
                0x20000 <= cp <= 0x2FA1F):
            width += 2
        else:
            width += 1
    return width


def _table_to_code_block(lines: list[str]) -> str:
    rows = _parse_table(lines)
    if rows is None:
        return _fallback_table_to_list(lines)

    data_rows = [r for i, r in enumerate(rows) if not (i > 0 and _is_table_separator_row(r))]
    if not data_rows:
        return _fallback_table_to_list(lines)

    num_cols = max(len(r) for r in data_rows)
    col_widths = [0] * num_cols
    for row in data_rows:
        for i, cell in enumerate(row):
            if i < num_cols:
                col_widths[i] = max(col_widths[i], _display_width(cell))

    formatted_rows: list[str] = []
    for row in data_rows:
        cells: list[str] = []
        for i in range(num_cols):
            cell = row[i] if i < len(row) else ""
            dw = _display_width(cell)
            padding = col_widths[i] - dw
            cells.append(cell + " " * max(padding, 0))
        formatted_rows.append("  ".join(cells))

    table_text = "\n".join(formatted_rows)
    return f"```text\n{_escape_code_block(table_text)}\n```"


def _fallback_table_to_list(lines: list[str]) -> str:
    parts: list[str] = []
    for line in lines:
        stripped = line.strip().strip("|")
        if _is_table_separator(line.strip()):
            continue
        cells = [c.strip() for c in stripped.split("|")]
        if len(cells) >= 2:
            label = escape_markdown_v2(cells[0])
            value = escape_markdown_v2(cells[1])
            parts.append(f"*{label}:* {value}")
        elif cells:
            parts.append(escape_markdown_v2(cells[0]))
    return "\n".join(parts) if parts else escape_markdown_v2("\n".join(lines))


# ---------------------------------------------------------------------------
# Math / LaTeX handling
# ---------------------------------------------------------------------------

def _simple_latex_to_unicode(latex: str) -> str:
    text = latex.strip()
    text = re.sub(r"\\sqrt\{([^}]+)\}", lambda m: f"√{_clean_braces(m.group(1))}", text)
    text = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}", r"(\1)/(\2)", text)
    for cmd, symbol in sorted(LATEX_SYMBOL_MAP.items(), key=lambda x: -len(x[0])):
        text = text.replace(cmd, symbol)
    text = re.sub(r"\^{([^}]+)}", lambda m: m.group(1).translate(_SUPERSCRIPT), text)
    text = re.sub(r"\^(\w)", lambda m: m.group(1).translate(_SUPERSCRIPT), text)
    subscript_map = "₀₁₂₃₄₅₆₇₈₉"
    text = re.sub(r"_{([^}]+)}", lambda m: "".join(
        subscript_map[int(c)] if c.isdigit() else c for c in m.group(1)
    ), text)
    text = re.sub(r"_(\d)", lambda m: subscript_map[int(m.group(1))], text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = text.replace("{", "").replace("}", "")
    return text


def _clean_braces(text: str) -> str:
    return text.replace("{", "").replace("}", "")


def _convert_inline_math(latex: str) -> str:
    converted = _simple_latex_to_unicode(latex)
    if not any(cmd in converted for cmd in ["\\", "{", "}"]):
        return escape_markdown_v2(converted)
    return f"`{_escape_inline_code(latex)}`"


def _convert_block_math(latex: str) -> str:
    converted = _simple_latex_to_unicode(latex)
    return f"```text\n{_escape_code_block(converted)}\n```"


def _process_math(text: str) -> str:
    text = re.sub(r"\$\$(.+?)\$\$", lambda m: _convert_block_math(m.group(1)), text, flags=re.DOTALL)
    text = re.sub(r"\$([^$\n]+?)\$", lambda m: _convert_inline_math(m.group(1)), text)
    return text


# ---------------------------------------------------------------------------
# Segment-based formatting (correct approach)
# ---------------------------------------------------------------------------

# Pattern order matters: code blocks first, then inline code, then others
_SEGMENT_PATTERNS = [
    ("code_block", re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)),
    ("inline_code", re.compile(r"`([^`]+?)`")),
    ("heading", re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)),
    ("bold", re.compile(r"\*\*(.+?)\*\*")),
    ("bold_u", re.compile(r"__(.+?)__")),
    ("italic", re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")),
    ("italic_u", re.compile(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)")),
    ("link", re.compile(r"\[([^\]]+)\]\(([^)]*(?:\([^)]*\)[^)]*)*)\)")),
    ("spoiler", re.compile(r"\|\|(.+?)\|\|")),
    ("blockquote", re.compile(r"^>\s*(.+)$", re.MULTILINE)),
]


def _format_plain_segment(text: str) -> str:
    """Convert a plain text segment to Telegram MarkdownV2.

    Uses placeholder characters to prevent bold/heading output from being
    matched by the italic regex.
    """
    if not text:
        return ""

    _B = "\x00"  # placeholder for bold markers

    # 1. Math
    text = _process_math(text)

    # 2. Tables
    text = _convert_tables_in_text(text)

    # 3. Lists (bullet and numbered)
    text = _convert_lists(text)

    # 4. Spoilers (before bold/italic to avoid || being split)
    text = re.sub(
        r"\|\|(.+?)\|\|",
        lambda m: f"||{escape_markdown_v2(m.group(1))}||",
        text,
    )

    # 5. Bold + Heading (use placeholder to protect from italic regex)
    #    **bold** → *escaped*  (placeholder-wrapped)
    text = re.sub(r"\*\*(.+?)\*\*", lambda m: f"{_B}{escape_markdown_v2(m.group(1))}{_B}", text)
    #    __bold__ → *escaped*  (placeholder-wrapped)
    text = re.sub(r"__(.+?)__", lambda m: f"{_B}{escape_markdown_v2(m.group(1))}{_B}", text)
    #    # heading → *escaped*  (placeholder-wrapped)
    text = re.sub(
        r"^(#{1,6})\s+(.+)$",
        lambda m: f"{_B}{escape_markdown_v2(m.group(2).strip())}{_B}",
        text,
        flags=re.MULTILINE,
    )

    # 6. Italic: *text* → _escaped_ (single * not part of bold)
    #    At this point, real bold uses \x00...\x00, so single * is truly italic
    text = re.sub(
        r"\*(.+?)\*",
        lambda m: f"_{escape_markdown_v2(m.group(1))}_",
        text,
    )

    # 7. Restore bold placeholders: \x00 → *
    text = text.replace(_B, "*")

    # 8. Italic from underscore: _text_ → _escaped_ (single _ not part of __bold__)
    #    Note: __bold__ was already handled above, so remaining _text_ is italic
    text = re.sub(
        r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)",
        lambda m: f"_{escape_markdown_v2(m.group(1))}_",
        text,
    )

    # 9. Links: [label](url) → [escaped_label](escaped_url)
    def _replace_link(m: re.Match) -> str:
        label = m.group(1)
        url = m.group(2)
        return f"[{_escape_link_label(label)}]({_escape_link_url(url)})"
    text = re.sub(r"\[([^\]]+)\]\(([^()]*(?:\([^()]*\)[^()]*)*)\)", _replace_link, text)

    # 10. Blockquotes
    lines = text.split("\n")
    result: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(">"):
            content = stripped[1:].lstrip()
            indent = line[: len(line) - len(stripped)]
            result.append(f"{indent}> {escape_markdown_v2(content)}")
        else:
            result.append(line)
    text = "\n".join(result)

    # 11. Escape remaining plain text
    text = _escape_remaining_text(text)

    return text


def _escape_remaining_text(text: str) -> str:
    """Escape special chars in plain text that aren't part of MarkdownV2 syntax.

    Strategy: split by known MarkdownV2 syntax boundaries, escape the gaps.
    """
    # Find all spans that are MarkdownV2 syntax (bold, italic, code, links, spoilers, blockquotes)
    # and escape everything else.
    #
    # We use a simple approach: process line by line, and for each line,
    # if it starts with known syntax markers, skip it. Otherwise, escape it.

    lines = text.split("\n")
    result: list[str] = []

    for line in lines:
        stripped = line.lstrip()

        # Skip lines that are entirely MarkdownV2 syntax
        if (stripped.startswith("*") and stripped.endswith("*") and len(stripped) > 2 and
                not stripped.startswith("**")):
            result.append(line)
            continue
        if (stripped.startswith("_") and stripped.endswith("_") and len(stripped) > 2 and
                not stripped.startswith("__")):
            result.append(line)
            continue
        if stripped.startswith("```"):
            result.append(line)
            continue
        if stripped.startswith("`") and stripped.endswith("`") and len(stripped) > 1:
            result.append(line)
            continue
        if stripped.startswith("[") and "](" in stripped:
            result.append(line)
            continue
        if stripped.startswith("||") and stripped.endswith("||") and len(stripped) > 4:
            result.append(line)
            continue
        if stripped.startswith("> "):
            result.append(line)
            continue
        if stripped.startswith("• ") or (len(stripped) > 2 and stripped[0].isdigit() and stripped[1:3] in(". ", "\\.")):
            result.append(line)
            continue

        # This line is plain text - escape it
        indent = line[: len(line) - len(stripped)]
        result.append(indent + escape_markdown_v2(stripped))

    return "\n".join(result)


# ---------------------------------------------------------------------------
# Table handling in text
# ---------------------------------------------------------------------------

def _convert_tables_in_text(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    table_buffer: list[str] = []
    in_table = False

    for line in lines:
        if _is_table_line(line.strip()):
            in_table = True
            table_buffer.append(line)
        else:
            if in_table and table_buffer:
                result.append(_table_to_code_block(table_buffer))
                table_buffer = []
                in_table = False
            result.append(line)

    if in_table and table_buffer:
        result.append(_table_to_code_block(table_buffer))

    return "\n".join(result)


def _convert_lists(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if re.match(r"^[-*]\s+", stripped):
            content = re.sub(r"^[-*]\s+", "", stripped)
            indent = line[: len(line) - len(stripped)]
            result.append(f"{indent}• {escape_markdown_v2(content)}")
        elif re.match(r"^\d+\.\s+", stripped):
            match = re.match(r"^(\d+)\.\s+(.+)", stripped)
            if match:
                num = match.group(1)
                content = match.group(2)
                indent = line[: len(line) - len(stripped)]
                result.append(f"{indent}{num}\\. {escape_markdown_v2(content)}")
            else:
                result.append(escape_markdown_v2(line))
        else:
            result.append(line)
    return "\n".join(result)


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def format_ai_response_for_telegram(markdown_text: str) -> str:
    """Convert standard Markdown (from AI) to Telegram MarkdownV2.

    Splits text into code blocks, inline code, and plain text.
    Code/inline-code are preserved as-is (with minimal escaping).
    Plain text goes through full conversion pipeline.
    """
    if not markdown_text or not markdown_text.strip():
        return ""

    segments = _extract_code_segments(markdown_text)

    processed: list[str] = []
    for seg_type, content in segments:
        if seg_type == "code_block":
            lang = content.get("lang", "")
            code = content.get("code", "")
            processed.append(f"```{lang}\n{_escape_code_block(code)}\n```")
        elif seg_type == "inline_code":
            code = content.get("code", "")
            processed.append(f"`{_escape_inline_code(code)}`")
        else:
            plain = content.get("text", "")
            processed.append(_format_plain_segment(plain))

    return "".join(processed)


def _extract_code_segments(text: str) -> list[tuple[str, dict]]:
    """Split text into code blocks, inline code, and plain text segments."""
    segments: list[tuple[str, dict]] = []
    pos = 0
    length = len(text)

    while pos < length:
        # Fenced code block: ```lang\n...```
        block_match = re.match(r"```(\w*)\n(.*?)```", text[pos:], re.DOTALL)
        if block_match:
            lang = block_match.group(1)
            code = block_match.group(2)
            if code.endswith("\n"):
                code = code[:-1]
            segments.append(("code_block", {"lang": lang, "code": code}))
            pos += block_match.end()
            continue

        # Lone ``` - treat as plain text
        if text[pos:pos + 3] == "```":
            segments.append(("plain", {"text": "```"}))
            pos += 3
            continue

        # Inline code: `code`
        inline_match = re.match(r"`([^`]+?)`", text[pos:])
        if inline_match:
            code = inline_match.group(1)
            segments.append(("inline_code", {"code": code}))
            pos += inline_match.end()
            continue

        # Plain text: consume until next ` or end
        next_backtick = text.find("`", pos)
        if next_backtick == -1:
            segments.append(("plain", {"text": text[pos:]}))
            break
        else:
            segments.append(("plain", {"text": text[pos:next_backtick]}))
            pos = next_backtick

    return segments


# ---------------------------------------------------------------------------
# Message splitting
# ---------------------------------------------------------------------------

def split_telegram_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> List[str]:
    """Split a MarkdownV2 message into chunks that fit Telegram's limit."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break

        split_pos = _find_split_point(remaining, limit)
        chunk = remaining[:split_pos]
        remaining = remaining[split_pos:].lstrip("\n")
        chunk = _ensure_code_blocks_closed(chunk)
        chunks.append(chunk)

    return chunks


def _find_split_point(text: str, limit: int) -> int:
    pos = text.rfind("\n\n", 0, limit)
    if pos > limit // 2:
        return pos + 2
    pos = text.rfind("\n", 0, limit)
    if pos > limit // 2:
        return pos + 1
    for sep in [". ", "، ", "! ", "? ", "؟ "]:
        pos = text.rfind(sep, 0, limit)
        if pos > limit // 2:
            return pos + len(sep)
    return limit


def _ensure_code_blocks_closed(text: str) -> str:
    opens = len(re.findall(r"```", text))
    if opens % 2 == 1:
        text += "\n```"
    return text


# ---------------------------------------------------------------------------
# Strip markdown (fallback)
# ---------------------------------------------------------------------------

def strip_markdown(text: str) -> str:
    """Remove all MarkdownV2 formatting for plain-text fallback."""
    text = re.sub(r"```\w*\n(.*?)```", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\\\*", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"\\_", "_", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"\|\|(.+?)\|\|", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\\([_*\[\]()~`>#\+\-=|{}.!])", r"\1", text)
    return text
