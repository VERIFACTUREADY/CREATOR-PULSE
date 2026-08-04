"""Aplicación FastAPI de CreatorPulse AI."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import Protected
from app.api.errors import register_error_handlers
from app.api.routes import channels, comparisons, health, oauth, runs
from app.core.auth import verify_startup_configuration
from app.core.config import settings
from app.core.logging import bind_correlation_id, configure_logging, get_logger
from app.db.session import detect_pgvector

logger = get_logger(__name__)

DESCRIPTION = """
API de **CreatorPulse AI**: analiza canales públicos de YouTube y convierte los
comentarios y las métricas públicas en recomendaciones de contenido con evidencia.

* Sólo se usan endpoints oficiales de la YouTube Data API v3.
* El cálculo numérico no depende de ningún LLM.
* Toda recomendación incluye su evidencia y su nivel de confianza.
"""


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level, settings.log_json)
    pgvector = detect_pgvector()
    logger.info(
        "api_starting",
        env=settings.app_env,
        demo_mode=settings.enable_demo_mode,
        youtube_configured=settings.youtube_configured,
        ai_provider=settings.ai_provider,
        pgvector=pgvector,
    )
    yield
    logger.info("api_stopping")


def create_app() -> FastAPI:
    # Un despliegue de producción sin control de acceso falla aquí, en el
    # arranque, en lugar de quedar abierto sin que nadie se entere.
    verify_startup_configuration()

    app = FastAPI(
        title=settings.app_name,
        description=DESCRIPTION,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS explícito: nunca se usa el comodín.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
        max_age=600,
    )

    @app.middleware("http")
    async def correlation_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = bind_correlation_id(request.headers.get("x-request-id"))
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        # No se registran cuerpos ni parámetros de consulta: pueden llevar datos.
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    register_error_handlers(app)

    # `health` queda fuera del control de acceso: un chequeo de salud tiene que
    # responder aunque el proxy no esté delante. Su ruta de configuración sí se
    # protege, dentro del propio router.
    app.include_router(health.router, prefix="/api")
    app.include_router(channels.router, prefix="/api", dependencies=[Protected])
    app.include_router(runs.router, prefix="/api", dependencies=[Protected])
    app.include_router(runs.export_router, prefix="/api", dependencies=[Protected])
    app.include_router(comparisons.router, prefix="/api", dependencies=[Protected])
    # El router de OAuth se protege ruta a ruta: el retorno de Google no puede
    # exigir la cabecera, porque quien llega ahí es el navegador del creador.
    app.include_router(oauth.router, prefix="/api")

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


app = create_app()

__all__ = ["app", "create_app"]
