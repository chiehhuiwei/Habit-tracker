"""LINE 對話執行期狀態（SQLite kv，每位使用者各自一份）：對話步驟、計時中 session、待寫入草稿、已送提醒、擁有者。"""
import os
import time

from timevest.core import store

from . import config, settings, users


def ensure_data_dir() -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)


def _uid() -> str:
    uid = users.current()
    if not uid:
        raise RuntimeError("沒有目前使用者")
    return uid


def _get(key: str):
    return store.kv_get(_uid(), key)


def _set(key: str, value) -> None:
    store.kv_set(_uid(), key, value)


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
    return users.owner_id()


def set_owner_id(user_id: str) -> None:
    users.set_owner_id(user_id)
