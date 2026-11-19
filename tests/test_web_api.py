from fastapi import FastAPI
from fastapi.testclient import TestClient

from timevest.web import auth
from timevest.web.routes import public, router


def make_client(monkeypatch, user="U_owner"):
    # token 形如 good:<userId>；單人測試的 "good" 代表擁有者
    def fake(token):
        if token == "good":
            return user
        return token.split(":", 1)[1] if token.startswith("good:") else None

    monkeypatch.setattr(auth, "_profile_user_id", fake)
    app = FastAPI()
    app.include_router(public, prefix="/api")
    app.include_router(router, prefix="/api")
    return TestClient(app)


H = {"Authorization": "Bearer good"}


def test_auth_required_and_owner_only(env, monkeypatch):
    c = make_client(monkeypatch)
    assert c.get("/api/healthz").status_code == 200
    assert c.get("/api/investments").status_code == 401
    assert c.get("/api/investments", headers={"Authorization": "Bearer bad"}).status_code == 401
    other = make_client(monkeypatch, user="U_someone_else")
    assert other.get("/api/investments", headers=H).status_code == 403


def test_timer_session_writes_one_row(env, monkeypatch):
    c = make_client(monkeypatch)
    reading = next(i for i in c.get("/api/investments", headers=H).json() if i["name"] == "閱讀")
    item = c.post("/api/items", headers=H, json={"investment_id": reading["id"], "name": "原子習慣", "total": 320}).json()
    assert c.post("/api/session/start", headers=H, json={"investment_id": reading["id"], "item_id": item["id"]}).status_code == 200
    assert c.post("/api/session/start", headers=H, json={"investment_id": reading["id"]}).status_code == 409
    r = c.post("/api/session/finish", headers=H, json={"progress_value": 160, "memo": "好書"})
    assert r.status_code == 200
    assert len(env["bq"].rows) == 1
    assert env["bq"].rows[0]["detail"] == "讀至第 160 頁｜好書"
    assert c.get("/api/items", headers=H, params={"investment_id": reading["id"]}).json()[0]["progress"] == 0.5
    assert c.get("/api/session", headers=H).json() is None


def test_manual_entry_and_validation(env, monkeypatch):
    c = make_client(monkeypatch)
    gym = next(i for i in c.get("/api/investments", headers=H).json() if i["name"] == "健身")
    bad = c.post("/api/activities", headers=H, json={"investment_id": gym["id"], "start": "2026-01-01T10:00", "end": "2026-01-01T09:00"})
    assert bad.status_code == 400
    ok = c.post("/api/activities", headers=H, json={"investment_id": gym["id"], "start": "2026-01-01T09:00", "end": "2026-01-01T10:00"})
    assert ok.status_code == 200
    assert env["bq"].rows[0]["duration_second"] == 3600


def test_members_have_separate_data(env, monkeypatch):
    """第二位成員有自己的帳戶／項目／計時，彼此看不到對方資料；非成員被擋。"""
    from timevest.core import service as tvs
    from timevest.line import users

    bq = env["bq"]
    factory_calls = []

    def factory(uid):
        factory_calls.append(uid)
        return tvs.TimeVestService(bq, "p.d.habit_logs", user_id=uid,
                                   legacy_owner=(uid == "U_owner"))

    monkeypatch.setattr(users, "_single", None)
    users.bind_factory(factory)
    users.add_member("U_friend")

    client = make_client(monkeypatch)
    O, F, X = ({"Authorization": f"Bearer good:{u}"} for u in ("U_owner", "U_friend", "U_stranger"))

    class As:
        def __init__(self, h):
            self.h = h

        def _kw(self, kw):
            kw["headers"] = self.h
            return kw

        def get(self, url, **kw): return client.get(url, **self._kw(kw))
        def post(self, url, **kw): return client.post(url, **self._kw(kw))
        def patch(self, url, **kw): return client.patch(url, **self._kw(kw))

    owner, friend, stranger = As(O), As(F), As(X)
    owner.post("/api/investments", json={"name": "游泳"})
    names_owner = [i["name"] for i in owner.get("/api/investments").json()]
    names_friend = [i["name"] for i in friend.get("/api/investments").json()]
    assert "游泳" in names_owner and "游泳" not in names_friend

    fav = friend.get("/api/investments").json()[0]
    assert friend.patch(f"/api/investments/{fav['id']}", json={"favorite": True}).json()["favorite"] is True
    assert not owner.get("/api/investments").json()[0].get("favorite")

    friend.post("/api/session/start", json={"investment_id": fav["id"]})
    assert owner.get("/api/session").json() is None
    assert friend.get("/api/session").json() is not None
    friend.post("/api/session/finish", json={})
    assert env["bq"].rows[-1]["user_id"] == "U_friend"

    assert stranger.get("/api/investments").status_code == 403
