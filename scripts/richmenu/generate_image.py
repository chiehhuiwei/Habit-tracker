#!/usr/bin/env python3
"""產生 LINE 雙分頁圖文選單圖片（2500x1686，3x2 格）。
Menu 1: richmenu_invest.png (時光投資)
Menu 2: richmenu_schedule.png (行程管理)
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SS = 2  # 超取樣
W, H = 2500, 1686
COL_EDGES = [0, 833, 1667, 2500]
ROW_EDGES = [0, 843, 1686]
FONT_PATH = "/System/Library/Fonts/PingFang.ttc"

BG, CARD, CARD2 = "#0B0E14", "#161B26", "#1C2333"
GOLD, INDIGO, TEAL, ORANGE, PURPLE, BLUE = (
    "#E2B659",
    "#6366F1",
    "#0D9488",
    "#F59E0B",
    "#A855F7",
    "#3B82F6",
)
TEXT, LABEL = "#FFFFFF", "#94A3B8"

# ── 選單 1：時光投資 ──
BUTTONS_INVEST = [
    ("開始記錄", "選擇活動・開始計時", "play", GOLD),
    ("結束記錄", "停止計時・寫下心得", "stop", ORANGE),
    ("我的活動", "專注碼表・LIFF 網頁", "timer", GOLD),
    ("今日統計", "投入時數・連續天數", "bars", GOLD),
    ("收益與項目", "項目進度・資產分配", "coins", TEAL),
    ("行程管理 ➔", "課表檢視・行事曆切換", "switch_cal", INDIGO),
]

# ── 選單 2：行程管理 ──
BUTTONS_SCHEDULE = [
    ("今日行程", "今日課表・活動檢視", "calendar", INDIGO),
    ("本週行程", "未來 7 天・衝突標示", "week", TEAL),
    ("管理行程", "LIFF 編輯・綁定日曆", "edit_cal", BLUE),
    ("提醒設定", "課前通知・早安推播", "bell", ORANGE),
    ("衝突檢查", "排課重疊偵測 ⚠️", "conflict", PURPLE),
    ("時光投資 ➔", "返回計時・資產對帳", "switch_invest", GOLD),
]


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


def icon_play(d, cx, cy, r, color, _bg):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=s(11))
    t = r * 0.45
    d.polygon([(cx - t * 0.7, cy - t), (cx - t * 0.7, cy + t), (cx + t * 1.05, cy)], fill=color)


def icon_stop(d, cx, cy, r, color, _bg):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=s(11))
    q = r * 0.38
    d.rounded_rectangle([cx - q, cy - q, cx + q, cy + q], radius=s(12), fill=color)


def icon_timer(d, cx, cy, r, color, _bg):
    kw, kh = r * 0.26, r * 0.16
    top_y = cy - r * 0.85
    d.rounded_rectangle([cx - kw / 2, top_y - kh, cx + kw / 2, top_y], radius=s(6), fill=color)
    br = r * 0.82
    bcy = cy + r * 0.08
    d.ellipse([cx - br, bcy - br, cx + br, bcy + br], outline=color, width=s(11))
    d.ellipse([cx - s(10), bcy - s(10), cx + s(10), bcy + s(10)], fill=color)
    d.line([cx, bcy, cx, bcy - br * 0.55], fill=color, width=s(9))
    d.line([cx, bcy, cx + br * 0.45, bcy], fill=color, width=s(8))


def icon_bars(d, cx, cy, r, color, _bg):
    bw, gap, base = r * 0.38, r * 0.2, cy + r * 0.85
    for i, h in enumerate([0.9, 1.45, 1.15]):
        x = cx - bw * 1.5 - gap + i * (bw + gap)
        d.rounded_rectangle([x, base - r * h, x + bw, base], radius=s(10), fill=color)
    d.line([cx - r, base + s(12), cx + r, base + s(12)], fill=color, width=s(8))


def calendar_frame(d, cx, cy, r, color, bg):
    left, top, right, bottom = cx - r, cy - r * 0.8, cx + r, cy + r * 0.95
    d.rounded_rectangle([left, top, right, bottom], radius=s(22), outline=color, width=s(11))
    d.rounded_rectangle([left, top, right, top + r * 0.45], radius=s(22), fill=color)
    for x in (cx - r * 0.45, cx + r * 0.45):
        d.rounded_rectangle([x - s(9), top - r * 0.25, x + s(9), top + r * 0.15], radius=s(9), fill=color, outline=bg, width=s(4))
    return left, top + r * 0.45, right, bottom


def icon_calendar(d, cx, cy, r, color, bg):
    _, inner_top, _, bottom = calendar_frame(d, cx, cy, r, color, bg)
    mid = (inner_top + bottom) / 2
    d.ellipse([cx - r * 0.22, mid - r * 0.22, cx + r * 0.22, mid + r * 0.22], fill=color)


def icon_week(d, cx, cy, r, color, bg):
    left, inner_top, right, bottom = calendar_frame(d, cx, cy, r, color, bg)
    dot = r * 0.09
    rows = [(4, inner_top + (bottom - inner_top) * 0.35), (3, inner_top + (bottom - inner_top) * 0.7)]
    for count, y in rows:
        span = (right - left) * 0.62
        for i in range(count):
            x = cx - span / 2 + span * i / 3
            d.ellipse([x - dot, y - dot, x + dot, y + dot], fill=color)


def icon_coins(d, cx, cy, r, color, bg):
    w, h = r * 0.95, r * 0.32
    for i in range(3):
        y = cy + r * 0.55 - i * h * 1.05
        d.rounded_rectangle([cx - w, y - h / 2, cx + w * 0.55, y + h / 2], radius=h / 2, fill=color, outline=bg, width=s(6))
    cr = r * 0.48
    ccx, ccy = cx + r * 0.5, cy - r * 0.45
    d.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr], fill=color, outline=bg, width=s(8))
    d.ellipse([ccx - cr * 0.5, ccy - cr * 0.5, ccx + cr * 0.5, ccy + cr * 0.5], outline=bg, width=s(7))


def icon_switch_cal(d, cx, cy, r, color, bg):
    calendar_frame(d, cx - r * 0.15, cy - r * 0.1, r * 0.65, color, bg)
    # 箭頭向右下
    ax, ay = cx + r * 0.45, cy + r * 0.45
    d.polygon([(ax + s(15), ay), (ax - s(12), ay - s(18)), (ax - s(12), ay + s(18))], fill=color)


def icon_switch_invest(d, cx, cy, r, color, _bg):
    # 碼表縮小版
    icon_timer(d, cx - r * 0.15, cy - r * 0.1, r * 0.65, color, _bg)
    ax, ay = cx + r * 0.45, cy + r * 0.45
    d.polygon([(ax + s(15), ay), (ax - s(12), ay - s(18)), (ax - s(12), ay + s(18))], fill=color)


def icon_edit_cal(d, cx, cy, r, color, bg):
    calendar_frame(d, cx, cy, r, color, bg)
    # 筆
    px, py = cx + r * 0.4, cy + r * 0.4
    d.line([px - r * 0.4, py - r * 0.4, px, py], fill=color, width=s(10))


def icon_bell(d, cx, cy, r, color, _bg):
    d.arc([cx - r * 0.65, cy - r * 0.75, cx + r * 0.65, cy + r * 0.35], 180, 0, fill=color, width=s(10))
    d.line([cx - r * 0.75, cy + r * 0.35, cx + r * 0.75, cy + r * 0.35], fill=color, width=s(10))
    d.ellipse([cx - s(15), cy + r * 0.45, cx + s(15), cy + r * 0.7], fill=color)


def icon_conflict(d, cx, cy, r, color, _bg):
    # 警告三角形
    top = (cx, cy - r * 0.8)
    bl = (cx - r * 0.8, cy + r * 0.75)
    br = (cx + r * 0.8, cy + r * 0.75)
    d.polygon([top, bl, br], outline=color, width=s(10))
    # 感嘆號
    d.line([cx, cy - r * 0.3, cx, cy + r * 0.2], fill=color, width=s(10))
    d.ellipse([cx - s(8), cy + r * 0.38, cx + s(8), cy + r * 0.54], fill=color)


ICONS = {
    "play": icon_play,
    "stop": icon_stop,
    "timer": icon_timer,
    "bars": icon_bars,
    "calendar": icon_calendar,
    "week": icon_week,
    "coins": icon_coins,
    "switch_cal": icon_switch_cal,
    "switch_invest": icon_switch_invest,
    "edit_cal": icon_edit_cal,
    "bell": icon_bell,
    "conflict": icon_conflict,
}


def draw_centered(d, cx, y, text, font, fill):
    bbox = d.textbbox((0, 0), text, font=font)
    d.text((cx - (bbox[2] - bbox[0]) / 2 - bbox[0], y), text, font=font, fill=fill)


def draw_button(d, box, button, fonts):
    title, subtitle, icon, accent = button
    left, top, right, bottom = box
    pad = s(22)
    card = [left + pad, top + pad, right - pad, bottom - pad]
    d.rounded_rectangle(card, radius=s(56), fill=CARD, outline=accent, width=s(4))

    cx = (left + right) / 2
    height = bottom - top
    ICONS[icon](d, cx, top + height * 0.36, s(118), accent, CARD)
    draw_centered(d, cx, top + height * 0.60, title, fonts["title"], TEXT)
    draw_centered(d, cx, top + height * 0.76, subtitle, fonts["sub"], LABEL)


def generate_menu_image(buttons, out_name):
    img = Image.new("RGB", (s(W), s(H)), BG)
    d = ImageDraw.Draw(img)
    fonts = {"title": load_font(96, "Semibold"), "sub": load_font(44, "Regular")}
    for i, button in enumerate(buttons):
        row, col = divmod(i, 3)
        box = [s(COL_EDGES[col]), s(ROW_EDGES[row]), s(COL_EDGES[col + 1]), s(ROW_EDGES[row + 1])]
        draw_button(d, box, button, fonts)

    out = Path(__file__).with_name(out_name)
    img.resize((W, H), Image.LANCZOS).save(out, optimize=True)
    print(f"✅ {out.name} ({out.stat().st_size // 1024} KB)")


def main():
    generate_menu_image(BUTTONS_INVEST, "richmenu_invest.png")
    generate_menu_image(BUTTONS_SCHEDULE, "richmenu_schedule.png")


if __name__ == "__main__":
    main()
