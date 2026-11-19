"""單一背景執行緒依序處理 LINE 事件與排程，避免同時讀寫 state.json 與 service。"""
import traceback
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="line-bot")


def _safe(fn, *args):
    try:
        fn(*args)
    except Exception:
        traceback.print_exc()


def submit(fn, *args):
    return _executor.submit(_safe, fn, *args)
