#!/usr/bin/env python3
"""產生純文字俐落版頂部頁籤式（Tabbed）LINE 圖文選單圖片（2500x1686）。
完全無 Emoji，採用高質感深色卡片 + 精緻線條。
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SS = 2
W, H = 2500, 1686
TAB_H = 266
CONTENT_H = H - TAB_H

COL_EDGES = [0, 833, 1667, 2500]
ROW_EDGES = [TAB_H, TAB_H + 710, H]
FONT_PATH = "/System/Library/Fonts/PingFang.ttc"

BG, CARD = "#0B0E14", "#161B26"
GOLD, INDIGO, TEAL, ORANGE, PURPLE, BLUE = (
    "#E2B659",
    "#6366F1",
    "#0D9488",
    "#F59E0B",
    "#A855F7",
    "#3B82F6",
)
TEXT, LABEL, TAB_INACTIVE = "#FFFFFF", "#94A3B8", "#64748B"


def s(v):
    return int(v * SS)


def load_font(size, weight):
    for index in range(30):
        try:
            font = ImageFont.truetype(FONT_PATH, s(size), index=index)
        except OSError:
            break
        family, style = font.getname()
        if family.endswith("TC") and style == weight:
            return font
    return ImageFont.truetype(FONT_PATH, s(size))


def draw_centered(d, cx, y, text, font, fill):
    bbox = d.textbbox((0, 0), text, font=font)
    d.text((cx - (bbox[2] - bbox[0]) / 2 - bbox[0], y), text, font=font, fill=fill)


# ── 純幾何向量圖示 ──
def icon_play(d, cx, cy, r, color):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=s(10))
    t = r * 0.45
    d.polygon([(cx - t * 0.7, cy - t), (cx - t * 0.7, cy + t), (cx + t * 1.05, cy)], fill=color)


def icon_stop(d, cx, cy, r, color):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=s(10))
    q = r * 0.38
    d.rounded_rectangle([cx - q, cy - q, cx + q, cy + q], radius=s(10), fill=color)


def icon_timer(d, cx, cy, r, color):
    kw, kh = r * 0.26, r * 0.16
    top_y = cy - r * 0.85
    d.rounded_rectangle([cx - kw / 2, top_y - kh, cx + kw / 2, top_y], radius=s(6), fill=color)
    br = r * 0.80
    bcy = cy + r * 0.08
    d.ellipse([cx - br, bcy - br, cx + br, bcy + br], outline=color, width=s(10))
    d.ellipse([cx - s(9), bcy - s(9), cx + s(9), bcy + s(9)], fill=color)
    d.line([cx, bcy, cx, bcy - br * 0.55], fill=color, width=s(8))
    d.line([cx, bcy, cx + br * 0.45, bcy], fill=color, width=s(7))


def icon_bars(d, cx, cy, r, color):
    bw, gap, base = r * 0.36, r * 0.18, cy + r * 0.8
    for i, h in enumerate([0.85, 1.35, 1.05]):
        x = cx - bw * 1.5 - gap + i * (bw + gap)
        d.rounded_rectangle([x, base - r * h, x + bw, base], radius=s(8), fill=color)
    d.line([cx - r, base + s(10), cx + r, base + s(10)], fill=color, width=s(7))


def icon_coins(d, cx, cy, r, color):
    w, h = r * 0.9, r * 0.3
    for i in range(3):
        y = cy + r * 0.5 - i * h * 1.05
        d.rounded_rectangle([cx - w, y - h / 2, cx + w * 0.5, y + h / 2], radius=h / 2, fill=color, width=s(5))
    cr = r * 0.45
    ccx, ccy = cx + r * 0.45, cy - r * 0.4
    d.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr], fill=color)


def calendar_frame(d, cx, cy, r, color):
    left, top, right, bottom = cx - r * 0.9, cy - r * 0.75, cx + r * 0.9, cy + r * 0.9
    d.rounded_rectangle([left, top, right, bottom], radius=s(18), outline=color, width=s(10))
    d.rounded_rectangle([left, top, right, top + r * 0.42], radius=s(18), fill=color)
    for x in (cx - r * 0.4, cx + r * 0.4):
        d.rounded_rectangle([x - s(8), top - r * 0.22, x + s(8), top + r * 0.12], radius=s(8), fill=color)
    return left, top + r * 0.42, right, bottom


def icon_calendar(d, cx, cy, r, color):
    _, inner_top, _, bottom = calendar_frame(d, cx, cy, r, color)
    mid = (inner_top + bottom) / 2
    d.ellipse([cx - r * 0.2, mid - r * 0.2, cx + r * 0.2, mid + r * 0.2], fill=color)


def icon_week(d, cx, cy, r, color):
    left, inner_top, right, bottom = calendar_frame(d, cx, cy, r, color)
    dot = r * 0.08
    rows = [(4, inner_top + (bottom - inner_top) * 0.35), (3, inner_top + (bottom - inner_top) * 0.7)]
    for count, y in rows:
        span = (right - left) * 0.6
        for i in range(count):
            x = cx - span / 2 + span * i / 3
            d.ellipse([x - dot, y - dot, x + dot, y + dot], fill=color)


def icon_edit_cal(d, cx, cy, r, color):
    calendar_frame(d, cx, cy, r, color)
    px, py = cx + r * 0.35, cy + r * 0.35
    d.line([px - r * 0.35, py - r * 0.35, px, py], fill=color, width=s(9))


def icon_bell(d, cx, cy, r, color):
    d.arc([cx - r * 0.6, cy - r * 0.7, cx + r * 0.6, cy + r * 0.3], 180, 0, fill=color, width=s(9))
    d.line([cx - r * 0.7, cy + r * 0.3, cx + r * 0.7, cy + r * 0.3], fill=color, width=s(9))
    d.ellipse([cx - s(12), cy + r * 0.4, cx + s(12), cy + r * 0.65], fill=color)


def icon_conflict(d, cx, cy, r, color):
    top = (cx, cy - r * 0.75)
    bl = (cx - r * 0.75, cy + r * 0.7)
    br = (cx + r * 0.75, cy + r * 0.7)
    d.polygon([top, bl, br], outline=color, width=s(9))
    d.line([cx, cy - r * 0.25, cx, cy + r * 0.2], fill=color, width=s(9))
    d.ellipse([cx - s(7), cy + r * 0.35, cx + s(7), cy + r * 0.5], fill=color)


def icon_help(d, cx, cy, r, color):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=s(9))
    draw_centered(d, cx, cy - r * 0.52, "?", load_font(68, "Bold"), color)


ICONS = {
    "play": icon_play,
    "stop": icon_stop,
    "timer": icon_timer,
    "bars": icon_bars,
    "coins": icon_coins,
    "calendar": icon_calendar,
    "week": icon_week,
    "edit_cal": icon_edit_cal,
    "bell": icon_bell,
    "conflict": icon_conflict,
    "help": icon_help,
}

# ── 內容格設定（無任何 Emoji）──
BUTTONS_INVEST = [
    ("開始記錄", "選擇活動・計時", "play", GOLD),
    ("結束記錄", "結算時間・心得", "stop", ORANGE),
    ("我的活動", "專注碼表・LIFF", "timer", GOLD),
    ("今日統計", "投入時數與天數", "bars", GOLD),
    ("收益與項目", "進度管理・資產", "coins", TEAL),
    ("使用說明", "快速上手指南", "help", INDIGO),
]

BUTTONS_SCHEDULE = [
    ("今日行程", "今日課表排程", "calendar", INDIGO),
    ("本週行程", "未來 7 天檢視", "week", TEAL),
    ("管理行程", "綁定手機日曆", "edit_cal", BLUE),
    ("提醒設定", "課前通知設定", "bell", ORANGE),
    ("衝突檢查", "重疊排程警示", "conflict", PURPLE),
    ("行程說明", "同步常見問題", "help", INDIGO),
]


def draw_tabs(d, active_tab, fonts):
    tab_w = W // 2
    # Tab 1: 時光投資
    is_t1 = active_tab == "invest"
    t1_bg = CARD if is_t1 else BG
    t1_fg = GOLD if is_t1 else TAB_INACTIVE
    d.rectangle([0, 0, s(tab_w), s(TAB_H)], fill=t1_bg)
    draw_centered(d, s(tab_w // 2), s(85), "時光投資", fonts["tab"], t1_fg)
    if is_t1:
        d.line([s(80), s(TAB_H - 8), s(tab_w - 80), s(TAB_H - 8)], fill=GOLD, width=s(10))

    # Tab 2: 行程管理
    is_t2 = active_tab == "schedule"
    t2_bg = CARD if is_t2 else BG
    t2_fg = INDIGO if is_t2 else TAB_INACTIVE
    d.rectangle([s(tab_w), 0, s(W), s(TAB_H)], fill=t2_bg)
    draw_centered(d, s(tab_w + tab_w // 2), s(85), "行程管理", fonts["tab"], t2_fg)
    if is_t2:
        d.line([s(tab_w + 80), s(TAB_H - 8), s(W - 80), s(TAB_H - 8)], fill=INDIGO, width=s(10))

    # 分隔線
    d.line([0, s(TAB_H), s(W), s(TAB_H)], fill="#1E293B", width=s(4))
    d.line([s(tab_w), s(35), s(tab_w), s(TAB_H - 35)], fill="#334155", width=s(3))


def draw_content_button(d, box, button, fonts):
    title, subtitle, icon, accent = button
    left, top, right, bottom = box
    pad = s(16)
    card = [left + pad, top + pad, right - pad, bottom - pad]
    d.rounded_rectangle(card, radius=s(44), fill=CARD, outline=accent, width=s(3))

    cx = (left + right) / 2
    height = bottom - top
    ICONS[icon](d, cx, top + height * 0.36, s(96), accent)
    draw_centered(d, cx, top + height * 0.60, title, fonts["title"], TEXT)
    draw_centered(d, cx, top + height * 0.77, subtitle, fonts["sub"], LABEL)


def generate_image(active_tab, buttons, filename):
    img = Image.new("RGB", (s(W), s(H)), BG)
    d = ImageDraw.Draw(img)
    fonts = {
        "tab": load_font(88, "Bold"),
        "title": load_font(80, "Semibold"),
        "sub": load_font(38, "Regular"),
    }
    draw_tabs(d, active_tab, fonts)

    for i, button in enumerate(buttons):
        row, col = divmod(i, 3)
        box = [s(COL_EDGES[col]), s(ROW_EDGES[row]), s(COL_EDGES[col + 1]), s(ROW_EDGES[row + 1])]
        draw_content_button(d, box, button, fonts)

    out = Path(__file__).with_name(filename)
    img.resize((W, H), Image.LANCZOS).save(out, optimize=True)
    print(f"✅ {out.name} ({out.stat().st_size // 1024} KB)")


def main():
    generate_image("invest", BUTTONS_INVEST, "richmenu_invest.png")
    generate_image("schedule", BUTTONS_SCHEDULE, "richmenu_schedule.png")


if __name__ == "__main__":
    main()
