"""開始記錄：選活動 →（閱讀等）輸入書名 →（新書）總頁數 → 計時"""
from .. import ledger, state
from ..api import reply
from ..labels import elapsed_sec, session_label
from ..messages import MAX_QUICK_REPLIES, QR, postback_data, qr_postback, text_msg
from ..timefmt import fmt_duration, fmt_time, now, parse_iso


def begin_start(token: str) -> None:
    running = state.get_session()
    if running:
        return reply(token, running_notice(running))

    state.set_conv({"step": "pick_activity"})
    choices = [
        qr_postback(inv["name"], postback_data(a="inv", id=inv["id"]))
        for inv in ledger.list_investments()[: MAX_QUICK_REPLIES - 1]
    ]
    reply(token, text_msg("要記錄什麼活動？\n點選下方按鈕，或直接輸入新的活動名稱 ✍️", choices + [QR.cancel()]))


def on_activity_text(token: str, text: str, _state=None) -> None:
    on_activity_chosen(token, ledger.find_or_create_investment(text))


def on_activity_chosen(token: str, inv) -> None:
    if not inv:
        return reply(token, text_msg("找不到這個活動，請重新選擇", [QR.start()]))
    if not inv.get("item_label"):
        return start_now(token, investment_id=inv["id"])

    state.set_conv({"step": "pick_item", "investment_id": inv["id"]})
    label = inv["item_label"]
    choices = [
        qr_postback(it["name"], postback_data(a="item", id=it["id"]))
        for it in ledger.items_for(inv["id"])[: MAX_QUICK_REPLIES - 2]
    ]
    reply(token, text_msg(f"請輸入{label}名稱 📖\n或點選下方的{label}", choices + [QR.skip(), QR.cancel()]))


def on_item_chosen(token: str, item_id: str) -> None:
    item = ledger.get_item(item_id)
    if not item:
        return reply(token, text_msg("找不到這個項目，請重新開始", [QR.start()]))
    start_now(token, investment_id=item["investment_id"], item_id=item["id"])


def on_item_text(token: str, text: str, conv: dict) -> None:
    inv = ledger.get_investment(conv["investment_id"])
    item, created = ledger.find_or_create_item(inv["id"], text)
    if created and inv["progress_type"] == "pages":
        state.set_conv({"step": "item_total", "investment_id": inv["id"], "item_id": item["id"]})
        return reply(token, text_msg(f"新的{inv['item_label']}！《{item['name']}》總共幾頁？", [QR.skip()]))
    start_now(token, investment_id=inv["id"], item_id=item["id"])


def on_item_total_text(token: str, text: str, conv: dict) -> None:
    try:
        total = int(text)
    except ValueError:
        total = 0
    if total <= 0:
        return reply(token, text_msg("請輸入頁數（數字），或按略過", [QR.skip()]))
    ledger.set_item_total(conv["item_id"], total)
    start_now(token, investment_id=conv["investment_id"], item_id=conv["item_id"])


def skip_start_step(token: str, conv: dict) -> None:
    start_now(token, investment_id=conv["investment_id"], item_id=conv.get("item_id"))


def start_from_event(token: str, investment_name: str, title: str) -> None:
    """課前提醒的按鈕：直接開始，課程標題帶入備註。"""
    running = state.get_session()
    if running:
        return reply(token, running_notice(running))
    start_now(token, investment_id=ledger.find_or_create_investment(investment_name)["id"], memo=title)


def start_now(token: str, investment_id: str, item_id=None, memo=None) -> None:
    session = {"investment_id": investment_id, "item_id": item_id, "memo": memo, "start": now().isoformat()}
    state.set_session(session)
    state.set_conv(None)
    reply(
        token,
        text_msg(
            f"⏱ 開始記錄：{session_label(session)}\n開始時間 {fmt_time(parse_iso(session['start']))}\n完成後點選單「結束記錄」",
            [QR.end()],
        ),
    )


def running_notice(session: dict) -> dict:
    return text_msg(
        f"目前正在記錄 {session_label(session)}（已 {fmt_duration(elapsed_sec(session))}）\n要先結束嗎？", [QR.end()]
    )
