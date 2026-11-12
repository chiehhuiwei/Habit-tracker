#!/usr/bin/env bash
# 用法：LINE_CHANNEL_ACCESS_TOKEN=xxx ./setup-richmenu.sh
set -euo pipefail
: "${LINE_CHANNEL_ACCESS_TOKEN:?請先設定 LINE_CHANNEL_ACCESS_TOKEN}"

DIR="$(cd "$(dirname "$0")" && pwd)"
API="https://api.line.me/v2/bot"
AUTH="Authorization: Bearer $LINE_CHANNEL_ACCESS_TOKEN"

json_field() {
  python3 -c "import sys, json; print(json.load(sys.stdin).get('$1', ''))"
}

OLD_ID=$(curl -sS "$API/user/all/richmenu" -H "$AUTH" | json_field richMenuId || true)

NEW_ID=$(curl -sS -X POST "$API/richmenu" -H "$AUTH" -H 'Content-Type: application/json' \
  -d @"$DIR/richmenu.json" | json_field richMenuId)
[ -n "$NEW_ID" ] || { echo "❌ 建立圖文選單失敗，請檢查 token 與 richmenu.json"; exit 1; }

curl -sS -f -X POST "https://api-data.line.me/v2/bot/richmenu/$NEW_ID/content" -H "$AUTH" \
  -H 'Content-Type: image/png' --data-binary @"$DIR/richmenu.png" > /dev/null
curl -sS -f -X POST "$API/user/all/richmenu/$NEW_ID" -H "$AUTH" > /dev/null

if [ -n "$OLD_ID" ] && [ "$OLD_ID" != "$NEW_ID" ]; then
  curl -sS -X DELETE "$API/richmenu/$OLD_ID" -H "$AUTH" > /dev/null && echo "🗑  已刪除舊選單 $OLD_ID"
fi
echo "✅ 圖文選單已設為預設：$NEW_ID"
