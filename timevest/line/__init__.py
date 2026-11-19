"""timeVest LINE OA：用 LINE 記錄專注時間、合併行事曆並提醒；LIFF 網頁共用同一個 TimeVestService。"""
from .config import is_enabled


def build_api(service_factory):
    """建立 FastAPI：/line/*（Webhook）、/api/*（LIFF 用 REST）、/liff（靜態頁面）。"""
    import os

    from fastapi import FastAPI
    from fastapi.responses import RedirectResponse
    from fastapi.staticfiles import StaticFiles

    from timevest.web.routes import public as web_public, router as web_router

    from . import state, users
    from .jobs.scheduler import start_scheduler
    from .routes import router

    users.bind_factory(service_factory)
    state.ensure_data_dir()
    start_scheduler()

    api = FastAPI(title="timeVest")
    api.include_router(router, prefix="/line")
    api.include_router(web_public, prefix="/api")
    api.include_router(web_router, prefix="/api")

    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "static")  # timevest/web/static
    api.mount("/liff", StaticFiles(directory=static_dir, html=True), name="liff")

    @api.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/liff/")

    return api


def serve(service_factory, host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(build_api(service_factory), host=host, port=port)


__all__ = ["is_enabled", "build_api", "serve"]
