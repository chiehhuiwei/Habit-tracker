from .. import ledger, state
from ..api import reply
from ..labels import elapsed_sec, session_label
from ..messages import QR, text_msg
from ..timefmt import fmt_day, fmt_duration, fmt_hours, fmt_percent, now


def reply_today_stats(token: str) -> None:
    today = ledger.hours_by_name(days_back=0)
    week_hours = sum(ledger.hours_by_name(days_back=6).values())
    lines = [f"📊 今日統計 {fmt_day(now())}", "", f"⏱ 今日投入 {fmt_duration(sum(today.values()) * 3600)}"]
    for name, hours in sorted(today.items(), key=lambda kv: -kv[1]):
        lines.append(f"・{name} {fmt_duration(hours * 3600)}")
    lines += ["", f"📆 近 7 天 {fmt_hours(week_hours)}", f"🔥 連續 {ledger.streak_days()} 天"]

    session = state.get_session()
    if session:
        lines += ["", f"🟢 進行中：{session_label(session)}（已 {fmt_duration(elapsed_sec(session))}）"]
    reply(token, text_msg("\n".join(lines), [QR.end() if session else QR.start()]))


def reply_accounts(token: str) -> None:
    hours = ledger.hours_by_name()
    lines = ["💰 我的帳戶", ""]
    for inv in ledger.list_investments():
        lines.append(f"{inv['name']}　{fmt_hours(hours.get(inv['name'], 0))}")
        for it in ledger.items_for(inv["id"]):
            if it.get("status") == "inProgress":
                lines.append(f"　└ {it['name']} {fmt_percent(it.get('progress') or 0)}")
    reply(token, text_msg("\n".join(lines), [QR.start(), QR.stats()]))
