import json
import os

from .. import config


def load_calendar_sources() -> list:
    """每次重新讀檔，修改 calendars.json 不需重啟。"""
    if not os.path.exists(config.CALENDARS_FILE):
        print(f"[calendar] 找不到 {config.CALENDARS_FILE}，請由 line_bot/calendars.example.json 複製")
        return []
    with open(config.CALENDARS_FILE, encoding="utf-8") as f:
        return json.load(f)
