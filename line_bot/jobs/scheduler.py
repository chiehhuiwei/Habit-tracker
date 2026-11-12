import threading
from datetime import timedelta

from .. import settings, worker
from ..flows.pending import commit_if_stale
from ..timefmt import now
from .reminders import daily_digest_tick, reminder_tick

MAX_CATCHUP = timedelta(minutes=10)  # 停機太久時不補發過舊的「課程結束」提醒


def _tick(last: dict) -> None:
    current = now()
    reminder_tick(current, max(last["at"], current - MAX_CATCHUP))
    daily_digest_tick(current)
    commit_if_stale()
    last["at"] = current


def start_scheduler() -> None:
    last = {"at": now() - timedelta(seconds=settings.TICK_INTERVAL_SEC)}
    stop = threading.Event()

    def loop():
        while not stop.is_set():
            worker.submit(_tick, last)
            stop.wait(settings.TICK_INTERVAL_SEC)

    threading.Thread(target=loop, name="line-scheduler", daemon=True).start()
