#!/usr/bin/env python3
"""產生 LINE 圖文選單圖片（2500x1686，3x2 格），色票沿用 iOS App。"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SS = 2  # 超取樣，讓圖形邊緣平滑
W, H = 2500, 1686
COL_EDGES = [0, 833, 1667, 2500]
ROW_EDGES = [0, 843, 1686]
FONT_PATH = "/System/Library/Fonts/PingFang.ttc"

BG, CARD, CARD2 = "#0B0E14", "#161B26", "#1C2333"
GOLD, INDIGO, TEAL, ORANGE = "#E2B659", "#6366F1", "#0D9488", "#F59E0B"
TEXT, LABEL = "#FFFFFF", "#94A3B8"

# 順序需與 richmenu.json 的 areas 一致
BUTTONS = [
    ("開始記錄", "選擇活動・開始計時", "play", GOLD, True),
    ("結束記錄", "停止計時・寫下心得", "stop", ORANGE, False),
    ("今日統計", "投入時數・連續天數", "bars", GOLD, False),
    ("今日行程", "上課＋教課 合併檢視", "calendar", INDIGO, False),
    ("本週行程", "未來 7 天・重疊提醒", "week", TEAL, False),
    ("我的帳戶", "累積資產・閱讀進度", "coins", GOLD, False),
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
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=s(12))
    t = r * 0.45
    d.polygon([(cx - t * 0.7, cy - t), (cx - t * 0.7, cy + t), (cx + t * 1.05, cy)], fill=color)


def icon_stop(d, cx, cy, r, color, _bg):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=s(12))
    q = r * 0.38
    d.rounded_rectangle([cx - q, cy - q, cx + q, cy + q], radius=s(12), fill=color)


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


ICONS = {
    "play": icon_play,
    "stop": icon_stop,
    "bars": icon_bars,
    "calendar": icon_calendar,
    "week": icon_week,
    "coins": icon_coins,
}


def draw_centered(d, cx, y, text, font, fill):
    bbox = d.textbbox((0, 0), text, font=font)
    d.text((cx - (bbox[2] - bbox[0]) / 2 - bbox[0], y), text, font=font, fill=fill)


def draw_button(d, box, button, fonts):
    title, subtitle, icon, accent, primary = button
    left, top, right, bottom = box
    pad = s(22)
    card = [left + pad, top + pad, right - pad, bottom - pad]
    fill = accent if primary else CARD
    d.rounded_rectangle(card, radius=s(56), fill=fill, outline=accent if not primary else None, width=s(4))

    fg = BG if primary else accent
    cx = (left + right) / 2
    height = bottom - top
    ICONS[icon](d, cx, top + height * 0.36, s(118), fg, fill)
    draw_centered(d, cx, top + height * 0.60, title, fonts["title"], BG if primary else TEXT)
    draw_centered(d, cx, top + height * 0.76, subtitle, fonts["sub"], CARD2 if primary else LABEL)


def main():
    img = Image.new("RGB", (s(W), s(H)), BG)
    d = ImageDraw.Draw(img)
    fonts = {"title": load_font(96, "Semibold"), "sub": load_font(44, "Regular")}
    for i, button in enumerate(BUTTONS):
        row, col = divmod(i, 3)
        box = [s(COL_EDGES[col]), s(ROW_EDGES[row]), s(COL_EDGES[col + 1]), s(ROW_EDGES[row + 1])]
        draw_button(d, box, button, fonts)

    out = Path(__file__).with_name("richmenu.png")
    img.resize((W, H), Image.LANCZOS).save(out, optimize=True)
    print(f"✅ {out}（{out.stat().st_size // 1024} KB，上限 1024 KB）")


if __name__ == "__main__":
    main()
