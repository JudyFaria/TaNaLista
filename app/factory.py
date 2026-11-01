"""Fábrica da aplicação FastAPI (monta API, middlewares e frontend)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.container import build_container
from app.presentation.api.errors import register_error_handlers
from app.presentation.api.routes import auth, events, groups, items

WEB_DIR = Path(__file__).parent / "presentation" / "web"

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    app = FastAPI(title="Lista de Compras", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.container = build_container(settings)
    register_error_handlers(app)

    @app.middleware("http")
    async def security_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        if not request.url.path.startswith("/api/docs"):
            response.headers.update(SECURITY_HEADERS)
        return response

    api = APIRouter(prefix="/api")

    @api.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok", "storage": settings.storage}

    for module in (auth, groups, items, events):
        api.include_router(module.router)
    app.include_router(api)

    # O frontend (PWA) é servido pelo mesmo servidor: um único endereço para tudo.
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app
