import os
import sys
import time
import logging
from dotenv import load_dotenv

load_dotenv()

from src.proxy_utils import normalize_proxy_environment

normalize_proxy_environment()

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest
from src.handlers import (
    start_command,
    help_command,
    error_handler,
    save_group_message,
    save_group_voice,
    setprompt_command,
    delprompt_command,
    showprompt_command,
    mention_handler,
    search_command,
    latex_command,
    news_command,
)

TOKEN = os.getenv("BOT_TOKEN")

LOG_DIR = "group_logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
# httpx INFO logs include full Telegram URLs with the bot token. Keep them out of logs.
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

MAX_RESTARTS = 10
RESTART_WINDOW = 600
_restart_times = []


def _should_restart():
    now = time.time()
    global _restart_times
    _restart_times = [t for t in _restart_times if now - t < RESTART_WINDOW]
    if len(_restart_times) >= MAX_RESTARTS:
        logging.critical("ربات %d بار کرش کرد. متوقف میشه.", MAX_RESTARTS)
        return False
    return True


def _build_app():
    request = HTTPXRequest(
        connect_timeout=10.0,
        read_timeout=120.0,
        write_timeout=10.0,
        pool_timeout=10.0,
    )
    app = ApplicationBuilder().token(TOKEN).request(request).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("setprompt", setprompt_command))
    app.add_handler(CommandHandler("delprompt", delprompt_command))
    app.add_handler(CommandHandler("showprompt", showprompt_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("latex", latex_command))
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(
        MessageHandler(
            filters.TEXT & (
                filters.Regex(r"(?i)\b(الکس|alex)\b") |
                filters.Entity("mention") |
                filters.REPLY
            ),
            mention_handler,
        )
    )
    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.GROUPS, save_group_message)
    )
    app.add_handler(
        MessageHandler(filters.VOICE & filters.ChatType.GROUPS, save_group_voice)
    )
    try:
        app.add_error_handler(error_handler)
    except Exception:
        pass
    return app


def main():
    if not TOKEN:
        logging.error("BOT_TOKEN در فایل .env پیدا نشد.")
        return

    logging.info("=== ربات شروع به کار کرد ===")
    while True:
        try:
            app = _build_app()
            app.run_polling(drop_pending_updates=True)
            logging.warning("run_polling بدون خطا برگشت، ری‌استارت...")
        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt دریافت شد.")
            break
        except Exception:
            logging.exception("ربات کرش کرد!")
            if not _should_restart():
                break
            _restart_times.append(time.time())
        time.sleep(3)
        logging.info("ری‌استارت ربات...")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    logging.info("=== ربات متوقف شد ===")


if __name__ == "__main__":
    main()
