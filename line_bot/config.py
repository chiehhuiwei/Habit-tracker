import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

TZ = ZoneInfo("Asia/Taipei")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip('"').strip("'")


CHANNEL_SECRET = _env("LINE_CHANNEL_SECRET")
CHANNEL_TOKEN = _env("LINE_CHANNEL_ACCESS_TOKEN")
OWNER_USER_ID = _env("LINE_OWNER_USER_ID")
DATA_DIR = _env("LINE_DATA_DIR") or os.path.join(BASE_DIR, "line_data")
CALENDARS_FILE = _env("LINE_CALENDARS_FILE") or os.path.join(DATA_DIR, "calendars.json")


def is_enabled() -> bool:
    return bool(CHANNEL_SECRET and CHANNEL_TOKEN)
