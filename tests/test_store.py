import json

from timevest.core import store
from timevest.line import users


def test_lists_are_per_user_and_transactional():
    store.connect(":memory:")
    assert store.load_list("items", "A") is None
    store.save_list("items", "A", [{"id": "1", "name": "x"}, {"id": "2", "name": "y"}])
    store.save_list("items", "B", [{"id": "1", "name": "other"}])  # 不同使用者可有相同 id
    assert [r["name"] for r in store.load_list("items", "A")] == ["x", "y"]
    store.save_list("items", "A", [{"id": "2", "name": "y"}])  # 整份取代
    assert [r["name"] for r in store.load_list("items", "A")] == ["y"]
    assert [r["name"] for r in store.load_list("items", "B")] == ["other"]


def test_kv_and_members():
    store.connect(":memory:")
    store.kv_set("A", "session", {"k": 1})
    assert store.kv_get("A", "session") == {"k": 1} and store.kv_get("B", "session") is None
    store.kv_set("A", "session", None)
    assert store.kv_get("A", "session") is None
    users.add_member("U1")
    users.add_member("U1")
    assert store.list_users() == ["U1"]


def test_import_legacy_json_once(tmp_path):
    store.connect(":memory:")
    (tmp_path / "investments.json").write_text(json.dumps([{"id": "i1", "name": "閱讀"}]), encoding="utf-8")
    (tmp_path / "items.json").write_text(json.dumps([{"id": "t1", "name": "書", "investment_id": "i1"}]), encoding="utf-8")
    (tmp_path / "state.json").write_text(json.dumps({"session": {"start": "x"}, "owner": "U_o"}), encoding="utf-8")
    assert store.import_legacy("U_o", str(tmp_path), str(tmp_path)) is True
    assert store.load_list("investments", "U_o")[0]["name"] == "閱讀"
    assert store.kv_get("U_o", "session") == {"start": "x"}
    assert store.import_legacy("U_o", str(tmp_path), str(tmp_path)) is False  # 只匯入一次
