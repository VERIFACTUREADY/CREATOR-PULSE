"""Utilidades de privacidad: anonimización estable de autores y saneado de texto."""

from __future__ import annotations

import hashlib
import re

from app.core.config import settings

_HANDLE_RE = re.compile(r"@[\w.\-]{2,}")
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[\w.\-+]+@[\w\-]+\.[\w.\-]+")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().\-]{7,}\d)(?!\d)")


def hash_author_id(raw_author_id: str | None, salt: str | None = None) -> str | None:
    """Devuelve un identificador de autor estable y no reversible.

    Se usa únicamente para deduplicar y para detectar spam repetido. Nunca se
    almacena el nombre público ni la foto de perfil del autor.
    """
    if not raw_author_id:
        return None
    salt_value = salt if salt is not None else settings.author_hash_salt
    digest = hashlib.sha256(f"{salt_value}:{raw_author_id}".encode())
    return f"a_{digest.hexdigest()[:24]}"


def redact_personal_data(text: str, *, anonymize: bool | None = None) -> str:
    """Sustituye handles, correos, teléfonos y URLs por marcadores.

    Se aplica a los textos que se muestran como ejemplos representativos y a los
    que se envían a un proveedor de IA externo. No se aplica al texto almacenado
    para el análisis, que conserva su significado original.
    """
    should_anonymize = settings.anonymize_comment_authors if anonymize is None else anonymize
    if not should_anonymize:
        return text
    out = _EMAIL_RE.sub("[correo]", text)
    out = _URL_RE.sub("[enlace]", out)
    out = _PHONE_RE.sub("[teléfono]", out)
    out = _HANDLE_RE.sub("[usuario]", out)
    return out


def truncate_for_display(text: str, max_chars: int = 280) -> str:
    """Recorta un texto para mostrarlo como ejemplo representativo."""
    clean = " ".join(text.split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 1].rstrip() + "…"


__all__ = ["hash_author_id", "redact_personal_data", "truncate_for_display"]
