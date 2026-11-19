import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

TZ = ZoneInfo("Asia/Taipei")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 專案根目錄


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip('"').strip("'")


CHANNEL_SECRET = _env("LINE_CHANNEL_SECRET")
CHANNEL_TOKEN = _env("LINE_CHANNEL_ACCESS_TOKEN")
OWNER_USER_ID = _env("LINE_OWNER_USER_ID")
LIFF_ID = _env("LIFF_ID")
INVITE_CODE = _env("LINE_INVITE_CODE")
DATA_DIR = _env("LINE_DATA_DIR") or os.path.join(BASE_DIR, "line_data")  # SQLite 資料庫所在（需掛成 volume）
# 舊版 JSON（investments/items/milestones.json）的位置，第一次啟動時匯入資料庫用
LEGACY_DIR = _env("LEGACY_DIR") or os.path.join(BASE_DIR, "legacy")
CALENDARS_FILE = _env("LINE_CALENDARS_FILE") or os.path.join(DATA_DIR, "calendars.json")


def is_enabled() -> bool:
    return bool(CHANNEL_SECRET and CHANNEL_TOKEN)
