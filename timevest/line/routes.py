import json

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from . import worker
from .api import verify_signature
from .flows.router import handle_event

router = APIRouter()


@router.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    if not verify_signature(body, request.headers.get("x-line-signature")):
        return PlainTextResponse("invalid signature", status_code=401)
    # 先回 200，再交給背景執行緒處理（BigQuery 查詢可能較慢）
    for ev in json.loads(body).get("events", []):
        worker.submit(handle_event, ev)
    return PlainTextResponse("OK")


@router.get("/healthz")
def healthz():
    return {"ok": True}
