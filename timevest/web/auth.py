"""以 LIFF access token 驗證身分：向 LINE 取得 userId，必須是成員，並把它設為本次請求的目前使用者。"""
import time

import requests
from fastapi import Header, HTTPException
from fastapi.concurrency import run_in_threadpool

from timevest.line import users

_CACHE: dict = {}  # token -> (user_id, expires_at)
_TTL = 300


def _profile_user_id(token: str):
    hit = _CACHE.get(token)
    if hit and hit[1] > time.time():
        return hit[0]
    try:
        res = requests.get("https://api.line.me/v2/profile", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    except requests.RequestException:
        raise HTTPException(503, "無法連線 LINE 驗證服務")
    if res.status_code != 200:
        return None
    user_id = res.json().get("userId")
    _CACHE[token] = (user_id, time.time() + _TTL)
    return user_id


async def require_member(authorization: str = Header(default="")) -> str:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "缺少登入憑證")
    user_id = await run_in_threadpool(_profile_user_id, authorization[7:].strip())
    if not user_id:
        raise HTTPException(401, "登入憑證無效或已過期")
    if not users.owner_id():
        raise HTTPException(403, "尚未設定擁有者，請先在 LINE 對官方帳號傳任意訊息")
    if not users.is_member(user_id):
        raise HTTPException(403, "尚未加入，請先在 LINE 輸入邀請碼")
    users.set_current(user_id)  # async 依賴在請求的 context 內執行，後續同步 endpoint 會繼承
    return user_id
