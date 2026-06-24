# Project state

The bot uses Telegram Rich Messages as the main output path.

Main flow:

```text
NVIDIA NIM response
→ clean Markdown
→ TelegramSender.send_ai_response
→ sendRichMessage
→ plain text fallback
```

Notes for future edits:

- Keep `sendRichMessage` as the main path.
- Do not convert AI answers to Telegram MarkdownV2 in the main path.
- Keep fixed bot messages in Markdown, but do not over-format casual replies.
- Avoid committing runtime files or local logs.
- Keep the prompt direct and natural. It should not force headings, emojis, or bold text into every answer.
