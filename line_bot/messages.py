from urllib.parse import parse_qsl, urlencode

MAX_QUICK_REPLIES = 13


def truncate(text: str, max_len: int) -> str:
    text = str(text)
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def text_msg(text: str, quick_replies=None) -> dict:
    msg = {"type": "text", "text": text}
    if quick_replies:
        msg["quickReply"] = {"items": quick_replies[:MAX_QUICK_REPLIES]}
    return msg


def flex_msg(alt_text: str, contents: dict) -> dict:
    return {"type": "flex", "altText": alt_text, "contents": contents}


def qr_postback(label: str, data: str, display_text=None) -> dict:
    return {
        "type": "action",
        "action": {"type": "postback", "label": truncate(label, 20), "data": data, "displayText": display_text or label},
    }


def postback_data(**params) -> str:
    return urlencode(params)


def parse_postback(data: str) -> dict:
    return dict(parse_qsl(data))


class QR:
    start = staticmethod(lambda: qr_postback("▶ 開始記錄", "a=start"))
    end = staticmethod(lambda: qr_postback("⏹ 結束記錄", "a=end"))
    stats = staticmethod(lambda: qr_postback("📊 今日統計", "a=stats"))
    skip = staticmethod(lambda: qr_postback("略過", "a=skip"))
    cancel = staticmethod(lambda: qr_postback("取消", "a=cancel"))


def help_message() -> dict:
    return text_msg(
        "\n".join(
            [
                "⏱ timeVest 使用方式",
                "",
                "▶ 開始記錄：選擇活動（閱讀會再問書名）後開始計時",
                "⏹ 結束記錄：停止計時，可填頁數與備註",
                "📅 今日／本週行程：合併上課與教課行事曆",
                "📊 今日統計｜💰 我的帳戶",
                "",
                "也可以直接輸入「開始」「結束」「取消」。",
            ]
        ),
        [QR.start(), QR.stats()],
    )
