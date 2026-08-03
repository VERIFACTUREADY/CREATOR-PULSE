"""Errores de dominio con código legible por máquina y mensaje seguro en español."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Error base de la aplicación.

    `message` está pensado para mostrarse al usuario final (español, sin datos
    técnicos). `detail` sólo se expone cuando `APP_ENV != production`.
    """

    code: str = "error_interno"
    status_code: int = 500
    message: str = "Se ha producido un error inesperado."

    def __init__(
        self,
        message: str | None = None,
        *,
        detail: str | None = None,
        code: str | None = None,
        status_code: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.detail = detail
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.context = context or {}
        super().__init__(self.message)

    def to_dict(self, include_detail: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.context:
            payload["context"] = self.context
        if include_detail and self.detail:
            payload["detail"] = self.detail
        return payload


class ValidationError(AppError):
    code = "entrada_invalida"
    status_code = 422
    message = "Los datos enviados no son válidos."


class NotFoundError(AppError):
    code = "no_encontrado"
    status_code = 404
    message = "El recurso solicitado no existe."


class ConflictError(AppError):
    code = "conflicto"
    status_code = 409
    message = "La operación entra en conflicto con el estado actual."


class RateLimitError(AppError):
    code = "demasiadas_peticiones"
    status_code = 429
    message = "Has hecho demasiadas peticiones. Espera unos segundos e inténtalo de nuevo."


class FeatureDisabledError(AppError):
    code = "funcion_desactivada"
    status_code = 400
    message = "Esta función está desactivada en esta instalación."


# --- Errores específicos de YouTube -----------------------------------------


class YouTubeError(AppError):
    code = "youtube_error"
    status_code = 502
    message = "No se ha podido comunicar con la API de YouTube."


class YouTubeNotConfiguredError(YouTubeError):
    code = "youtube_sin_clave"
    status_code = 400
    message = (
        "No hay ninguna clave de la API de YouTube configurada. "
        "Añade YOUTUBE_API_KEY al fichero .env o usa el modo demostración."
    )


class YouTubeInvalidKeyError(YouTubeError):
    code = "youtube_clave_invalida"
    status_code = 400
    message = (
        "La clave de la API de YouTube no es válida o no tiene habilitada la YouTube Data API v3."
    )


class YouTubeQuotaExceededError(YouTubeError):
    code = "youtube_cuota_agotada"
    status_code = 429
    message = (
        "Se ha agotado la cuota diaria de la API de YouTube. "
        "Vuelve a intentarlo mañana o reduce el número de vídeos y comentarios."
    )


class ChannelNotFoundError(YouTubeError):
    code = "canal_no_encontrado"
    status_code = 404
    message = "No se ha encontrado ningún canal público con esa referencia."


class UnsupportedChannelReferenceError(YouTubeError):
    code = "referencia_canal_no_soportada"
    status_code = 422
    message = (
        "No se reconoce el formato del canal. Usa una URL de YouTube, "
        "un identificador @handle o un ID de canal que empiece por UC."
    )


class CommentsDisabledError(YouTubeError):
    code = "comentarios_desactivados"
    status_code = 200
    message = "Este vídeo tiene los comentarios desactivados."


# --- Errores del proveedor de IA --------------------------------------------


class AiProviderError(AppError):
    code = "ia_error"
    status_code = 502
    message = "El proveedor de IA externo no ha respondido correctamente."


class AiInvalidResponseError(AiProviderError):
    code = "ia_respuesta_invalida"
    message = "El proveedor de IA ha devuelto una respuesta con un formato inesperado."


# --- Errores del pipeline ----------------------------------------------------


class InsufficientDataError(AppError):
    code = "datos_insuficientes"
    status_code = 200
    message = "No hay suficientes datos públicos para generar un análisis fiable de este canal."


class AnalysisFailedError(AppError):
    code = "analisis_fallido"
    status_code = 500
    message = "El análisis no ha podido completarse."


__all__ = [
    "AiInvalidResponseError",
    "AiProviderError",
    "AnalysisFailedError",
    "AppError",
    "ChannelNotFoundError",
    "CommentsDisabledError",
    "ConflictError",
    "FeatureDisabledError",
    "InsufficientDataError",
    "NotFoundError",
    "RateLimitError",
    "UnsupportedChannelReferenceError",
    "ValidationError",
    "YouTubeError",
    "YouTubeInvalidKeyError",
    "YouTubeNotConfiguredError",
    "YouTubeQuotaExceededError",
]
