from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.notifications.telegram import TelegramNotifier


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    notifier = TelegramNotifier(settings)
    await notifier.send(f"{settings.app_name} startup: env={settings.app_env}, live_trading={settings.live_trading_enabled}, sandbox={settings.exchange_sandbox}")
    try:
        yield
    finally:
        await notifier.send(f"{settings.app_name} shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_production_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.show_api_docs else None,
        redoc_url="/redoc" if settings.show_api_docs else None,
        openapi_url="/openapi.json" if settings.show_api_docs else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        await TelegramNotifier(settings).send(f"Unhandled API error on {request.method} {request.url.path}: {type(exc).__name__}: {exc}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
