"""Dependencias compartidas de la API."""

from __future__ import annotations

import re
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


#: Cabecera con la identidad que fija el proxy del frontend. El cliente no
#: puede elegir su valor: se deriva de una cookie firmada que no sabe fabricar,
#: y el proxy borra cualquier copia que llegue del navegador.
IDENTITY_HEADER = "x-creatorpulse-identity"

#: Longitud máxima de una clave de rate limit. Sin esto, un cliente podría
#: llenar el diccionario en memoria con claves larguísimas.
MAX_KEY_LENGTH = 64

_VALID_KEY = re.compile(r"^[A-Za-z0-9_.:\-]{1,64}$")


def _sane(value: str) -> str | None:
    """Devuelve la clave si tiene una forma aceptable, o `None`."""
    candidate = value.strip()[:MAX_KEY_LENGTH]
    return candidate if _VALID_KEY.match(candidate) else None


def client_key(request: Request) -> str:
    """Identifica al cliente para el límite de peticiones.

    El orden importa y es deliberado:

    1. La identidad que fija el proxy del frontend, si la petición viene de una
       red de confianza. El visitante no puede escogerla.
    2. `X-Forwarded-For`, sólo desde una red de confianza y **sólo** si el
       proxy no ha puesto identidad. Un cliente directo puede inventarse esa
       cabecera, así que fiarse de ella sin comprobar el origen convertía el
       límite en decorativo: bastaba con cambiar el valor en cada petición.
    3. La IP real de la conexión.

    Toda clave se valida en formato y longitud antes de usarse.
    """
    trusted = peer_is_trusted(request)

    if trusted:
        identity = request.headers.get(IDENTITY_HEADER)
        if identity:
            sane = _sane(identity)
            if sane:
                return f"id:{sane}"

        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            sane = _sane(forwarded.split(",")[0])
            if sane:
                return f"ip:{sane}"

    host = request.client.host if request.client else "anon"
    return f"ip:{_sane(host) or 'anon'}"


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
