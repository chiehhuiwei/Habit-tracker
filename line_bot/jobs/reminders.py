import time
from datetime import datetime, timedelta

from .. import ledger, settings, state
from ..api import push
from ..calendar.events import fetch_events
from ..labels import elapsed_sec, session_label
from ..messages import QR, postback_data, qr_postback, text_msg, truncate
from ..timefmt import day_start, fmt_duration, fmt_time
from ..views.schedule import build_schedule

SENT_TTL_SEC = 2 * 24 * 3600


def reminder_tick(now: datetime, last_tick: datetime) -> None:
    """last_tick：上次執行時間，用來抓這段期間剛結束的行程。"""
    horizon = now + timedelta(minutes=settings.REMIND_BEFORE_MIN)
    sent = _prune(state.get_sent())
    session = state.get_session()

    for ev in fetch_events(last_tick, horizon):
        if ev["all_day"]:
            continue
        if now < ev["start"] <= horizon:
            _notify_once(sent, f"pre:{ev['uid']}", lambda ev=ev: _push_upcoming(ev, now))
        if settings.PROMPT_END_AFTER_EVENT and last_tick < ev["end"] <= now and _is_recording(session, ev):
            _notify_once(sent, f"end:{ev['uid']}", lambda ev=ev: _push_event_ended(ev))

    if session and elapsed_sec(session) > settings.LONG_SESSION_HOURS * 3600:
        _notify_once(sent, f"long:{session['start']}", lambda: _push_long_session(session))
    state.set_sent(sent)


def daily_digest_tick(now: datetime) -> None:
    today = now.date().isoformat()
    if now.hour != settings.DAILY_DIGEST_HOUR or state.get_last_digest_day() == today:
        return
    state.set_last_digest_day(today)
    events, message = build_schedule("☀️ 早安！今日行程", day_start(now), 1)
    if events or settings.DIGEST_WHEN_EMPTY:
        push(message)


def _push_upcoming(ev: dict, now: datetime) -> None:
    mins = max(1, round((ev["start"] - now).total_seconds() / 60))
    investment = ev["cal"]["investment"]
    start_btn = qr_postback(
        "▶ 開始記錄這堂", postback_data(a="evStart", inv=investment, t=truncate(ev["title"], 40)), f"開始記錄：{investment}"
    )
    text = "\n".join(
        [f"{ev['cal']['emoji']} {mins} 分鐘後｜{ev['cal']['label']}", ev["title"],
         f"🕒 {fmt_time(ev['start'])}–{fmt_time(ev['end'])}"]
    )
    push(text_msg(text, [start_btn]))


def _push_event_ended(ev: dict) -> None:
    push(text_msg(f"{ev['cal']['emoji']} {ev['cal']['label']}「{ev['title']}」結束了\n要結束這次記錄嗎？", [QR.end()]))


def _push_long_session(session: dict) -> None:
    push(text_msg(f"⏳ {session_label(session)} 已記錄 {fmt_duration(elapsed_sec(session))}\n是不是忘了按結束？", [QR.end()]))


def _is_recording(session, ev: dict) -> bool:
    inv = ledger.get_investment(session["investment_id"]) if session else None
    return bool(inv) and inv["name"] == ev["cal"]["investment"]


def _notify_once(sent: dict, key: str, send) -> None:
    if key in sent:
        return
    send()
    sent[key] = time.time()


def _prune(sent: dict) -> dict:
    cutoff = time.time() - SENT_TTL_SEC
    return {k: v for k, v in sent.items() if v >= cutoff}
