"""SQLite 儲存層：取代 investments.json / items.json / milestones.json / state.json / users.json / calendars.json。

所有資料都帶 user_id，每位使用者各自一份。清單類資料（帳戶、項目、里程碑）以 JSON 存放，
整份取出／整份寫回（單一交易），維持 TimeVestService 原本「記憶體 list + 存檔」的用法。
"""
import json
import os
import sqlite3
import threading

_lock = threading.RLock()
_conn = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, joined_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS kv (user_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT, PRIMARY KEY (user_id, key));
CREATE TABLE IF NOT EXISTS investments (user_id TEXT NOT NULL, id TEXT NOT NULL, pos INTEGER, data TEXT NOT NULL, PRIMARY KEY (user_id, id));
CREATE TABLE IF NOT EXISTS items (user_id TEXT NOT NULL, id TEXT NOT NULL, pos INTEGER, data TEXT NOT NULL, PRIMARY KEY (user_id, id));
CREATE TABLE IF NOT EXISTS milestones (user_id TEXT NOT NULL, id TEXT NOT NULL, pos INTEGER, data TEXT NOT NULL, PRIMARY KEY (user_id, id));
CREATE INDEX IF NOT EXISTS idx_items_user ON items (user_id);
"""

_LISTS = ("investments", "items", "milestones")


def default_path() -> str:
    from timevest.line import config

    return os.environ.get("TIMEVEST_DB", "").strip() or os.path.join(config.DATA_DIR, "timevest.db")


def connect(path=None) -> sqlite3.Connection:
    """開啟（或切換）資料庫。測試可傳入暫存路徑。"""
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
        path = path or default_path()
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        _conn = sqlite3.connect(path, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(SCHEMA)
        _conn.commit()
        return _conn


def _c() -> sqlite3.Connection:
    return _conn or connect()


# ---------- 清單：帳戶／項目／里程碑 ----------
def load_list(table: str, user_id: str):
    """回傳 list，使用者從未存過時回傳 None（讓呼叫端決定是否放預設值）。"""
    assert table in _LISTS
    with _lock:
        rows = _c().execute(f"SELECT data FROM {table} WHERE user_id=? ORDER BY pos", (user_id,)).fetchall()
    return [json.loads(r[0]) for r in rows] if rows else None


def save_list(table: str, user_id: str, rows: list) -> None:
    assert table in _LISTS
    with _lock:
        c = _c()
        with c:  # 單一交易：整份取代
            c.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
            c.executemany(
                f"INSERT INTO {table} (user_id, id, pos, data) VALUES (?,?,?,?)",
                [(user_id, r["id"], i, json.dumps(r, ensure_ascii=False)) for i, r in enumerate(rows)],
            )


# ---------- kv：每人的對話／計時／草稿／行事曆／旗標 ----------
def kv_get(user_id: str, key: str):
    with _lock:
        row = _c().execute("SELECT value FROM kv WHERE user_id=? AND key=?", (user_id, key)).fetchone()
    return json.loads(row[0]) if row else None


def kv_set(user_id: str, key: str, value) -> None:
    with _lock:
        c = _c()
        with c:
            if value is None:
                c.execute("DELETE FROM kv WHERE user_id=? AND key=?", (user_id, key))
            else:
                c.execute(
                    "INSERT INTO kv (user_id, key, value) VALUES (?,?,?) "
                    "ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value",
                    (user_id, key, json.dumps(value, ensure_ascii=False)),
                )


# ---------- 全域：擁有者、成員 ----------
def meta_get(key: str):
    with _lock:
        row = _c().execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def meta_set(key: str, value) -> None:
    with _lock:
        c = _c()
        with c:
            c.execute(
                "INSERT INTO meta (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value)),
            )


def list_users() -> list:
    with _lock:
        return [r[0] for r in _c().execute("SELECT id FROM users ORDER BY joined_at, id").fetchall()]


def add_user(user_id: str) -> None:
    with _lock:
        c = _c()
        with c:
            c.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))


# ---------- 一次性匯入舊的 JSON 檔（歸給擁有者）----------
def import_legacy(user_id: str, root: str, data_dir: str) -> bool:
    """把舊版 investments/items/milestones.json、state.json、calendars.json 匯入 user_id。只會執行一次。"""
    if meta_get("legacy_imported"):
        return False

    def read(path):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return None

    found = False
    for table in _LISTS:
        rows = read(os.path.join(root, f"{table}.json"))
        if rows and load_list(table, user_id) is None:
            save_list(table, user_id, rows)
            found = True
    if found:
        kv_set(user_id, "seeded", True)
    state = read(os.path.join(data_dir, "state.json")) or {}
    for key in ("conv", "session", "pending", "sent", "last_digest_day"):
        if state.get(key) is not None:
            kv_set(user_id, key, state[key])
    calendars = read(os.path.join(data_dir, "calendars.json"))
    if calendars and kv_get(user_id, "calendars") is None:
        kv_set(user_id, "calendars", calendars)
    meta_set("legacy_imported", True)
    return found
