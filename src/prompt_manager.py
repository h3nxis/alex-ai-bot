import os
import json
import logging

PROMPTS_FILE = "group_prompts.json"
LOG_DIR = "group_logs"


def _load_prompts() -> dict:
    if not os.path.exists(PROMPTS_FILE):
        return {}
    try:
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.exception("Failed to load prompts: %s", e)
        return {}


def _save_prompts(prompts: dict):
    try:
        with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.exception("Failed to save prompts: %s", e)


def get_system_prompt(group_id: int | str) -> str:
    prompts = _load_prompts()
    return prompts.get(str(group_id), "")


def set_system_prompt(group_id: int | str, prompt: str):
    prompts = _load_prompts()
    prompts[str(group_id)] = prompt.strip()
    _save_prompts(prompts)
    logging.info("Set system prompt for group %s", group_id)


def delete_system_prompt(group_id: int | str):
    prompts = _load_prompts()
    if str(group_id) in prompts:
        del prompts[str(group_id)]
        _save_prompts(prompts)
        logging.info("Deleted system prompt for group %s", group_id)


def read_last_messages(group_id: int | str, count: int = 200) -> list[str]:
    file_path = os.path.join(LOG_DIR, f"group_{group_id}.txt")
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines[-count:] if len(lines) > count else lines
    except Exception as e:
        logging.exception("Failed to read group messages: %s", e)
        return []
