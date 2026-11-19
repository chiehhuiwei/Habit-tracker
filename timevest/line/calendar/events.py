from datetime import datetime

from .ics import ics_events
from .sources import load_calendar_sources


def fetch_events(start: datetime, end: datetime) -> list:
    """合併所有行事曆，每筆：{uid, id, title, start, end, all_day, cal}"""
    merged = []
    for cal in load_calendar_sources():
        try:
            for ev in ics_events(cal["url"], start, end):
                ev.update(cal=cal, uid=f"{cal['key']}:{ev['id']}:{int(ev['start'].timestamp())}")
                merged.append(ev)
        except Exception as e:
            print(f"[calendar] 讀取失敗：{cal.get('label')} {e}")
    merged = [e for e in merged if e["start"] < end and e["end"] > start]
    return sorted(merged, key=lambda e: e["start"])


def conflict_uids(events: list) -> set:
    timed = [e for e in events if not e["all_day"]]
    uids = set()
    for i, a in enumerate(timed):
        for b in timed[i + 1 :]:
            if a["start"] < b["end"] and b["start"] < a["end"]:
                uids.update((a["uid"], b["uid"]))
    return uids
