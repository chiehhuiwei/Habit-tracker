from .. import ledger, state
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
    "help": lambda ev, p: reply(ev["replyToken"], help_message()),
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
    if not _is_owner(ev):
        return
    if ev["type"] == "message" and ev["message"]["type"] == "text":
        return _handle_text(ev)
    if ev["type"] == "postback":
        params = parse_postback(ev["postback"]["data"])
        return _run_action(params.get("a"), ev, params)
    if ev["type"] == "follow":
        reply(ev["replyToken"], [text_msg("歡迎使用 timeVest 時光投資簿 📈"), help_message()])


def _handle_text(ev: dict) -> None:
    text = ev["message"]["text"].strip()
    command = TEXT_COMMANDS.get(text)
    if command:
        return _run_action(command, ev, {})
    conv = state.get_conv()
    handler = conv and STEP_HANDLERS.get(conv["step"])
    if handler:
        return handler(ev["replyToken"], text, conv)
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


def _is_owner(ev: dict) -> bool:
    """未設定 LINE_OWNER_USER_ID 時，第一個傳訊息的人會被綁定為擁有者。"""
    user_id = (ev.get("source") or {}).get("userId")
    if not user_id:
        return False
    owner = state.get_owner_id()
    if not owner:
        state.set_owner_id(user_id)
        print(f"[LINE] 已綁定擁有者 {user_id}")
        return True
    if owner == user_id:
        return True
    if ev.get("replyToken"):
        reply(ev["replyToken"], text_msg("這是私人使用的帳號 🙏"))
    return False
