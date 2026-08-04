"""Dependencias compartidas de la API."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.auth import peer_is_trusted, require_access
from app.core.config import Settings, get_settings, settings
from app.core.errors import RateLimitError
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]

#: Ventanas deslizantes por cliente. Suficiente para un MVP de un solo proceso;
#: en producción con varias réplicas conviene moverlo a Redis.
_windows: dict[str, deque[float]] = defaultdict(deque)


def client_key(request: Request) -> str:
    """Identifica al cliente para el límite de peticiones.

    `X-Forwarded-For` sólo se cree si la conexión viene de una red de
    confianza. Un cliente directo puede poner esa cabecera a mano, así que
    fiarse de ella sin comprobar el origen convertía el límite en decorativo:
    bastaba con cambiar el valor en cada petición para no agotarlo nunca.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and peer_is_trusted(request):
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "anon"


def rate_limit(request: Request) -> None:
    """Límite de peticiones básico por IP."""
    if settings.app_env == "test":
        return

    key = client_key(request)
    now = time.monotonic()
    window = _windows[key]
    horizon = now - settings.rate_limit_window_seconds

    while window and window[0] < horizon:
        window.popleft()

    if len(window) >= settings.rate_limit_requests:
        raise RateLimitError(context={"retry_after_seconds": settings.rate_limit_window_seconds})
    window.append(now)


def reset_rate_limits() -> None:
    """Sólo para pruebas."""
    _windows.clear()


RateLimited = Depends(rate_limit)
#: Protege una ruta con el control de acceso configurado. Con `AUTH_MODE=none`
#: no hace nada, y en producción ese modo impide arrancar.
Protected = Depends(require_access)

__all__ = [
    "AppSettings",
    "DbSession",
    "Protected",
    "RateLimited",
    "client_key",
    "rate_limit",
    "reset_rate_limits",
]
