# Security

This bot needs a Telegram bot token and an NVIDIA API key. Keep both outside the repository.

If a token was committed, uploaded, or sent to someone else, rotate it. Removing it from Git history is not enough.

Files that must stay local:

- `.env`
- `bot.log`
- `bot_state.json`
- `group_prompts.json`
- `group_logs/`
- virtual environments

Run this before publishing:

```bash
python scripts/check_public_safety.py
```
