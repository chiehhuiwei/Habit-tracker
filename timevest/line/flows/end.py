"""結束記錄：停止計時 → 問頁數／進度 → 問備註 → 一次寫入 BigQuery"""
from .. import ledger, state
from ..api import reply
from ..labels import activity_label
from ..messages import QR, text_msg
from ..timefmt import fmt_duration, fmt_hours, fmt_percent, fmt_time, now, parse_iso, seconds_between
from .pending import commit_pending


def begin_end(token: str) -> None:
    session = state.get_session()
    if not session:
        return reply(token, text_msg("目前沒有進行中的記錄", [QR.start()]))
    commit_pending()  # 上一筆沒回覆完的草稿先寫入

    draft = {**session, "end": now().isoformat()}
    state.set_session(None)
    state.set_pending(draft)

    inv = ledger.get_investment(draft["investment_id"])
    item = ledger.get_item(draft.get("item_id"))
    head = f"⏹ 已停止 {activity_label(inv, item)}\n⏱ {time_range(draft)}"
    question = progress_question(inv, item)
    if not question:
        return ask_memo(token, draft, head)
    state.set_conv({"step": "end_progress"})
    reply(token, text_msg(f"{head}\n\n{question}", [QR.skip()]))


def progress_question(inv, item):
    if not item:
        return None
    if inv["progress_type"] == "pages" and item.get("total"):
        return f"📖 讀到第幾頁了？（共 {int(item['total'])} 頁）"
    if inv["progress_type"] == "percentage":
        return "📈 完成度大約幾 %？"
    return None


def on_progress_text(token: str, text: str, _conv=None) -> None:
    try:
        value = float(text)
    except ValueError:
        return reply(token, text_msg("請輸入數字，或按略過", [QR.skip()]))

    draft = state.get_pending()
    inv = ledger.get_investment(draft["investment_id"])
    item = ledger.get_item(draft["item_id"])
    ratio = value / float(item["total"]) if inv["progress_type"] == "pages" else value / 100
    draft.update(progress=min(max(ratio, 0.0), 1.0), progress_value=value)
    state.set_pending(draft)
    ask_memo(token, draft, f"📈 進度 {fmt_percent(draft['progress'])}")


def ask_memo(token: str, draft: dict, head: str) -> None:
    state.set_conv({"step": "end_memo"})
    hint = f"\n（略過將沿用：{draft['memo']}）" if draft.get("memo") else ""
    reply(token, text_msg(f"{head}\n\n✍️ 有想記下的備註嗎？例如章節、心得{hint}", [QR.skip()]))


def on_memo_text(token: str, text: str, _conv=None) -> None:
    finish(token, memo=text)


def skip_end_step(token: str, conv: dict) -> None:
    if conv["step"] == "end_progress":
        return ask_memo(token, state.get_pending(), "👌 進度略過")
    finish(token, memo=None)


def finish(token: str, memo) -> None:
    result = commit_pending(memo)
    if result is None:
        return reply(token, text_msg("這筆記錄已經儲存過了 👌", [QR.start()]))
    ok, draft, detail = result
    if not ok:
        return reply(token, text_msg("⚠️ 寫入資料庫失敗，稍後會自動重試", [QR.start()]))

    inv = ledger.get_investment(draft["investment_id"])
    item = ledger.get_item(draft.get("item_id"))
    lines = [f"✅ 已記錄 {activity_label(inv, item)}", f"⏱ {time_range(draft)}"]
    lines.append(f"📝 {ledger.build_detail(inv, draft, draft.get('memo'))}")
    lines += [f"🏆 {m['title']}" for m in detail or []]
    lines.append(f"☀️ 今日共投入 {fmt_hours(sum(ledger.hours_by_name(days_back=0).values()))}")
    reply(token, text_msg("\n".join(lines), [QR.start(), QR.stats()]))


def time_range(draft: dict) -> str:
    start, end = parse_iso(draft["start"]), parse_iso(draft["end"])
    return f"{fmt_time(start)}–{fmt_time(end)}（{fmt_duration(seconds_between(start, end))}）"
