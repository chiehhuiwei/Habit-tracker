"""LINE 與 TimeVestService 之間的轉接層：所有帳戶／項目／BigQuery 寫入都經過既有的 service。"""
from . import settings
from .timefmt import add_days, day_start, now, parse_iso, seconds_between

_service = None


def bind_service(service) -> None:
    global _service
    _service = service


def svc():
    if _service is None:
        raise RuntimeError("line_bot 尚未綁定 TimeVestService")
    return _service


# --- Investments ---
def list_investments() -> list:
    return svc().get_investments()


def get_investment(inv_id):
    return next((i for i in svc().investments if i["id"] == inv_id), None) if inv_id else None


def find_investment_by_name(name: str):
    target = name.strip()
    return next((i for i in svc().investments if i["name"] == target), None)


def find_or_create_investment(name: str):
    existing = find_investment_by_name(name)
    if existing:
        return existing
    preset = dict(settings.NEW_INVESTMENT_DEFAULT)
    for pattern, rule in settings.KEYWORD_RULES:
        if pattern.search(name):
            preset.update(rule)
            break
    return svc().add_investment(name.strip(), preset["icon"], preset["color"], preset["item_label"], preset["progress_type"])


# --- Items ---
def get_item(item_id):
    return next((it for it in svc().items if it["id"] == item_id), None) if item_id else None


def items_for(inv_id: str) -> list:
    """依 AGENTS.md 規則列出該帳戶所有項目（不只進行中），進行中的排前面。"""
    items = svc().get_items(inv_id=inv_id)
    return sorted(items, key=lambda it: it.get("status") != "inProgress")


def find_or_create_item(inv_id: str, name: str):
    clean = name.strip().lower()
    existed = any(it["investment_id"] == inv_id and it["name"].strip().lower() == clean for it in svc().items)
    return svc().add_item(inv_id, name), not existed


def set_item_total(item_id: str, total: float) -> None:
    item = get_item(item_id)
    svc().update_item_progress_and_total(item_id, (item.get("progress") or 0) * total, total_val=total)


# --- Activities ---
def build_detail(inv, draft: dict, memo) -> str:
    """與網頁版 settle_timer 相同格式：「讀至第 N 頁｜備註」。"""
    progress_text = ""
    value = draft.get("progress_value")
    if value is not None and inv["progress_type"] == "pages":
        progress_text = f"讀至第 {int(value)} 頁"
    elif value is not None and inv["progress_type"] == "percentage":
        progress_text = f"進度更新至 {int(value)}%"
    parts = [p for p in (progress_text, memo) if p]
    return "｜".join(parts) or "專注投入"


def log_session(draft: dict, memo):
    """寫入 BigQuery，回傳 (成功與否, 新里程碑或錯誤訊息)。"""
    inv = get_investment(draft["investment_id"])
    start, end = parse_iso(draft["start"]), parse_iso(draft["end"])
    return svc().log_activity(
        inv_id=inv["id"],
        item_id=draft.get("item_id"),
        duration_seconds=seconds_between(start, end),
        detail=build_detail(inv, draft, memo),
        start_time=start,
        end_time=end,
        progress_snapshot=draft.get("progress"),
    )


# --- Stats（BigQuery）---
def hours_by_name(days_back=None) -> dict:
    kwargs = {}
    if days_back is not None:
        today = day_start(now())
        kwargs = {"start_date": add_days(today, -days_back).date().isoformat(), "end_date": today.date().isoformat()}
    return {row["name"]: row["hours"] for row in svc().get_allocation(**kwargs)}


def streak_days() -> int:
    return svc().calculate_streak()
