"""多人支援：目前使用者（contextvar）、成員名單、每人一份 service 與資料夾。

- 擁有者：LINE_OWNER_USER_ID，或第一個傳訊息的人。其他成員用邀請碼（LINE_INVITE_CODE）加入。
- 所有資料（帳戶、項目、計時狀態、行事曆）都在 SQLite（store.py），以 user_id 區分。
"""
import contextvars
import re
import threading
from contextlib import contextmanager

from timevest.core import store

from . import config

_current = contextvars.ContextVar("current_user", default=None)
_lock = threading.Lock()
_services: dict = {}
_factory = None
_single = None  # 測試／單人模式：所有人共用同一個 service
_ID_RE = re.compile(r"[A-Za-z0-9_-]+")


# ---------- 註冊表（SQLite）----------
def owner_id():
    return config.OWNER_USER_ID or store.meta_get("owner")


def set_owner_id(user_id: str) -> None:
    store.meta_set("owner", user_id)


def members() -> list:
    owner = owner_id()
    return ([owner] if owner else []) + [m for m in store.list_users() if m != owner]


def is_member(user_id: str) -> bool:
    return user_id in members()


def add_member(user_id: str) -> None:
    if not _ID_RE.fullmatch(user_id or ""):
        raise ValueError("invalid user id")
    store.add_user(user_id)


# ---------- 目前使用者 ----------
def current():
    """沒有明確指定時退回擁有者（單人模式與排程相容）。"""
    return _current.get() or owner_id()


@contextmanager
def use(user_id: str):
    token = _current.set(user_id)
    try:
        yield
    finally:
        _current.reset(token)


def set_current(user_id: str) -> None:
    _current.set(user_id)


def is_owner(user_id) -> bool:
    return bool(user_id) and user_id == owner_id()


# ---------- service ----------
def bind_factory(factory) -> None:
    global _factory
    _factory = factory
    _services.clear()


def bind_single(service) -> None:
    global _single
    _single = service


def service_for(user_id: str):
    if _single is not None:
        return _single
    if _factory is None:
        raise RuntimeError("timevest.line 尚未綁定 TimeVestService")
    with _lock:
        if user_id not in _services:
            _services[user_id] = _factory(user_id)
        return _services[user_id]
