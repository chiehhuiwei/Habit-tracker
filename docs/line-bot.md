# timeVest × LINE OA & LIFF

用 LINE 記錄專注時間、開啟 LIFF 專注碼表與進度管理，並支援行事曆自動提醒。
所有資料存在 SQLite（`line_data/timevest.db`），每次專注記錄寫入 Google BigQuery（`habit_logs`），支援多位使用者各自獨立記錄。

```
LINE App ──HTTPS──▶ Caddy ──▶ timevest.main（FastAPI :7860）
                               ├─ /liff/         LIFF 手機網頁（專注碼表／項目進度／收益）
                               ├─ /api/*         LIFF 後端 REST API
                               └─ /line/webhook  LINE 機器人 Webhook
                                    ├─ SQLite    每位使用者的帳戶／項目／計時／狀態
                                    ├─ BigQuery  專注時間序列活動日誌
                                    └─ 排程       行事曆提醒與每日摘要
```

## 功能

| 圖文選單 | 行為 |
|---|---|
| ▶ 開始記錄 | 選帳戶（或直接輸入新活動）→ 有子項目的帳戶追問項目名稱 → 開始計時 |
| ⏹ 結束記錄 | 停止計時 → 問進度／頁數（可略過）→ 問備註（可略過）→ 寫入 BigQuery |
| ⏱ 我的活動 | 開啟 LIFF 網頁專注碼表，支援即時碼表計時、補記歷史記錄 |
| 📊 今日統計 | 今日各帳戶時數、近 7 天投入、連續天數、進行中的記錄 |
| 📅 今日行程 | 顯示個人行事曆排程，時間重疊標記橘色 ⚠️ |
| 🧾 收益與項目 | 開啟 LIFF 網頁項目管理，設定 ⭐ 常用活動、編輯進度與檢視里程碑 |

- **多使用者支援**：每位使用者擁有自己獨立的帳戶、項目與計時狀態。可透過 `LINE_INVITE_CODE` 邀請朋友加入。
- **常用活動置頂**：在 LIFF 標記 ⭐ 常用帳戶，LINE 點選「開始記錄」時將自動排在最前排。也可直接傳「`開始 閱讀`」一鍵開始。

---

## 設定步驟

### 1. LINE Developers 設定

1. [LINE Official Account Manager](https://manager.line.biz/) 建立官方帳號 →「設定 → Messaging API」啟用。
2. [LINE Developers Console](https://developers.line.biz/console/)：
   - **Basic settings**：複製 `Channel secret`。
   - **Messaging API**：發行並複製 `Channel access token (long-lived)`。
   - **LIFF**：建立 LIFF App，Endpoint URL 填 `https://<你的網域>/liff/`，Scope 勾選 `profile`，取得 `LIFF ID`。
3. OA Manager →「回應設定」：關閉自動回應訊息、開啟 Webhook。

### 2. VM 上的 `.env`

```env
LINE_CHANNEL_SECRET=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_DOMAIN=line.example.com      # 指向這台 VM 的網域（用於 Caddy 自動 HTTPS）
LIFF_ID=...                       # LINE Developers 建立的 LIFF ID
LINE_INVITE_CODE=...              # 朋友加入時需輸入的邀請碼（留空則僅限擁有者）
```

### 3. 行事曆（選用）

```bash
cp examples/calendars.example.json my-calendars.json   # 填入 iCal 網址
python -m timevest.line.set_calendars <你的 LINE userId> my-calendars.json
```

確認讀得到（容器內）：
```bash
docker compose exec habit-tracker python -m timevest.line.check_calendars
```

### 4. 啟動服務與 Webhook 驗證

```bash
docker compose --profile https up -d --build
```

- LINE Developers → Messaging API → Webhook URL 填 `https://<LINE_DOMAIN>/line/webhook` → **Verify** → 開啟 **Use webhook**。
- 用手機加好友並傳任意訊息：第一位傳訊息的使用者將自動綁定為系統擁有者。

### 5. 上傳圖文選單

```bash
cd scripts/richmenu
python3 generate_image.py                          # 重新產生 2500x1686 圖片（需 Pillow）
./setup-richmenu.sh                                # 自動讀取 .env，建立、上傳並設為預設選單
```

---

## 資料儲存說明

- **SQLite**（`line_data/timevest.db`）：帳戶、項目、里程碑、計時中狀態、行事曆與使用者名單皆存於 SQLite，每位使用者透過 `user_id` 嚴格隔離。
- **BigQuery**（`habit_logs`）：存放完成的專注紀錄，供長期統計與分析。
- `line_data/` 必須以 Docker volume 掛載保存。
