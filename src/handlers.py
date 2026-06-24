import asyncio
from telegram import Update, ReactionTypeEmoji
from telegram.ext import ContextTypes
from datetime import datetime
import os
import json
import logging

from .prompt_manager import set_system_prompt, get_system_prompt, delete_system_prompt
from .nim_ai import get_response
from .channel_reader import get_channel_news
from .telegram_sender import TelegramSender

LOG_DIR = "group_logs"
STATE_FILE = "bot_state.json"

REACTION_THINKING = [ReactionTypeEmoji(emoji="🤔")]
REACTION_DONE = [ReactionTypeEmoji(emoji="👍")]
REACTION_ERROR = [ReactionTypeEmoji(emoji="👎")]

sender = TelegramSender()


def _load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.exception("Failed to save bot state: %s", e)


async def _add_reaction(context, chat_id, message_id, reaction):
    try:
        await context.bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=reaction,
        )
    except Exception as e:
        logging.debug("Reaction failed: %s", e)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    state = _load_state()
    state[str(chat.id)] = datetime.now().isoformat()
    _save_state(state)

    chat_id = update.effective_chat.id
    text = f"""## سلام {user.first_name}

**من الکس هستم**؛ دستیار هوش مصنوعی گروه.

### چطور استفاده کنی؟

- من را با `الکس` یا `alex` صدا بزن.
- به پیام من ریپلای کن.
- برای راهنمای کامل بزن: `/help`
"""
    await sender.send_bot_message(
        chat_id=chat_id,
        markdown=text,
        reply_to_message_id=update.effective_message.message_id if update.effective_message else None,
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """## راهنمای الکس

### دستورات

| دستور | کاربرد |
|---|---|
| `/start` | شروع کار با ربات |
| `/help` | نمایش راهنما |
| `/setprompt <متن>` | تنظیم پرامپت سفارشی گروه |
| `/delprompt` | حذف پرامپت سفارشی |
| `/showprompt` | نمایش پرامپت فعلی |
| `/search <عبارت>` | جستجوی وب |
| `/latex <فرمول>` | نمایش فرمول ریاضی |
| `/news` | آخرین اخبار از @VahidOnline |

### روش استفاده

- `الکس <سوال>` یا `alex <question>` بنویس.
- به پیام الکس ریپلای کن.
- برای جستجو بگو: **سرچ کن...**
- برای اخبار بگو: **چه خبر؟** یا **اخبار**
- برای فرمول ریاضی از `$...$` یا `$$...$$` استفاده کن.

### توانایی‌ها

- **اخبار و خلاصه‌سازی**
- **جستجوی وب**
- **ترجمه فارسی/انگلیسی**
- **محاسبات و فرمول‌های ریاضی**
- **نوشتن و توضیح کد**
"""
    await sender.send_bot_message(
        chat_id=update.effective_chat.id,
        markdown=help_text,
        reply_to_message_id=update.effective_message.message_id if update.effective_message else None,
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("Bot error: %s", context.error, exc_info=context.error)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await sender.send_bot_message(
            chat_id=update.effective_chat.id,
            markdown="**استفاده درست:** `/search <عبارت جستجو>`",
        )
        return

    query = " ".join(context.args)
    await sender.send_bot_message(
        chat_id=update.effective_chat.id,
        markdown=f"**در حال جستجو:** `{query}`",
    )

    from .web_search import web_search
    result = await web_search(query)

    if result and len(result) > 4000:
        result = result[:4000] + "\n\n... (نتایج بیشتر حذف شد)"

    await sender.send_bot_message(
        chat_id=update.effective_chat.id,
        markdown=result or "**نتیجه‌ای یافت نشد.**",
    )


async def latex_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await sender.send_bot_message(
            chat_id=update.effective_chat.id,
            markdown=(
                "## استفاده از فرمول\n\n"
                "**فرمت:** `/latex <فرمول>`\n\n"
                "### مثال‌ها\n\n"
                "- `/latex E = mc^2`\n"
                "- `/latex \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}`"
            ),
            reply_to_message_id=update.effective_message.message_id if update.effective_message else None,
        )
        return

    formula = " ".join(context.args)
    await sender.send_bot_message(
        chat_id=update.effective_chat.id,
        markdown=f"## فرمول شما\n\n$${formula}$$",
        reply_to_message_id=update.effective_message.message_id if update.effective_message else None,
    )

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await sender.send_bot_message(
        chat_id=update.effective_chat.id,
        markdown="**در حال دریافت اخبار از @VahidOnline...**",
    )

    query = " ".join(context.args) if context.args else ""
    result = await get_channel_news(query)

    if result and len(result) > 4000:
        result = result[:4000] + "\n\n... (ادامه حذف شد)"

    await sender.send_bot_message(
        chat_id=update.effective_chat.id,
        markdown=result or "**اخباری یافت نشد.**",
    )


def _reply_to_label(msg) -> str:
    if not msg.reply_to_message:
        return ""
    r = msg.reply_to_message
    who = ""
    if r.from_user:
        who = r.from_user.full_name or r.from_user.username or "ناشناس"
    elif r.sender_chat:
        who = r.sender_chat.title or "چنل/گروه"
    reply_text = (r.text or r.caption or "").strip()
    if reply_text and len(reply_text) > 100:
        reply_text = reply_text[:100] + "..."
    if reply_text:
        return f" (پاسخ به {who}: «{reply_text}»)"
    return f" (پاسخ به {who})"


def _forward_label(msg) -> str:
    origin = getattr(msg, "forward_origin", None)
    if not origin:
        return ""
    cls = type(origin).__name__
    if "Hidden" in cls and getattr(origin, "sender_user_name", None):
        return f" (فوروارد از: {origin.sender_user_name})"
    if "User" in cls and getattr(origin, "sender_user", None):
        u = origin.sender_user
        return f" (فوروارد از: {getattr(u, 'full_name', None) or getattr(u, 'username', 'ناشناس')})"
    if "Channel" in cls and getattr(origin, "chat", None):
        return f" (فوروارد از: {getattr(origin.chat, 'title', 'چنل')})"
    if "Chat" in cls and getattr(origin, "sender_chat", None):
        return f" (فوروارد از: {getattr(origin.sender_chat, 'title', 'چت')})"
    return " (فوروارد)"


async def save_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or getattr(update, "edited_message", None)
    if not update.effective_chat or not msg:
        return

    group_id = update.effective_chat.id
    user = update.effective_user or msg.from_user
    user_name = user.full_name if user else "Unknown"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = msg.text or msg.caption or ""

    reply_label = _reply_to_label(msg)
    forward_label = _forward_label(msg)
    prefix = f"[{timestamp}] {user_name}{reply_label}{forward_label}{msg.message_id}: "
    line = prefix + (text or "[بدون متن]") + "\n"

    file_path = os.path.join(LOG_DIR, f"group_{group_id}.txt")
    os.makedirs(os.path.dirname(file_path) or LOG_DIR, exist_ok=True)

    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        logging.exception("Failed to save group message: %s", e)


async def save_group_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message or not update.message.voice:
        return

    group_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id if user else "0"

    group_folder = os.path.join(LOG_DIR, f"group_{group_id}")
    os.makedirs(group_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"voice_{user_id}_{timestamp}.ogg"
    file_path = os.path.join(group_folder, filename)

    try:
        voice = update.message.voice
        file = await voice.get_file()
        await file.download_to_drive(file_path)
    except Exception as e:
        logging.exception("Failed to download voice message: %s", e)


async def setprompt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await sender.send_bot_message(
            chat_id=chat.id if chat else update.effective_chat.id,
            markdown="**این دستور فقط در گروه‌ها قابل استفاده است.**",
            reply_to_message_id=update.effective_message.message_id if update.effective_message else None,
        )
        return

    if not context.args:
        await sender.send_bot_message(
            chat_id=chat.id,
            markdown=(
                "## تنظیم پرامپت گروه\n\n"
                "**فرمت:** `/setprompt <متن پرامپت>`\n\n"
                "**مثال:** `/setprompt تو یک دستیار فارسی‌زبان هستی.`\n\n"
                "نکته: قوانین Rich Markdown همیشه حفظ می‌شوند و پرامپت سفارشی به آن اضافه می‌شود."
            ),
            reply_to_message_id=update.effective_message.message_id if update.effective_message else None,
        )
        return

    prompt_text = " ".join(context.args)
    set_system_prompt(chat.id, prompt_text)
    await sender.send_bot_message(
        chat_id=chat.id,
        markdown=(
            "## پرامپت سیستم تنظیم شد\n\n"
            f"{prompt_text[:500]}"
            + ("..." if len(prompt_text) > 500 else "")
        ),
        reply_to_message_id=update.effective_message.message_id if update.effective_message else None,
    )

async def delprompt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await sender.send_bot_message(
            chat_id=chat.id,
            markdown="**این دستور فقط در گروه‌ها قابل استفاده است.**",
        )
        return

    current = get_system_prompt(chat.id)
    if not current:
        await sender.send_bot_message(
            chat_id=chat.id, markdown="**پرامپتی تنظیم نشده.**"
        )
        return

    delete_system_prompt(chat.id)
    await sender.send_bot_message(
        chat_id=chat.id, markdown="**پرامپت حذف شد.**"
    )


async def showprompt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat or chat.type not in ("group", "supergroup"):
        await sender.send_bot_message(
            chat_id=chat.id,
            markdown="**این دستور فقط در گروه‌ها قابل استفاده است.**",
        )
        return

    prompt = get_system_prompt(chat.id)
    if not prompt:
        await sender.send_bot_message(
            chat_id=chat.id, markdown="**پرامپتی تنظیم نشده.**"
        )
    else:
        await sender.send_bot_message(
            chat_id=chat.id, markdown=f"## پرامپت فعلی\n\n{prompt}"
        )


async def mention_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message or update.edited_message
        if not update.effective_chat or not msg:
            return

        text = msg.text or msg.caption or ""
        group_id = update.effective_chat.id

        state = _load_state()
        start_time_str = state.get(str(group_id))
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
                msg_time = msg.date.replace(tzinfo=None)
                if msg_time < start_time:
                    return
            except Exception:
                pass

        has_mention = any(word in text.lower() for word in ["الکس", "alex"])
        is_reply_to_bot = (
            msg.reply_to_message
            and msg.reply_to_message.from_user
            and msg.reply_to_message.from_user.id == context.bot.id
        )

        if not has_mention and not is_reply_to_bot:
            return

        message_id = msg.message_id
        user = update.effective_user or msg.from_user
        user_name = user.full_name if user else "Unknown"

        reply_label = _reply_to_label(msg)
        forward_label = _forward_label(msg)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = f"[{timestamp}] {user_name}{reply_label}{forward_label}{message_id}: "
        line = prefix + (text or "[بدون متن]") + "\n"

        file_path = os.path.join(LOG_DIR, f"group_{group_id}.txt")
        os.makedirs(os.path.dirname(file_path) or LOG_DIR, exist_ok=True)
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            logging.exception("Failed to save group message: %s", e)

        await _add_reaction(context, group_id, message_id, REACTION_THINKING)

        system_prompt = get_system_prompt(group_id) or None
        res = await get_response(group_id, text, system_prompt=system_prompt, username=user_name)

        if res:
            await _add_reaction(context, group_id, message_id, REACTION_DONE)
            await sender.send_ai_response(
                chat_id=group_id,
                ai_answer=res,
                reply_to_message_id=message_id,
            )

            try:
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(f"bot reply to {message_id}: {res}\n")
            except Exception:
                pass
        else:
            await _add_reaction(context, group_id, message_id, REACTION_ERROR)

    except Exception as e:
        logging.exception("mention_handler crashed: %s", e)
