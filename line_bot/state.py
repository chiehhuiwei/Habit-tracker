"""LINE 對話執行期狀態（line_data/state.json）：對話步驟、計時中 session、待寫入草稿、已送提醒、擁有者。"""
import json
import os
import threading
import time

from . import config, settings

_lock = threading.Lock()
_FILE = os.path.join(config.DATA_DIR, "state.json")


def ensure_data_dir() -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)


def _load() -> dict:
    if not os.path.exists(_FILE):
        return {}
    with open(_FILE, encoding="utf-8") as f:
        return json.load(f)


def _get(key: str):
    with _lock:
        return _load().get(key)


def _set(key: str, value) -> None:
    with _lock:
        data = _load()
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
        tmp = f"{_FILE}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _FILE)


def get_conv():
    conv = _get("conv")
    if conv and time.time() - conv["ts"] <= settings.CONV_STATE_TTL_SEC:
        return conv
    return None


def set_conv(conv) -> None:
    _set("conv", {**conv, "ts": time.time()} if conv else None)


# session：{investment_id, item_id, memo, start}
def get_session():
    return _get("session")


def set_session(session) -> None:
    _set("session", session)


# 已按結束、還在等頁數／備註的草稿：session + end + progress
def get_pending():
    return _get("pending")


def set_pending(draft) -> None:
    _set("pending", draft)


def get_sent() -> dict:
    return _get("sent") or {}


def set_sent(sent: dict) -> None:
    _set("sent", sent)


def get_last_digest_day():
    return _get("last_digest_day")


def set_last_digest_day(day: str) -> None:
    _set("last_digest_day", day)


def get_owner_id():
    return config.OWNER_USER_ID or _get("owner")


def set_owner_id(user_id: str) -> None:
    _set("owner", user_id)
