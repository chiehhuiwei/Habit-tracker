import time
from datetime import datetime, timedelta

import icalendar
import recurring_ical_events
import requests

from .. import settings
from ..timefmt import to_local

_cache: dict = {}  # url -> (fetched_at, Calendar)


def _load(url: str):
    hit = _cache.get(url)
    if hit and time.time() - hit[0] < settings.ICS_CACHE_SEC:
        return hit[1]
    res = requests.get(url, timeout=15)
    res.raise_for_status()
    cal = icalendar.Calendar.from_ical(res.content)
    _cache[url] = (time.time(), cal)
    return cal


def ics_events(url: str, start: datetime, end: datetime) -> list:
    """展開週期行程（RRULE / EXDATE / 單次改期）。"""
    events = []
    for comp in recurring_ical_events.of(_load(url)).between(start, end):
        raw_start = comp.get("DTSTART").dt
        all_day = not isinstance(raw_start, datetime)
        ev_start = to_local(raw_start)
        if comp.get("DTEND"):
            ev_end = to_local(comp.get("DTEND").dt)
        elif comp.get("DURATION"):
            ev_end = ev_start + comp.get("DURATION").dt
        else:
            ev_end = ev_start + (timedelta(days=1) if all_day else timedelta())
        events.append(
            {
                "id": str(comp.get("UID", "")),
                "title": str(comp.get("SUMMARY", "")) or "(無標題)",
                "start": ev_start,
                "end": ev_end,
                "all_day": all_day,
            }
        )
    return events
