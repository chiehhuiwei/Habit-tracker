"""待寫入草稿：BigQuery 串流寫入後無法馬上 UPDATE，所以收齊頁數／備註後才一次寫入。"""
from datetime import timedelta

from .. import ledger, settings, state
from ..timefmt import now, parse_iso

END_STEPS = ("end_progress", "end_memo")


def commit_pending(memo=None):
    """寫入草稿；回傳 (成功, 草稿, 里程碑或錯誤)。沒有草稿時回傳 None。"""
    draft = state.get_pending()
    if not draft:
        return None
    final_memo = memo if memo is not None else draft.get("memo")
    ok, result = ledger.log_session(draft, final_memo)
    if not ok:
        print(f"[LINE] 寫入 BigQuery 失敗，保留草稿稍後重試：{result}")
        return False, draft, result
    state.set_pending(None)
    conv = state.get_conv()
    if conv and conv["step"] in END_STEPS:
        state.set_conv(None)
    return True, {**draft, "memo": final_memo}, result


def commit_if_stale() -> None:
    draft = state.get_pending()
    if draft and now() - parse_iso(draft["end"]) > timedelta(minutes=settings.PENDING_COMMIT_MIN):
        commit_pending()
