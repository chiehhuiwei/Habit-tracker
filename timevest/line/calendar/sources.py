from timevest.core import store

from .. import users


def load_calendar_sources() -> list:
    """每位使用者各自的行事曆來源（存在 SQLite）；沒設定就是空的。"""
    uid = users.current()
    return (store.kv_get(uid, "calendars") if uid else None) or []


def save_calendar_sources(user_id: str, sources: list) -> None:
    store.kv_set(user_id, "calendars", sources)
