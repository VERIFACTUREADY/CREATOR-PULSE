"""Parser de referencias de canal de YouTube.

Acepta URLs completas, handles (`@creador`), IDs de canal (`UC…`) y las URLs
heredadas `/user/` y `/c/`. No hace ninguna petición de red: sólo normaliza y
clasifica la entrada para que el resolutor sepa qué endpoint usar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import unquote, urlparse

from app.core.errors import UnsupportedChannelReferenceError

#: Un ID de canal de YouTube empieza por `UC` y tiene 24 caracteres.
CHANNEL_ID_RE = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
#: Un handle válido: 3-30 caracteres alfanuméricos, guiones, guiones bajos y puntos.
HANDLE_RE = re.compile(r"^[A-Za-z0-9._-]{3,30}$")

_ALLOWED_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be",
    }
)


class ReferenceKind(StrEnum):
    CHANNEL_ID = "channel_id"
    HANDLE = "handle"
    LEGACY_USER = "legacy_user"
    LEGACY_CUSTOM = "legacy_custom"


@dataclass(frozen=True, slots=True)
class ChannelReference:
    """Referencia de canal normalizada."""

    kind: ReferenceKind
    value: str
    raw: str

    @property
    def is_direct_id(self) -> bool:
        return self.kind is ReferenceKind.CHANNEL_ID

    def as_display(self) -> str:
        if self.kind is ReferenceKind.HANDLE:
            return f"@{self.value}"
        return self.value


def _normalise_handle(value: str) -> str:
    handle = unquote(value).strip().lstrip("@")
    if not HANDLE_RE.match(handle):
        raise UnsupportedChannelReferenceError(
            "El identificador @handle no tiene un formato válido. "
            "Debe tener entre 3 y 30 caracteres alfanuméricos.",
            detail=f"handle inválido: {value!r}",
        )
    return handle


def _from_path(path: str, raw: str) -> ChannelReference:
    """Interpreta la ruta de una URL de YouTube."""
    parts = [p for p in path.split("/") if p]
    if not parts:
        raise UnsupportedChannelReferenceError(
            "La URL no apunta a ningún canal de YouTube.", detail=f"ruta vacía en {raw!r}"
        )

    head = parts[0]

    if head.startswith("@"):
        return ChannelReference(ReferenceKind.HANDLE, _normalise_handle(head), raw)

    if head == "channel":
        if len(parts) < 2:
            raise UnsupportedChannelReferenceError(
                "La URL de canal no incluye ningún identificador.",
                detail=f"falta el ID en {raw!r}",
            )
        channel_id = unquote(parts[1]).strip()
        if not CHANNEL_ID_RE.match(channel_id):
            raise UnsupportedChannelReferenceError(
                "El identificador de canal no es válido. Debe empezar por UC "
                "y tener 24 caracteres.",
                detail=f"ID inválido: {channel_id!r}",
            )
        return ChannelReference(ReferenceKind.CHANNEL_ID, channel_id, raw)

    if head == "user":
        if len(parts) < 2:
            raise UnsupportedChannelReferenceError(
                "La URL de usuario no incluye ningún nombre.", detail=f"falta el usuario en {raw!r}"
            )
        return ChannelReference(ReferenceKind.LEGACY_USER, unquote(parts[1]).strip(), raw)

    if head == "c":
        if len(parts) < 2:
            raise UnsupportedChannelReferenceError(
                "La URL personalizada no incluye ningún nombre.",
                detail=f"falta el nombre en {raw!r}",
            )
        return ChannelReference(ReferenceKind.LEGACY_CUSTOM, unquote(parts[1]).strip(), raw)

    # Rutas que nunca corresponden a un canal.
    if head in {"watch", "playlist", "shorts", "results", "feed", "embed", "live", "hashtag"}:
        raise UnsupportedChannelReferenceError(
            "Esa URL apunta a un vídeo o a una búsqueda, no a un canal. "
            "Introduce la URL del canal.",
            detail=f"ruta no soportada: /{head}",
        )

    # `youtube.com/NombrePersonalizado` (formato heredado sin prefijo).
    return ChannelReference(ReferenceKind.LEGACY_CUSTOM, unquote(head).strip(), raw)


def parse_channel_reference(raw_input: str) -> ChannelReference:
    """Convierte la entrada del usuario en una `ChannelReference` normalizada.

    Lanza `UnsupportedChannelReferenceError` con un mensaje en español si la
    entrada no puede interpretarse.
    """
    if raw_input is None:
        raise UnsupportedChannelReferenceError()
    raw = raw_input.strip()
    if not raw:
        raise UnsupportedChannelReferenceError(
            "Introduce la URL, el @handle o el ID del canal que quieres analizar.",
            detail="entrada vacía",
        )
    if len(raw) > 2048:
        raise UnsupportedChannelReferenceError(
            "La referencia del canal es demasiado larga.", detail="entrada > 2048 caracteres"
        )

    # ID de canal en crudo.
    if CHANNEL_ID_RE.match(raw):
        return ChannelReference(ReferenceKind.CHANNEL_ID, raw, raw)

    # Handle en crudo.
    if raw.startswith("@"):
        return ChannelReference(ReferenceKind.HANDLE, _normalise_handle(raw), raw)

    # A partir de aquí se espera algo con forma de URL.
    candidate = raw
    if "://" not in candidate:
        if not candidate.lower().startswith(("youtube.com", "www.youtube.com", "m.youtube.com")):
            # Texto suelto: se acepta como handle si su forma lo permite.
            if HANDLE_RE.match(candidate):
                return ChannelReference(ReferenceKind.HANDLE, _normalise_handle(candidate), raw)
            raise UnsupportedChannelReferenceError(
                "No se reconoce el formato. Usa una URL de YouTube, un @handle "
                "o un ID de canal que empiece por UC.",
                detail=f"entrada no reconocida: {raw!r}",
            )
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise UnsupportedChannelReferenceError(
            "Sólo se aceptan direcciones http o https de youtube.com.",
            detail=f"esquema no soportado: {parsed.scheme!r}",
        )
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        # Evita SSRF: nunca se descarga una URL arbitraria proporcionada por el usuario.
        raise UnsupportedChannelReferenceError(
            "La dirección debe pertenecer a youtube.com.",
            detail=f"host no permitido: {host!r}",
        )

    return _from_path(parsed.path, raw)


def is_valid_channel_id(value: str) -> bool:
    return bool(CHANNEL_ID_RE.match(value.strip()))


def is_valid_video_id(value: str) -> bool:
    """Un ID de vídeo son 11 caracteres del alfabeto base64url."""
    return bool(re.match(r"^[A-Za-z0-9_-]{11}$", value.strip()))


__all__ = [
    "CHANNEL_ID_RE",
    "HANDLE_RE",
    "ChannelReference",
    "ReferenceKind",
    "is_valid_channel_id",
    "is_valid_video_id",
    "parse_channel_reference",
]
