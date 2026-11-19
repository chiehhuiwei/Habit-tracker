"""python -m timevest.line.set_calendars <userId> <calendars.json>：把某位使用者的行事曆來源寫進資料庫。

檔案格式見 examples/calendars.example.json。傳入空陣列 [] 代表清除。
"""
import json
import sys

from .calendar.sources import save_calendar_sources


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    user_id, path = sys.argv[1], sys.argv[2]
    with open(path, encoding="utf-8") as f:
        sources = json.load(f)
    save_calendar_sources(user_id, sources)
    print(f"已儲存 {len(sources)} 個行事曆給 {user_id}")


if __name__ == "__main__":
    main()
