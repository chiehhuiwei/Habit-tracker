from . import ledger
from .timefmt import now, parse_iso


def activity_label(inv, item=None) -> str:
    if not inv:
        return "未知活動"
    return f"{inv['name']}《{item['name']}》" if item else inv["name"]


def session_label(session: dict) -> str:
    return activity_label(ledger.get_investment(session["investment_id"]), ledger.get_item(session.get("item_id")))


def elapsed_sec(session: dict) -> int:
    return int((now() - parse_iso(session["start"])).total_seconds())
