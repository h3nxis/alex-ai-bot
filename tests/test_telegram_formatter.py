"""
Tests for telegram_formatter.py
"""

import sys
import os

# Add project root to path so we can import src modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.telegram_formatter import (
    escape_markdown_v2,
    format_ai_response_for_telegram,
    split_telegram_message,
    strip_markdown,
    _simple_latex_to_unicode,
    _convert_inline_math,
    _convert_block_math,
    _table_to_code_block,
    _is_table_line,
    _is_table_separator,
    _display_width,
)


# ---------------------------------------------------------------------------
# escape_markdown_v2
# ---------------------------------------------------------------------------


class TestEscapeMarkdownV2:
    def test_simple_text_no_special_chars(self):
        assert escape_markdown_v2("hello") == "hello"

    def test_plus_equals_exclamation(self):
        assert escape_markdown_v2("2 + 2 = 4!") == "2 \\+ 2 \\= 4\\!"

    def test_underscore(self):
        assert escape_markdown_v2("hello_world!") == "hello\\_world\\!"

    def test_persian_text_with_special_chars(self):
        result = escape_markdown_v2("سلام! چطوری؟ خوبی-خوشی")
        assert "\\!" in result
        assert "\\-" in result

    def test_all_special_chars_escaped(self):
        text = "_*[]()~`>#+-=|{}.!"
        result = escape_markdown_v2(text)
        for ch in "_*[]()~`>#+-=|{}.!":
            assert f"\\{ch}" in result

    def test_empty_string(self):
        assert escape_markdown_v2("") == ""

    def test_backslash_not_doubled(self):
        # Backslash itself should be escaped
        result = escape_markdown_v2("a\\b")
        assert "\\\\" in result


# ---------------------------------------------------------------------------
# format_ai_response_for_telegram - headings
# ---------------------------------------------------------------------------


class TestHeadings:
    def test_h1_to_bold(self):
        result = format_ai_response_for_telegram("# سلام")
        assert result == "*سلام*"

    def test_h2_to_bold(self):
        result = format_ai_response_for_telegram("## عنوان")
        assert result == "*عنوان*"

    def test_h3_to_bold(self):
        result = format_ai_response_for_telegram("### فصل اول")
        assert result == "*فصل اول*"

    def test_heading_with_special_chars(self):
        result = format_ai_response_for_telegram("# hello_world!")
        assert result == "*hello\\_world\\!*"


# ---------------------------------------------------------------------------
# format_ai_response_for_telegram - bold / italic
# ---------------------------------------------------------------------------


class TestBoldItalic:
    def test_bold_double_star(self):
        result = format_ai_response_for_telegram("**متن بولد**")
        assert result == "*متن بولد*"

    def test_bold_double_underscore(self):
        result = format_ai_response_for_telegram("__متن بولد__")
        assert result == "*متن بولد*"

    def test_italic_single_star(self):
        result = format_ai_response_for_telegram("*متن ایتالیک*")
        assert result == "_متن ایتالیک_"

    def test_italic_single_underscore(self):
        result = format_ai_response_for_telegram("_متن ایتالیک_")
        assert result == "_متن ایتالیک_"


# ---------------------------------------------------------------------------
# format_ai_response_for_telegram - inline code
# ---------------------------------------------------------------------------


class TestInlineCode:
    def test_inline_code_preserved(self):
        result = format_ai_response_for_telegram("کد: `print('hi')`")
        assert "`print('hi')`" in result

    def test_inline_code_with_backtick_inside(self):
        # This is tricky - backtick inside inline code
        result = format_ai_response_for_telegram("use `backtick` here")
        assert "`" in result


# ---------------------------------------------------------------------------
# format_ai_response_for_telegram - code blocks
# ---------------------------------------------------------------------------


class TestCodeBlock:
    def test_python_code_block(self):
        text = "```python\nprint('hello')\n```"
        result = format_ai_response_for_telegram(text)
        assert "```python" in result
        assert "print('hello')" in result
        assert "```" in result

    def test_plain_code_block(self):
        text = "```\nsome code\n```"
        result = format_ai_response_for_telegram(text)
        assert "```" in result
        assert "some code" in result


# ---------------------------------------------------------------------------
# format_ai_response_for_telegram - links
# ---------------------------------------------------------------------------


class TestLinks:
    def test_simple_link(self):
        result = format_ai_response_for_telegram("[گوگل](https://google.com)")
        assert "[گوگل](https://google.com)" in result

    def test_link_with_special_chars_in_label(self):
        result = format_ai_response_for_telegram("[hello_world!](https://example.com)")
        assert "hello\\_world\\!" in result

    def test_link_with_parentheses_in_url(self):
        result = format_ai_response_for_telegram("[wiki](https://en.wikipedia.org/wiki/Foo_(bar))")
        assert "\\)" in result


# ---------------------------------------------------------------------------
# format_ai_response_for_telegram - lists
# ---------------------------------------------------------------------------


class TestLists:
    def test_bullet_list(self):
        result = format_ai_response_for_telegram("- آیتم ۱\n- آیتم ۲")
        assert "• آیتم ۱" in result
        assert "• آیتم ۲" in result

    def test_numbered_list(self):
        result = format_ai_response_for_telegram("1. اول\n2. دوم")
        assert "1\\. اول" in result
        assert "2\\. دوم" in result

    def test_bullet_with_star(self):
        result = format_ai_response_for_telegram("* آیتم")
        assert "• آیتم" in result


# ---------------------------------------------------------------------------
# format_ai_response_for_telegram - blockquotes
# ---------------------------------------------------------------------------


class TestBlockquotes:
    def test_blockquote(self):
        result = format_ai_response_for_telegram("> نکته مهم")
        assert "> نکته مهم" in result


# ---------------------------------------------------------------------------
# format_ai_response_for_telegram - spoilers
# ---------------------------------------------------------------------------


class TestSpoilers:
    def test_spoiler(self):
        result = format_ai_response_for_telegram("||متن مخفی||")
        assert "||" in result
        assert "متن مخفی" in result


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class TestTables:
    def test_is_table_line(self):
        assert _is_table_line("| a | b |") is True
        assert _is_table_line("not a table") is False

    def test_is_table_separator(self):
        assert _is_table_separator("| --- | --- |") is True
        assert _is_table_separator("| --- |:---:| --- |") is True
        assert _is_table_separator("| a | b |") is False

    def test_table_to_code_block(self):
        lines = [
            "| نام  | سن |",
            "| --- | --- |",
            "| علی  | ۲۰ |",
            "| سارا | ۲۱ |",
        ]
        result = _table_to_code_block(lines)
        assert "```text" in result
        assert "```" in result
        assert "نام" in result
        assert "علی" in result

    def test_table_in_full_format(self):
        text = (
            "| نام  | سن |\n"
            "| --- | --- |\n"
            "| علی  | ۲۰ |\n"
            "| سارا | ۲۱ |"
        )
        result = format_ai_response_for_telegram(text)
        assert "```text" in result

    def test_display_width(self):
        assert _display_width("abc") == 3
        assert _display_width("سلام") == 4  # 2 Arabic chars × 2


# ---------------------------------------------------------------------------
# Math / LaTeX
# ---------------------------------------------------------------------------


class TestMath:
    def test_simple_latex_to_unicode_pi(self):
        result = _simple_latex_to_unicode(r"\pi")
        assert result == "π"

    def test_simple_latex_to_unicode_sqrt(self):
        result = _simple_latex_to_unicode(r"\sqrt{x}")
        assert result == "√x"

    def test_simple_latex_to_unicode_superscript(self):
        result = _simple_latex_to_unicode("x^2")
        assert "²" in result

    def test_inline_math(self):
        result = format_ai_response_for_telegram("فرمول: $a^2 + b^2 = c^2$")
        assert "`" in result or "²" in result

    def test_block_math(self):
        text = "$$\nE = mc^2\n$$"
        result = format_ai_response_for_telegram(text)
        assert "```" in result

    def test_inline_math_fraction(self):
        result = _simple_latex_to_unicode(r"\frac{a}{b}")
        assert "(a)/(b)" in result

    def test_inline_math_symbols(self):
        result = _simple_latex_to_unicode(r"\alpha + \beta = \gamma")
        assert "α" in result
        assert "β" in result
        assert "γ" in result


# ---------------------------------------------------------------------------
# split_telegram_message
# ---------------------------------------------------------------------------


class TestSplitMessage:
    def test_short_message_not_split(self):
        text = "Hello world"
        result = split_telegram_message(text)
        assert len(result) == 1
        assert result[0] == text

    def test_long_message_split(self):
        text = "Line\n\n" * 1000
        result = split_telegram_message(text, limit=200)
        assert len(result) > 1
        for part in result:
            assert len(part) <= 200

    def test_code_block_not_broken(self):
        text = "```python\nprint('hello')\n```\n" + "x" * 5000
        result = split_telegram_message(text, limit=100)
        # At least one chunk should contain the full code block
        found = False
        for part in result:
            if "print('hello')" in part and "```python" in part and "```" in part:
                found = True
        assert found


# ---------------------------------------------------------------------------
# strip_markdown (fallback)
# ---------------------------------------------------------------------------


class TestStripMarkdown:
    def test_strip_bold(self):
        result = strip_markdown("**bold text**")
        assert "bold text" in result
        assert "*" not in result

    def test_strip_inline_code(self):
        result = strip_markdown("`code`")
        assert "code" in result
        assert "`" not in result

    def test_strip_link(self):
        result = strip_markdown("[label](url)")
        assert "label" in result
        assert "(" not in result

    def test_strip_escape_chars(self):
        result = strip_markdown("hello\\_world\\!")
        assert "hello_world!" in result


# ---------------------------------------------------------------------------
# Persian text integration
# ---------------------------------------------------------------------------


class TestPersianText:
    def test_persian_with_exclamation(self):
        result = format_ai_response_for_telegram("سلام!")
        assert "\\!" in result

    def test_persian_with_dot(self):
        result = format_ai_response_for_telegram("سلام. خوبی؟")
        assert "\\." in result

    def test_persian_mixed(self):
        text = "این یک تست است! قیمت ۲ + ۲ = ۴ می‌باشد."
        result = format_ai_response_for_telegram(text)
        # Should not crash
        assert isinstance(result, str)
        assert len(result) > 0

    def test_persian_bold_with_special_chars(self):
        result = format_ai_response_for_telegram("**قیمت: ۱۰۰۰ تومان!**")
        assert "*" in result
        assert "قیمت" in result
