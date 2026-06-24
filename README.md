# Alex Telegram bot

Alex is a Persian Telegram bot that answers with Telegram Rich Messages. It sends the model output as clean Markdown through `sendRichMessage`, then falls back to plain `sendMessage` if Telegram rejects the rich message.

The project is kept small on purpose. It uses Python, `python-telegram-bot`, NVIDIA NIM, and a thin sender layer around the Telegram Bot API.

## What it does

- Replies in private chats and groups when users mention `الکس` or `alex`
- Sends answers as Rich Markdown, not MarkdownV2
- Supports headings, lists, tables, code blocks, and math blocks when Telegram accepts them
- Uses a plain text fallback when rich messages fail
- Can read recent group context from local logs
- Can run behind a local SOCKS proxy

## How messages are sent

```text
AI clean Markdown
→ TelegramSender.send_ai_response()
→ Telegram Bot API sendRichMessage
→ fallback: sendMessage without parse_mode
```

The bot does not send AI answers through the old MarkdownV2 formatter. That formatter is still in the repository for tests and possible future fallback work, but it is not the main path.

## Setup

Create a virtual environment first. This avoids the common SOCKS proxy error that happens when the system Python does not have `socksio` installed.

```bash
cd telegram-bot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create your local environment file:

```bash
cp .env.example .env
```

Fill these values in `.env`:

```env
BOT_TOKEN=your-telegram-bot-token
NVIDIA_API_KEY=your-nvidia-api-key
```

Run the bot:

```bash
python main.py
```

Do not run it with `/usr/bin/python3` after creating a virtual environment. Use the activated `python` command so the installed dependencies are used.

## Proxy notes

If your VPN exposes a local SOCKS proxy, use `socks5://`, not `socks://`:

```bash
export ALL_PROXY=socks5://127.0.0.1:10808
export HTTPS_PROXY=socks5://127.0.0.1:10808
export HTTP_PROXY=socks5://127.0.0.1:10808
python main.py
```

The project normalizes `socks://127.0.0.1:10808` to `socks5://127.0.0.1:10808`, but installing the SOCKS dependencies is still required:

```bash
python -m pip install -r requirements.txt
```

To ignore proxy variables for this bot:

```bash
export BOT_DISABLE_PROXY=1
python main.py
```

## Commands

| Command | What it does |
|---|---|
| `/start` | Starts the bot |
| `/help` | Shows usage help |
| `/setprompt <text>` | Sets a custom prompt for the current group |
| `/delprompt` | Deletes the group prompt |
| `/showprompt` | Shows the current group prompt |
| `/search <query>` | Runs a web search helper |
| `/latex <formula>` | Sends a math formula as a Rich Markdown block |
| `/news` | Gets recent channel news if configured |

## Manual checks

Send these messages in Telegram after starting the bot:

```text
الکس سلام، وضعیت چطوره؟
```

Expected result: a short Persian reply with light Markdown.

```text
الکس یه جدول مقایسه پایتون و جاوااسکریپت بده
```

Expected result: a compact Markdown table.

```text
الکس فرمول انرژی انیشتین رو توضیح بده
```

Expected result: a math block like this:

```markdown
$$
E = mc^2
$$
```

## Tests

```bash
python -m pytest -q
```

If tests fail because `telegram` is missing, install the project dependencies inside the virtual environment:

```bash
python -m pip install -r requirements.txt
```

## Public repo checklist

Before pushing to GitHub:

- Do not commit `.env`
- Do not commit `bot.log`, `bot_state.json`, `group_prompts.json`, or `group_logs/`
- Do not commit `.venv/` or `venv/`
- Rotate any token that was ever shared, logged, zipped, or committed
- Search the repo for old keys before pushing

A quick check:

```bash
python scripts/check_public_safety.py
```

## License

MIT. See `LICENSE`.
