"""timeVest LINE OA：用 LINE 記錄專注時間、合併行事曆並提醒。與 Gradio 共用同一個 TimeVestService。"""
from .config import is_enabled


def serve_with_gradio(blocks, service, host: str, port: int) -> None:
    """把 LINE webhook（/line/webhook）與 Gradio 掛在同一個 FastAPI，共用 service 的記憶體狀態。"""
    import gradio as gr
    import uvicorn
    from fastapi import FastAPI

    from . import ledger, state
    from .jobs.scheduler import start_scheduler
    from .routes import router

    ledger.bind_service(service)
    state.ensure_data_dir()
    start_scheduler()

    api = FastAPI()
    api.include_router(router, prefix="/line")
    api = gr.mount_gradio_app(api, blocks, path="/")
    uvicorn.run(api, host=host, port=port)


__all__ = ["is_enabled", "serve_with_gradio"]
