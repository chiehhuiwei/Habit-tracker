from datetime import datetime

from ..api import reply
from ..calendar.events import conflict_uids, fetch_events
from ..calendar.sources import load_calendar_sources
from ..messages import QR, flex_msg, text_msg
from ..timefmt import add_days, day_start, fmt_day, now
from .schedule_flex import schedule_bubble


def reply_today_schedule(token: str) -> None:
    reply(token, build_schedule("📅 今日行程", day_start(now()), 1)[1])


def reply_week_schedule(token: str) -> None:
    reply(token, build_schedule("📆 未來 7 天行程", day_start(now()), 7)[1])


def build_schedule(title: str, start: datetime, days: int):
    """回傳 (events, message)。"""
    events = fetch_events(start, add_days(start, days))
    if not events:
        return events, text_msg(f"{title}\n沒有排程，好好投資自己的時間吧 ✨", [QR.start()])
    bubble = schedule_bubble(title, _group_by_day(events), conflict_uids(events), load_calendar_sources())
    return events, flex_msg(title, bubble)


def _group_by_day(events: list) -> list:
    groups = []
    for ev in events:
        key = ev["start"].date()
        if groups and groups[-1]["key"] == key:
            groups[-1]["events"].append(ev)
        else:
            groups.append({"key": key, "label": fmt_day(ev["start"]), "events": [ev]})
    return groups
