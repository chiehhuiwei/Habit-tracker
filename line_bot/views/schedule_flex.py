from ..timefmt import fmt_time

# 色票沿用 iOS App 的 DesignSystem
COLORS = {"bg": "#0B0E14", "card": "#161B26", "card2": "#1C2333", "gold": "#E2B659",
          "text": "#FFFFFF", "label": "#94A3B8", "warn": "#F59E0B"}
MAX_EVENTS = 40  # Flex 訊息有大小上限


def schedule_bubble(title: str, groups: list, conflicts: set, calendars: list) -> dict:
    body, count = [], 0
    for i, group in enumerate(groups):
        if count >= MAX_EVENTS:
            break
        if i:
            body.append({"type": "separator", "margin": "lg", "color": COLORS["card2"]})
        body.append({"type": "text", "text": group["label"], "size": "sm", "weight": "bold",
                     "color": COLORS["gold"], "margin": "lg" if i else "none"})
        for ev in group["events"][: MAX_EVENTS - count]:
            body.append(_event_row(ev, ev["uid"] in conflicts))
        count += len(group["events"])
    if conflicts:
        body.append({"type": "text", "text": "⚠️ 橘色時間代表行程重疊", "size": "xs", "color": COLORS["warn"], "margin": "lg"})

    legend = "　".join(f"{c['emoji']} {c['label']}" for c in calendars)
    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box", "layout": "vertical", "backgroundColor": COLORS["bg"],
            "contents": [
                {"type": "text", "text": title, "weight": "bold", "size": "lg", "color": COLORS["text"]},
                {"type": "text", "text": legend or " ", "size": "xs", "color": COLORS["label"], "margin": "sm", "wrap": True},
            ],
        },
        "body": {"type": "box", "layout": "vertical", "backgroundColor": COLORS["card"], "spacing": "sm", "contents": body},
    }


def _event_row(ev: dict, conflict: bool) -> dict:
    time_text = "全天" if ev["all_day"] else f"{fmt_time(ev['start'])}–{fmt_time(ev['end'])}"
    return {
        "type": "box", "layout": "horizontal", "spacing": "md", "margin": "sm",
        "contents": [
            {"type": "text", "text": time_text, "size": "sm", "flex": 0,
             "color": COLORS["warn"] if conflict else COLORS["label"]},
            {"type": "text", "text": f"{ev['cal']['emoji']} {ev['title']}", "size": "sm",
             "color": COLORS["text"], "wrap": True, "flex": 1},
        ],
    }
