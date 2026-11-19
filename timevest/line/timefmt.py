from datetime import date, datetime, timedelta

from .config import TZ

WEEKDAYS = "一二三四五六日"


def now() -> datetime:
    return datetime.now(TZ)


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(TZ)


def day_start(dt: datetime) -> datetime:
    return dt.astimezone(TZ).replace(hour=0, minute=0, second=0, microsecond=0)


def to_local(value) -> datetime:
    """icalendar 可能回傳 date、naive 或帶時區的 datetime，一律轉成台北時間。"""
    if isinstance(value, datetime):
        return value.replace(tzinfo=TZ) if value.tzinfo is None else value.astimezone(TZ)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=TZ)
    raise TypeError(f"unsupported date value: {value!r}")


def fmt_time(dt: datetime) -> str:
    return dt.astimezone(TZ).strftime("%H:%M")


def fmt_day(dt: datetime) -> str:
    d = dt.astimezone(TZ)
    return f"{d.month}/{d.day}（{WEEKDAYS[d.weekday()]}）"


def fmt_duration(sec: float) -> str:
    sec = int(sec)
    if sec < 60:
        return f"{sec} 秒"
    h, m = sec // 3600, (sec % 3600) // 60
    return f"{h} 小時 {m} 分" if h else f"{m} 分"


def fmt_hours(hours: float) -> str:
    return f"{hours:.1f} 小時"


def fmt_percent(ratio: float) -> str:
    return f"{round(ratio * 100)}%"


def seconds_between(start: datetime, end: datetime) -> int:
    return max(1, int((end - start).total_seconds()))


def add_days(dt: datetime, days: int) -> datetime:
    return dt + timedelta(days=days)
