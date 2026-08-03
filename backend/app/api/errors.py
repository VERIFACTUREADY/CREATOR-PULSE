"""Manejadores de error que producen respuestas consistentes en español."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import correlation_id_var, get_logger

logger = get_logger(__name__)


def _payload(
    code: str,
    message: str,
    *,
    detail: str | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if context:
        error["context"] = context
    # El detalle técnico nunca se expone en producción.
    if detail and not settings.is_production:
        error["detail"] = detail
    return {"ok": False, "data": None, "error": error, "request_id": correlation_id_var.get()}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
        # Los errores "de negocio" con status 200 se devuelven como 400 en HTTP:
        # una respuesta de error nunca debe parecer un éxito.
        status_code = exc.status_code if exc.status_code >= 400 else 400
        logger.info("app_error", code=exc.code, status=status_code)
        return JSONResponse(
            status_code=status_code,
            content=_payload(exc.code, exc.message, detail=exc.detail, context=exc.context),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_payload(
                "entrada_invalida",
                "Los datos enviados no son válidos. Revisa el formulario.",
                detail=str(exc.errors()),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        messages = {
            404: "El recurso solicitado no existe.",
            405: "Método no permitido para esta dirección.",
            429: "Has hecho demasiadas peticiones. Espera unos segundos.",
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(
                f"http_{exc.status_code}",
                messages.get(exc.status_code, "Se ha producido un error en la petición."),
                detail=str(exc.detail),
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error("database_error", error=type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content=_payload(
                "base_datos_no_disponible",
                "No se ha podido acceder a la base de datos. Inténtalo de nuevo en unos momentos.",
                detail=str(exc),
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error")
        return JSONResponse(
            status_code=500,
            content=_payload(
                "error_interno",
                "Se ha producido un error inesperado. Vuelve a intentarlo.",
                detail=f"{type(exc).__name__}: {exc}",
            ),
        )


__all__ = ["register_error_handlers"]
