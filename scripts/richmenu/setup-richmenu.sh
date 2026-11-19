#!/usr/bin/env bash
# 用法：LINE_CHANNEL_ACCESS_TOKEN=xxx [LIFF_ID=xxx] ./setup-richmenu.sh
# 一鍵建立雙分頁圖文選單（時光投資 menu-invest <-> 行程管理 menu-schedule）
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$DIR/../.." && pwd)"

if [ -f "$ROOT_DIR/.env" ]; then
  if [ -z "${LINE_CHANNEL_ACCESS_TOKEN:-}" ]; then
    VAL=$(grep -E '^LINE_CHANNEL_ACCESS_TOKEN=' "$ROOT_DIR/.env" | tail -1 | cut -d= -f2- | tr -d "\"' \r" || true)
    [ -n "$VAL" ] && export LINE_CHANNEL_ACCESS_TOKEN="$VAL"
  fi
  if [ -z "${LIFF_ID:-}" ]; then
    VAL=$(grep -E '^LIFF_ID=' "$ROOT_DIR/.env" | tail -1 | cut -d= -f2- | tr -d "\"' \r" || true)
    [ -n "$VAL" ] && export LIFF_ID="$VAL"
  fi
fi

: "${LINE_CHANNEL_ACCESS_TOKEN:?請先設定 LINE_CHANNEL_ACCESS_TOKEN（或在根目錄 .env 填入）}"

API="https://api.line.me/v2/bot"
AUTH="Authorization: Bearer $LINE_CHANNEL_ACCESS_TOKEN"

json_field() {
  python3 -c "import sys, json; print(json.load(sys.stdin).get('$1', ''))"
}

prepare_json() {
  local src="$1"
  local dest="$2"
  if [ -n "${LIFF_ID:-}" ]; then
    sed "s/REPLACE_LIFF_ID/$LIFF_ID/g" "$src" > "$dest"
  else
    # 尚未設定 LIFF_ID 時轉成 postback 免得 LINE API 報 400
    sed -E 's#"type": "uri"[^}]+REPLACE_LIFF_ID[^}]*\}#"type": "postback", "data": "a=stats", "displayText": "功能選單"#g' "$src" > "$dest"
  fi
}

echo "🧹 正在清理舊的 rich menu 與 aliases..."
# 刪除舊 alias
for alias in "menu-invest" "menu-schedule"; do
  curl -sS -X DELETE "$API/richmenu/alias/$alias" -H "$AUTH" > /dev/null 2>&1 || true
done

# 刪除所有舊選單
MENUS=$(curl -sS "$API/richmenu/list" -H "$AUTH" | python3 -c "import sys, json; print(' '.join(m['richMenuId'] for m in json.load(sys.stdin).get('richmenus', [])))" || true)
for m in $MENUS; do
  curl -sS -X DELETE "$API/richmenu/$m" -H "$AUTH" > /dev/null 2>&1 || true
done

TMP1=$(mktemp)
TMP2=$(mktemp)
trap 'rm -f "$TMP1" "$TMP2"' EXIT

prepare_json "$DIR/richmenu_invest.json" "$TMP1"
prepare_json "$DIR/richmenu_schedule.json" "$TMP2"

echo "📤 上傳【選單 1：時光投資】..."
ID1=$(curl -sS -X POST "$API/richmenu" -H "$AUTH" -H 'Content-Type: application/json' -d @"$TMP1" | json_field richMenuId)
[ -n "$ID1" ] || { echo "❌ 建立時光投資選單失敗"; exit 1; }
curl -sS -f -X POST "https://api-data.line.me/v2/bot/richmenu/$ID1/content" -H "$AUTH" \
  -H 'Content-Type: image/png' --data-binary @"$DIR/richmenu_invest.png" > /dev/null

echo "📤 上傳【選單 2：行程管理】..."
ID2=$(curl -sS -X POST "$API/richmenu" -H "$AUTH" -H 'Content-Type: application/json' -d @"$TMP2" | json_field richMenuId)
[ -n "$ID2" ] || { echo "❌ 建立行程管理選單失敗"; exit 1; }
curl -sS -f -X POST "https://api-data.line.me/v2/bot/richmenu/$ID2/content" -H "$AUTH" \
  -H 'Content-Type: image/png' --data-binary @"$DIR/richmenu_schedule.png" > /dev/null

echo "🔗 綁定雙向切換 Alias..."
curl -sS -X POST "$API/richmenu/alias" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"richMenuAliasId\": \"menu-invest\", \"richMenuId\": \"$ID1\"}" > /dev/null
curl -sS -X POST "$API/richmenu/alias" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"richMenuAliasId\": \"menu-schedule\", \"richMenuId\": \"$ID2\"}" > /dev/null

echo "⭐ 設定預設選單為【時光投資】..."
curl -sS -f -X POST "$API/user/all/richmenu/$ID1" -H "$AUTH" > /dev/null

echo "🎉 完成！雙分頁圖文選單已成功設定！"
echo "   - 預設選單（時光投資）：$ID1 (alias: menu-invest)"
echo "   - 行程選單（行程管理）：$ID2 (alias: menu-schedule)"
