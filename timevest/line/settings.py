import re

REMIND_BEFORE_MIN = 15
TICK_INTERVAL_SEC = 60
DAILY_DIGEST_HOUR = 8
DIGEST_WHEN_EMPTY = False
PROMPT_END_AFTER_EVENT = True
LONG_SESSION_HOURS = 3
ICS_CACHE_SEC = 5 * 60
CONV_STATE_TTL_SEC = 30 * 60
# 結束後沒回覆頁數／備註時，多久自動寫入 BigQuery
PENDING_COMMIT_MIN = 10

NEW_INVESTMENT_DEFAULT = {"icon": "star.fill", "color": "#E2B659", "item_label": None, "progress_type": "none"}

# 輸入新活動時依關鍵字決定是否追問「書籍」等子項目
KEYWORD_RULES = [
    (re.compile(r"閱讀|讀書|看書|書"), {"icon": "book.fill", "item_label": "書籍", "progress_type": "pages"}),
    (re.compile(r"吉他|鋼琴|樂器|練琴"), {"icon": "guitars.fill", "item_label": "曲目", "progress_type": "percentage"}),
    (re.compile(r"課程|線上課|學習"), {"icon": "laptopcomputer", "item_label": "課程", "progress_type": "percentage"}),
]
