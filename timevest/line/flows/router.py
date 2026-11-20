from .. import config, ledger, state, users
from ..api import reply
from ..messages import help_message, parse_postback, text_msg
from ..views.schedule import reply_today_schedule, reply_week_schedule
from ..views.stats import reply_accounts, reply_today_stats
from .end import begin_end, on_memo_text, on_progress_text, skip_end_step
from .pending import commit_pending
from .start import (
    begin_start,
    on_activity_chosen,
    on_activity_text,
    on_item_chosen,
    on_item_text,
    on_item_total_text,
    on_quick_start,
    skip_start_step,
    start_from_event,
)


def _cancel(ev, _p):
    state.set_conv(None)
    reply(ev["replyToken"], text_msg("已取消 👌"))


ACTIONS = {
    "start": lambda ev, p: begin_start(ev["replyToken"]),
    "end": lambda ev, p: begin_end(ev["replyToken"]),
    "today": lambda ev, p: reply_today_schedule(ev["replyToken"]),
    "week": lambda ev, p: reply_week_schedule(ev["replyToken"]),
    "stats": lambda ev, p: reply_today_stats(ev["replyToken"]),
    "accounts": lambda ev, p: reply_accounts(ev["replyToken"]),
    "remind_cfg": lambda ev, p: _reply_cal_help(ev["replyToken"]),
    "bind_cal": lambda ev, p: _reply_cal_help(ev["replyToken"]),
    "help": lambda ev, p: reply(ev["replyToken"], help_message()),
    "tab_invest": lambda ev, p: None,
    "tab_schedule": lambda ev, p: None,
    "cancel": _cancel,
    "inv": lambda ev, p: on_activity_chosen(ev["replyToken"], ledger.get_investment(p.get("id"))),
    "item": lambda ev, p: on_item_chosen(ev["replyToken"], p.get("id")),
    "evStart": lambda ev, p: start_from_event(ev["replyToken"], p.get("inv", ""), p.get("t", "")),
    "skip": lambda ev, p: _on_skip(ev["replyToken"]),
}

TEXT_COMMANDS = {
    "開始": "start", "開始記錄": "start",
    "結束": "end", "結束記錄": "end",
    "行程": "today", "今日行程": "today", "本週行程": "week",
    "統計": "stats", "今日統計": "stats",
    "帳戶": "accounts", "我的帳戶": "accounts",
    "取消": "cancel", "說明": "help", "help": "help",
}

STEP_HANDLERS = {
    "pick_activity": on_activity_text,
    "pick_item": on_item_text,
    "item_total": on_item_total_text,
    "end_progress": on_progress_text,
    "end_memo": on_memo_text,
}

SKIP_HANDLERS = {
    "pick_item": skip_start_step,
    "item_total": skip_start_step,
    "end_progress": skip_end_step,
    "end_memo": skip_end_step,
}


def handle_event(ev: dict) -> None:
    user_id = _authorize(ev)
    if not user_id:
        return
    with users.use(user_id):
        _dispatch(ev)


def _dispatch(ev: dict) -> None:
    if ev["type"] == "message" and ev["message"]["type"] == "text":
        return _handle_text(ev)
    if ev["type"] == "postback":
        params = parse_postback(ev["postback"]["data"])
        return _run_action(params.get("a"), ev, params)
    if ev["type"] == "follow":
        reply(ev["replyToken"], [text_msg("歡迎使用 timeVest 時光投資簿 📈"), help_message()])


def _reply_cal_help(token):
    from ..api import reply
    from ..messages import text_msg, QR
    msg = """📅 綁定個人手機行事曆（iPhone / Google 日曆）

1. 打開 iPhone「行事曆」App ➔ 點下方「行事曆」
2. 在想同步的日曆旁點 ℹ️ ➔ 開啟「公開行事曆」
3. 點「共享連結」複製網址（webcal://...）
4. 直接傳送該網址給我即可綁定！

也可以開啟 LIFF「行程管理」頁面進行設定 ✨"""
    reply(token, text_msg(msg, [QR.start()]))

def _handle_text(ev: dict) -> None:
    text = ev["message"]["text"].strip()
    # 偵測是否傳送了行事曆 URL (webcal:// 或包含 .ics 或 p*-caldav.icloud.com)
    if text.startswith("webcal://") or ".ics" in text or "icloud.com/published" in text:
        from ..calendar.sources import load_calendar_sources, save_calendar_sources
        clean_url = text.strip()
        if clean_url.startswith("webcal://"):
            clean_url = "https://" + clean_url[9:]
        sources = load_calendar_sources()
        import uuid
        sources.append({
            "key": f"cal_{uuid.uuid4().hex[:8]}",
            "label": "iPhone個人行事曆",
            "emoji": "📱",
            "url": clean_url,
            "investment": "個人成長"
        })
        save_calendar_sources(users.current(), sources)
        from ..api import reply
        from ..messages import text_msg, QR
        msg = "✅ 成功綁定 iPhone 行事曆！\n未來每天早上 08:00 與課前 15 分鐘將為你推播提醒 🔔"
        return reply(ev["replyToken"], text_msg(msg, [QR.start()]))

    command = TEXT_COMMANDS.get(text)
    if command:
        return _run_action(command, ev, {})
    conv = state.get_conv()
    handler = conv and STEP_HANDLERS.get(conv["step"])
    if handler:
        return handler(ev["replyToken"], text, conv)
    if text.startswith("開始 ") and text[3:].strip():
        commit_pending()
        return on_quick_start(ev["replyToken"], text[3:].strip())
    reply(ev["replyToken"], help_message())


def _run_action(name, ev: dict, params: dict) -> None:
    action = ACTIONS.get(name)
    if not action:
        return
    # 使用者跳去做別的事（含取消）時，先把還沒填完的草稿寫入，時間不會遺失
    if name != "skip":
        commit_pending()
    action(ev, params)


def _on_skip(token: str) -> None:
    conv = state.get_conv()
    handler = conv and SKIP_HANDLERS.get(conv["step"])
    if handler:
        return handler(token, conv)
    reply(token, text_msg("目前沒有需要略過的步驟"))


def _authorize(ev: dict):
    """回傳可使用的 userId；非成員可用邀請碼（LINE_INVITE_CODE）加入。第一位使用者在未設定擁有者時成為擁有者。"""
    user_id = (ev.get("source") or {}).get("userId")
    if not user_id:
        return None
    if not users.owner_id():
        users.set_owner_id(user_id)
        print(f"[LINE] 已綁定擁有者 {user_id}")
        return user_id
    if users.is_member(user_id):
        return user_id
    token = ev.get("replyToken")
    if not token:
        return None
    text = ev["message"]["text"].strip() if ev["type"] == "message" and ev["message"]["type"] == "text" else ""
    if config.INVITE_CODE and text == config.INVITE_CODE:
        users.add_member(user_id)
        with users.use(user_id):
            reply(token, [text_msg("歡迎加入 timeVest 時光投資簿 📈"), help_message()])
        return None
    reply(token, text_msg("請輸入邀請碼才能使用 🔑" if config.INVITE_CODE else "這是私人使用的帳號 🙏"))
    return None
