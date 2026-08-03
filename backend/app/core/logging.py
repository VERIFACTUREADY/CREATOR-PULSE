"""Logging estructurado con IDs de correlación.

Nunca se registran claves de API, tokens, prompts completos ni datasets de
comentarios: los procesadores de este módulo redactan las claves sensibles.
"""

from __future__ import annotations

import logging
import sys
import uuid
from collections.abc import MutableMapping
from contextvars import ContextVar
from typing import Any

import structlog

#: ID de correlación de la petición o del trabajo en curso.
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
#: ID de la ejecución de análisis en curso (sólo en el worker).
analysis_run_id_var: ContextVar[str | None] = ContextVar("analysis_run_id", default=None)

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "youtube_api_key",
        "anthropic_api_key",
        "openai_api_key",
        "authorization",
        "access_token",
        "refresh_token",
        "client_secret",
        "password",
        "key",
        "token",
        "prompt",
        "system_prompt",
        "comments",
        "comment_texts",
    }
)


def new_correlation_id() -> str:
    return uuid.uuid4().hex[:16]


def bind_correlation_id(value: str | None = None) -> str:
    cid = value or new_correlation_id()
    correlation_id_var.set(cid)
    return cid


def bind_analysis_run_id(value: str | None) -> None:
    analysis_run_id_var.set(value)


def _redact(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Sustituye valores sensibles por un marcador."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "[redacted]"
    return event_dict


def _add_context(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    cid = correlation_id_var.get()
    if cid:
        event_dict.setdefault("correlation_id", cid)
    run_id = analysis_run_id_var.get()
    if run_id:
        event_dict.setdefault("analysis_run_id", run_id)
    return event_dict


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    """Configura structlog y el logging estándar una sola vez."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level, force=True)
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(max(log_level, logging.WARNING))

    renderer: Any = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _add_context,
            _redact,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "creator_signal") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]


__all__ = [
    "analysis_run_id_var",
    "bind_analysis_run_id",
    "bind_correlation_id",
    "configure_logging",
    "correlation_id_var",
    "get_logger",
    "new_correlation_id",
]
