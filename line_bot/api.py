import base64
import hashlib
import hmac

import requests

from . import config, state

API = "https://api.line.me/v2/bot/"


def _call(path: str, payload: dict) -> None:
    try:
        res = requests.post(
            API + path,
            json=payload,
            headers={"Authorization": f"Bearer {config.CHANNEL_TOKEN}"},
            timeout=10,
        )
        if res.status_code >= 300:
            print(f"[LINE] {path} {res.status_code} {res.text}")
    except requests.RequestException as e:
        print(f"[LINE] {path} failed: {e}")


def _as_list(messages):
    return messages if isinstance(messages, list) else [messages]


# reply 不計入每月訊息額度；push 會計入
def reply(reply_token: str, messages) -> None:
    _call("message/reply", {"replyToken": reply_token, "messages": _as_list(messages)})


def push(messages) -> None:
    owner = state.get_owner_id()
    if not owner:
        print("[LINE] 尚未綁定擁有者，略過推播")
        return
    _call("message/push", {"to": owner, "messages": _as_list(messages)})


def verify_signature(body: bytes, signature) -> bool:
    if not signature:
        return False
    expected = base64.b64encode(hmac.new(config.CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(expected, signature)
