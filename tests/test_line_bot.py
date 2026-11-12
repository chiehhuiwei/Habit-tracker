import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta

from line_bot import state
from line_bot.flows.pending import commit_if_stale
from line_bot.flows.router import handle_event
from line_bot.timefmt import TZ

BASE = {"source": {"userId": "U_owner"}, "replyToken": "r"}


def text(t):
    handle_event({**BASE, "type": "message", "message": {"type": "text", "text": t}})


def postback(data):
    handle_event({**BASE, "type": "postback", "postback": {"data": data}})


def last_text(sent):
    return sent[-1]["body"]["messages"][0]["text"]


def quick_labels(sent):
    return [i["action"]["label"] for i in sent[-1]["body"]["messages"][0].get("quickReply", {}).get("items", [])]


def rewind_session(minutes):
    session = state.get_session()
    session["start"] = (datetime.now(TZ) - timedelta(minutes=minutes)).isoformat()
    state.set_session(session)


def test_reading_flow_writes_one_bigquery_row(env):
    sent, bq, service = env["sent"], env["bq"], env["service"]
    postback("a=start")
    assert "要記錄什麼活動" in last_text(sent)
    assert "閱讀" in quick_labels(sent)

    reading = next(i for i in service.investments if i["name"] == "閱讀")
    postback(f"a=inv&id={reading['id']}")
    assert "請輸入書籍名稱" in last_text(sent)

    text("原子習慣")
    assert "總共幾頁" in last_text(sent)
    text("320")
    assert "開始記錄：閱讀《原子習慣》" in last_text(sent)

    rewind_session(45)
    postback("a=end")
    assert "已停止 閱讀《原子習慣》" in last_text(sent)
    assert "45 分" in last_text(sent)
    assert "共 320 頁" in last_text(sent)
    assert bq.rows == [], "收齊頁數與備註前不應寫入 BigQuery"

    text("160")
    assert "進度 50%" in last_text(sent)
    text("第三章 習慣堆疊")
    assert "已記錄 閱讀《原子習慣》" in last_text(sent)

    [row] = bq.rows
    assert row["habit_name"] == "閱讀"
    assert row["item_name"] == "原子習慣"
    assert row["detail"] == "讀至第 160 頁｜第三章 習慣堆疊"
    assert row["progress_snapshot"] == 0.5
    assert row["total_pages"] == 320
    assert 2690 <= row["duration_second"] <= 2710
    assert service.items[0]["progress"] == 0.5
    assert state.get_session() is None and state.get_pending() is None


def test_finishing_a_book_unlocks_milestone(env):
    sent, service = env["sent"], env["service"]
    reading = next(i for i in service.investments if i["name"] == "閱讀")
    postback(f"a=inv&id={reading['id']}")
    text("刻意練習")
    text("100")
    postback("a=end")
    text("100")
    postback("a=skip")
    assert "🏆 項目結清：《刻意練習》" in last_text(sent)
    assert service.items[0]["status"] == "completed"


def test_new_activity_keyword_asks_for_book(env):
    sent = env["sent"]
    postback("a=start")
    text("看書會")
    assert "請輸入書籍名稱" in last_text(sent)
    postback("a=skip")
    assert "開始記錄：看書會" in last_text(sent)


def test_abandoned_draft_is_committed(env):
    bq = env["bq"]
    postback("a=start")
    text("冥想")
    postback("a=end")
    assert bq.rows == []
    draft = state.get_pending()
    draft["end"] = (datetime.now(TZ) - timedelta(minutes=11)).isoformat()
    state.set_pending(draft)
    commit_if_stale()
    assert [r["habit_name"] for r in bq.rows] == ["冥想"]
    assert bq.rows[0]["detail"] == "專注投入"


def test_switching_action_commits_draft(env):
    bq = env["bq"]
    postback("a=start")
    text("冥想")
    postback("a=end")
    postback("a=stats")
    assert len(bq.rows) == 1


def test_ics_expands_recurring_and_detects_conflicts(env):
    from line_bot.calendar.events import conflict_uids, fetch_events

    start = datetime(2026, 11, 10, tzinfo=TZ)
    events = fetch_events(start, start + timedelta(days=14))
    summary = [(e["start"].strftime("%m-%d %H:%M"), e["title"]) for e in events]
    assert summary == [
        ("11-10 20:00", "English lesson"),
        ("11-12 20:00", "English lesson"),
        ("11-12 20:30", "Teach Amy"),
        ("11-19 21:00", "English lesson (moved)"),
    ]
    assert len(conflict_uids(events)) == 2


def test_reminder_pushes_once_and_starts_from_event(env):
    from line_bot.jobs.reminders import reminder_tick

    sent, bq = env["sent"], env["bq"]
    now = datetime(2026, 11, 12, 20, 20, tzinfo=TZ)
    reminder_tick(now, now - timedelta(minutes=1))
    reminder_tick(now, now - timedelta(minutes=1))
    pushes = [s for s in sent if s["path"] == "message/push"]
    assert len(pushes) == 1
    msg = pushes[0]["body"]["messages"][0]
    assert "10 分鐘後｜教英文" in msg["text"]

    postback(msg["quickReply"]["items"][0]["action"]["data"])
    assert "開始記錄：教英文" in last_text(sent)
    postback("a=end")
    assert "略過將沿用：Teach Amy" in last_text(sent)
    postback("a=skip")
    assert bq.rows[-1]["habit_name"] == "教英文"
    assert bq.rows[-1]["detail"] == "Teach Amy"


def test_webhook_signature(env):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from line_bot import worker
    from line_bot.routes import router

    app = FastAPI()
    app.include_router(router, prefix="/line")
    client = TestClient(app)
    body = json.dumps({"events": [{**BASE, "type": "postback", "postback": {"data": "a=help"}}]}).encode()
    good = base64.b64encode(hmac.new(b"test-secret", body, hashlib.sha256).digest()).decode()

    assert client.post("/line/webhook", content=body, headers={"x-line-signature": "bad"}).status_code == 401
    assert client.post("/line/webhook", content=body, headers={"x-line-signature": good}).status_code == 200
    worker.submit(lambda: None).result()
    assert "timeVest 使用方式" in last_text(env["sent"])
