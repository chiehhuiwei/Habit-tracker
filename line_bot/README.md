# timeVest × LINE OA

用 LINE 記錄專注時間，並把「上英文課」與「教英文」兩個行事曆合併查看、自動提醒。
LINE 與網頁版共用同一個 `TimeVestService`：帳戶、項目都存在同一份 JSON，每次專注都寫進同一張 BigQuery `habit_logs`，所以 LINE 記錄會立刻出現在網頁版。

```
LINE App ──HTTPS──▶ Caddy ──▶ app.py（:7860）
                               ├─ /           Gradio 網頁版
                               └─ /line/webhook  LINE ──▶ TimeVestService ──▶ JSON + BigQuery
                                    └─ 排程：讀兩個 iCal 行事曆 → 推播提醒
```

## 功能

| 圖文選單 | 行為 |
|---|---|
| ▶ 開始記錄 | 選帳戶（或直接輸入新活動）→ 有子項目的帳戶會問「書籍名稱」→ 新書再問總頁數 → 開始計時 |
| ⏹ 結束記錄 | 停止計時 → 問讀到第幾頁（可略過）→ 問備註（可略過）→ 寫入 BigQuery |
| 📊 今日統計 | 今日各帳戶時數、近 7 天、連續天數、進行中的記錄 |
| 📅 今日行程 / 📆 本週行程 | 兩個行事曆合併顯示，時間重疊標橘色 ⚠️ |
| 💰 我的帳戶 | 各帳戶累積時數、進行中項目進度 |

自動提醒（推播）：每天 08:00 今日行程、課前 15 分鐘（附「▶ 開始記錄這堂」一鍵開始）、課程結束時若還在記錄會問要不要結束、記錄超過 3 小時提醒。

- 寫入 BigQuery 的 `detail` 格式與網頁版相同：`讀至第 160 頁｜備註`，沒填則為 `專注投入`。
- BigQuery 串流寫入後無法馬上 UPDATE，所以按結束後會先保留草稿，收齊頁數與備註才一次寫入。沒回覆的話 10 分鐘後自動寫入；中途按其他選單也會先寫入，時間不會遺失。
- 輸入新活動名稱時，含「閱讀／讀書／書」會自動設定為「書籍＋頁數」帳戶（規則在 `settings.py` 的 `KEYWORD_RULES`）。

## 設定

### 1. LINE

1. [LINE Official Account Manager](https://manager.line.biz/) 建立官方帳號 →「設定 → Messaging API」啟用。
2. [LINE Developers Console](https://developers.line.biz/console/)：**Basic settings** 複製 Channel secret；**Messaging API** 發行 Channel access token (long-lived)。
3. OA Manager →「回應設定」：關閉自動回應訊息、開啟 Webhook。

### 2. VM 上的 `.env`

```env
LINE_CHANNEL_SECRET=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_DOMAIN=line.example.com   # 指向這台 VM 的網域
```

沒填 `LINE_CHANNEL_*` 時 app 照舊用 `app.launch()` 啟動，網頁版行為完全不變。

### 3. 行事曆

```bash
mkdir -p line_data
cp line_bot/calendars.example.json line_data/calendars.json   # 填入兩個 iCal 網址
```

| 來源 | 取得網址 |
|---|---|
| Google 日曆 | 日曆設定 →「整合日曆」→ **iCal 格式的私密網址**（不需 Google 授權）|
| 上課／教課平台 | 平台的「行事曆同步」或「匯出到 Google/Apple 行事曆」提供的 `.ics` 網址 |
| 平台沒有匯出 | 在 Google 日曆另建一個日曆手動排課，再用上面 Google 的方式 |

`investment` 是從提醒按「開始記錄」時要記到哪個帳戶（不存在會自動建立）。支援每週重複、單次取消、單次改期；每 5 分鐘重新下載，改 `calendars.json` 不需重啟。私密網址等同密碼，`line_data/` 已 gitignore。

確認讀得到（容器內）：

```bash
docker compose exec habit-tracker python -m line_bot.check_calendars
```

### 4. HTTPS 與 Webhook

LINE 只接受 HTTPS。`docker-compose.yml` 內建 Caddy（自動申請憑證），網域 DNS 指向 VM、防火牆開 80/443 後：

```bash
docker compose --profile https up -d --build
```

LINE Developers → Messaging API → Webhook URL 填 `https://<LINE_DOMAIN>/line/webhook` → **Verify** → 開啟 **Use webhook**。
然後用手機加好友並傳任意訊息：沒設 `LINE_OWNER_USER_ID` 時，**第一個傳訊息的人會被綁定為擁有者**（log 會印出 userId，可回填 `.env` 固定）。

> 網頁版也會變成 `https://<LINE_DOMAIN>/`；原本的 `http://<IP>:7860` 仍可用。

### 5. 圖文選單（在本機執行一次）

```bash
cd line_bot/richmenu
python3 generate_image.py                          # 改文字／顏色後重新產生（需 Pillow）
LINE_CHANNEL_ACCESS_TOKEN=xxx ./setup-richmenu.sh  # 建立、上傳、設為預設、刪除舊選單
```

## 之後更新

```bash
git pull && docker compose --profile https up -d --build
```

`line_data/`（對話狀態、行事曆設定）以 volume 掛載，重建 image 不會遺失。

## 調整參數（`line_bot/settings.py`）

| 參數 | 預設 | 說明 |
|---|---|---|
| `REMIND_BEFORE_MIN` | 15 | 課前幾分鐘提醒 |
| `DAILY_DIGEST_HOUR` | 8 | 每日行程推播時間 |
| `DIGEST_WHEN_EMPTY` | False | 沒行程也推播 |
| `PROMPT_END_AFTER_EVENT` | True | 課程結束時提醒結束記錄 |
| `LONG_SESSION_HOURS` | 3 | 記錄超過幾小時提醒 |
| `PENDING_COMMIT_MIN` | 10 | 結束後沒回覆，幾分鐘後自動寫入 |

## 注意事項

- **推播額度**：回覆免費，提醒屬於推播。以每天 2 堂課估算約 150 則／月，接近免費方案上限時可關掉 `PROMPT_END_AFTER_EVENT`。
- **安全性**：每個 webhook 請求驗證 `X-Line-Signature`，且只回應綁定的擁有者。
- **測試**：`uv pip install pytest httpx && python -m pytest tests`（假的 BigQuery client，不會動到真實資料與 repo 內的 JSON）。
