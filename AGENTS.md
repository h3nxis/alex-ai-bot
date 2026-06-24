# Agent instructions

Make small, safe changes. The bot is already wired to send Rich Markdown through `TelegramSender`.

Do not route AI answers through MarkdownV2 unless a separate fallback is implemented and tested.

Writing style for user-facing text:

- Prefer plain, specific wording.
- Use Markdown only when it helps readability.
- Avoid promotional language, vague claims, forced lists, and decorative emojis.
- Avoid em dashes and en dashes in docs and prompts.
- Do not overuse bold text.
- Keep Persian replies natural and short unless the user asks for detail.

Before handing back changes, run:

```bash
python -m pytest -q
python scripts/check_public_safety.py
```
