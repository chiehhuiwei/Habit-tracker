"""測試環境：LINE 設定指向暫存資料夾、BigQuery 用假的 client、對外 HTTP 全部攔截。"""
import json
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp(prefix="timevest-line-"))
ICS_URL = "https://cal.test/teach.ics"
os.environ.update(
    LINE_CHANNEL_SECRET="test-secret",
    LINE_CHANNEL_ACCESS_TOKEN="test-token",
    LINE_OWNER_USER_ID="U_owner",
    LINE_DATA_DIR=str(TMP / "line_data"),
    LINE_CALENDARS_FILE=str(TMP / "calendars.json"),
)
(TMP / "calendars.json").write_text(
    json.dumps([{"key": "teach", "label": "教英文", "emoji": "🧑‍🏫", "url": ICS_URL, "investment": "教英文"}]),
    encoding="utf-8",
)


class FakeBigQuery:
    def __init__(self):
        self.rows = []

    def insert_rows_json(self, _table, rows):
        self.rows.extend(rows)
        return []

    def query(self, sql):
        return _FakeJob(self.rows, sql)


class _FakeJob:
    def __init__(self, rows, sql):
        self.rows, self.sql = rows, sql

    def to_dataframe(self):
        df = pd.DataFrame(self.rows or [], columns=["habit_name", "start_time", "duration_second"])
        if "GROUP BY habit_name" in self.sql:
            return df.groupby("habit_name", as_index=False)["duration_second"].sum().rename(
                columns={"duration_second": "total_sec"}
            )
        if "DISTINCT DATE" in self.sql:
            dates = sorted({r["start_time"][:10] for r in self.rows}, reverse=True)
            return pd.DataFrame({"date": dates})
        return pd.DataFrame()


class FakeResponse:
    def __init__(self, status=200, content=b""):
        self.status_code, self.content, self.text = status, content, content.decode()

    def raise_for_status(self):
        pass


@pytest.fixture
def env(monkeypatch):
    import timevest_service as tvs

    for name in ("INVESTMENTS_FILE", "ITEMS_FILE", "MILESTONES_FILE"):
        monkeypatch.setattr(tvs, name, str(TMP / f"{name.lower()}.json"))
        Path(getattr(tvs, name)).unlink(missing_ok=True)
    state_file = TMP / "line_data" / "state.json"
    state_file.unlink(missing_ok=True)

    from line_bot import api, ledger, state
    from line_bot.calendar import ics

    bq = FakeBigQuery()
    service = tvs.TimeVestService(bq, "p.d.habit_logs")
    ledger.bind_service(service)
    state.ensure_data_dir()

    sent = []
    monkeypatch.setattr(api.requests, "post", lambda url, json, **_: sent.append({"path": url.split("/bot/")[1], "body": json}) or FakeResponse())
    ics_body = (ROOT / "tests" / "fixtures" / "sample.ics").read_bytes()
    monkeypatch.setattr(ics.requests, "get", lambda url, **_: FakeResponse(content=ics_body))
    ics._cache.clear()
    return {"service": service, "bq": bq, "sent": sent}
