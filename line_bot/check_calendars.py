"""python -m line_bot.check_calendars：列出未來 7 天合併後的行程，確認行事曆讀得到。"""
from .calendar.events import conflict_uids, fetch_events
from .calendar.sources import load_calendar_sources
from .timefmt import add_days, day_start, fmt_day, fmt_time, now


def main() -> None:
    start = day_start(now())
    events = fetch_events(start, add_days(start, 7))
    conflicts = conflict_uids(events)
    for cal in load_calendar_sources():
        count = sum(1 for e in events if e["cal"]["key"] == cal["key"])
        print(f"{cal['emoji']} {cal['label']}：{count} 筆")
    print()
    for ev in events:
        mark = "⚠️ " if ev["uid"] in conflicts else "   "
        when = "全天       " if ev["all_day"] else f"{fmt_time(ev['start'])}–{fmt_time(ev['end'])}"
        print(f"{mark}{fmt_day(ev['start'])} {when} {ev['cal']['emoji']} {ev['title']}")


if __name__ == "__main__":
    main()
