"""LIFF 用的 REST API。所有資料操作都經 timevest.line.ledger（唯一碰 TimeVestService 的地方）。"""
import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from timevest.line import config, ledger, state
from timevest.line.timefmt import now

from .auth import require_member

public = APIRouter()
router = APIRouter(dependencies=[Depends(require_member)])


@public.get("/config")
def get_config():
    return {"liffId": config.LIFF_ID}


@public.get("/healthz")
def healthz():
    return {"ok": True}


# ---------- 帳戶 ----------
class InvestmentIn(BaseModel):
    name: str


@router.get("/investments")
def list_investments():
    return ledger.list_investments()


@router.post("/investments")
def add_investment(body: InvestmentIn):
    if not body.name.strip():
        raise HTTPException(400, "名稱不可為空")
    return ledger.find_or_create_investment(body.name)


class FavoriteIn(BaseModel):
    favorite: bool


@router.patch("/investments/{inv_id}")
def set_favorite(inv_id: str, body: FavoriteIn):
    if not ledger.svc().set_favorite(inv_id, body.favorite):
        raise HTTPException(404, "帳戶不存在")
    return ledger.get_investment(inv_id)


@router.delete("/investments/{inv_id}")
def delete_investment(inv_id: str):
    if not ledger.get_investment(inv_id):
        raise HTTPException(404, "帳戶不存在")
    ledger.svc().delete_investment(inv_id)
    return {"ok": True}


# ---------- 項目 ----------
class ItemIn(BaseModel):
    investment_id: str
    name: str
    total: Optional[float] = None


class ItemUpdate(BaseModel):
    current: Optional[float] = None
    total: Optional[float] = None
    status: Optional[str] = None


@router.get("/items")
def list_items(investment_id: str):
    return ledger.items_for(investment_id)


@router.post("/items")
def add_item(body: ItemIn):
    if not ledger.get_investment(body.investment_id):
        raise HTTPException(404, "帳戶不存在")
    if not body.name.strip():
        raise HTTPException(400, "名稱不可為空")
    item, _ = ledger.find_or_create_item(body.investment_id, body.name)
    if body.total:
        ledger.set_item_total(item["id"], body.total)
    return ledger.get_item(item["id"])


@router.patch("/items/{item_id}")
def update_item(item_id: str, body: ItemUpdate):
    item = ledger.get_item(item_id)
    if not item:
        raise HTTPException(404, "項目不存在")
    current = body.current if body.current is not None else _current_value(item)
    ok, msg = ledger.svc().update_item_progress_and_total(item_id, current, total_val=body.total, status=body.status)
    if not ok:
        raise HTTPException(400, msg)
    return ledger.get_item(item_id)


@router.delete("/items/{item_id}")
def delete_item(item_id: str):
    ledger.svc().delete_item(item_id)
    return {"ok": True}


def _current_value(item) -> float:
    inv = ledger.get_investment(item["investment_id"])
    progress = item.get("progress") or 0
    if inv and inv["progress_type"] == "pages":
        return progress * (item.get("total") or 0)
    return progress * 100


# ---------- 計時（與 LINE 共用同一個 session）----------
class SessionStart(BaseModel):
    investment_id: str
    item_id: Optional[str] = None
    memo: Optional[str] = None


class SessionFinish(BaseModel):
    progress_value: Optional[float] = None
    memo: Optional[str] = None


@router.get("/session")
def get_session():
    return state.get_session()


@router.post("/session/start")
def start_session(body: SessionStart):
    if state.get_session():
        raise HTTPException(409, "已有進行中的記錄")
    if not ledger.get_investment(body.investment_id):
        raise HTTPException(404, "帳戶不存在")
    session = {"investment_id": body.investment_id, "item_id": body.item_id, "memo": body.memo,
               "start": now().isoformat()}
    state.set_session(session)
    return session


@router.post("/session/cancel")
def cancel_session():
    state.set_session(None)
    return {"ok": True}


@router.post("/session/finish")
def finish_session(body: SessionFinish):
    session = state.get_session()
    if not session:
        raise HTTPException(404, "沒有進行中的記錄")
    draft = {**session, "end": now().isoformat(), "progress_value": body.progress_value}
    inv = ledger.get_investment(session["investment_id"])
    item = ledger.get_item(session.get("item_id"))
    if body.progress_value is not None and item:
        if inv["progress_type"] == "pages" and item.get("total"):
            draft["progress"] = min(body.progress_value / item["total"], 1.0)
        elif inv["progress_type"] == "percentage":
            draft["progress"] = min(body.progress_value / 100.0, 1.0)
    ok, result = ledger.log_session(draft, body.memo or session.get("memo"))
    if not ok:
        raise HTTPException(500, str(result))
    state.set_session(None)
    return {"ok": True, "milestones": result}


# ---------- 手動補記 ----------
class ManualIn(BaseModel):
    investment_id: str
    item_id: Optional[str] = None
    start: str  # ISO 8601
    end: str
    progress_value: Optional[float] = None
    memo: Optional[str] = None


@router.post("/activities")
def add_manual(body: ManualIn):
    inv = ledger.get_investment(body.investment_id)
    if not inv:
        raise HTTPException(404, "帳戶不存在")
    try:
        start = datetime.datetime.fromisoformat(body.start)
        end = datetime.datetime.fromisoformat(body.end)
    except ValueError:
        raise HTTPException(400, "時間格式錯誤")
    if start.tzinfo is None:
        start = start.replace(tzinfo=config.TZ)
    if end.tzinfo is None:
        end = end.replace(tzinfo=config.TZ)
    if end <= start:
        raise HTTPException(400, "結束時間必須晚於開始時間")
    draft = {"investment_id": inv["id"], "item_id": body.item_id, "start": start.isoformat(),
             "end": end.isoformat(), "progress_value": body.progress_value}
    item = ledger.get_item(body.item_id)
    if body.progress_value is not None and item:
        if inv["progress_type"] == "pages" and item.get("total"):
            draft["progress"] = min(body.progress_value / item["total"], 1.0)
        elif inv["progress_type"] == "percentage":
            draft["progress"] = min(body.progress_value / 100.0, 1.0)
    ok, result = ledger.log_session(draft, body.memo)
    if not ok:
        raise HTTPException(500, str(result))
    return {"ok": True, "milestones": result}


# ---------- 統計 ----------
@router.get("/stats")
def stats(days: Optional[int] = None):
    svc = ledger.svc()
    summary = svc.get_portfolio_summary()
    kwargs = {}
    if days:
        today = now().date()
        kwargs = {"start_date": (today - datetime.timedelta(days=days)).isoformat(), "end_date": today.isoformat()}
    return {"summary": summary, "allocation": svc.get_allocation(**kwargs), "milestones": svc.milestones[-20:][::-1]}


@router.get("/activities")
def history(investment_id: str, start_date: str, end_date: str):
    inv = ledger.get_investment(investment_id)
    if not inv:
        raise HTTPException(404, "帳戶不存在")
    return ledger.svc().get_activities_by_range(start_date, end_date, inv["name"])


@router.delete("/activities/{row_id}")
def delete_activity(row_id: str, start_date: str):
    ok, msg = ledger.svc().delete_historical_activity(row_id, start_date)
    if not ok:
        raise HTTPException(500, msg)
    return {"ok": True}

# ---------- 行事曆（iPhone / Google 日曆 iCal 綁定）----------
class CalendarIn(BaseModel):
    label: str
    url: str
    investment: Optional[str] = None
    emoji: Optional[str] = "📱"


@router.get("/calendars")
def get_user_calendars():
    from timevest.line.calendar.sources import load_calendar_sources
    return load_calendar_sources()


@router.post("/calendars")
def save_user_calendar(body: CalendarIn):
    from timevest.line.calendar.sources import load_calendar_sources, save_calendar_sources
    from timevest.line import users
    import uuid

    clean_url = body.url.strip()
    if clean_url.startswith("webcal://"):
        clean_url = "https://" + clean_url[9:]
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        raise HTTPException(400, "行事曆網址格式不正確（需為 https:// 或 webcal://）")

    sources = load_calendar_sources()
    # 檢查是否已存在相同 url
    existing = next((c for c in sources if c.get("url") == clean_url), None)
    if existing:
        existing["label"] = body.label.strip() or existing.get("label", "個人行事曆")
        existing["investment"] = body.investment.strip() if body.investment else existing.get("investment")
        existing["emoji"] = body.emoji or "📱"
    else:
        sources.append({
            "key": f"cal_{uuid.uuid4().hex[:8]}",
            "label": body.label.strip() or "iPhone行事曆",
            "emoji": body.emoji or "📱",
            "url": clean_url,
            "investment": body.investment.strip() if body.investment else "個人成長"
        })
    save_calendar_sources(users.current(), sources)
    return {"ok": True, "calendars": sources}


@router.delete("/calendars/{key}")
def delete_user_calendar(key: str):
    from timevest.line.calendar.sources import load_calendar_sources, save_calendar_sources
    from timevest.line import users

    sources = [c for c in load_calendar_sources() if c.get("key") != key]
    save_calendar_sources(users.current(), sources)
    return {"ok": True, "calendars": sources}
