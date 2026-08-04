"""Cifrado de tokens OAuth en reposo.

Los tokens de Google dan acceso de lectura a las analíticas privadas de un
canal, así que no pueden guardarse en claro: quien leyera la base de datos
tendría ese acceso. Se cifran con Fernet (AES-128-CBC + HMAC-SHA256) usando la
clave de `OAUTH_TOKEN_ENCRYPTION_KEY`.

Si el modo propietario está activo y no hay clave, la aplicación falla al
arrancar el flujo en lugar de guardar los tokens sin cifrar.
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.errors import AppError


class EncryptionNotConfiguredError(AppError):
    code = "cifrado_no_configurado"
    status_code = 500
    message = (
        "El modo propietario requiere una clave de cifrado para los tokens. "
        "Genera una con `python -m app.cli generar-clave` y añádela a "
        "OAUTH_TOKEN_ENCRYPTION_KEY."
    )


class DecryptionError(AppError):
    code = "descifrado_fallido"
    status_code = 500
    message = (
        "No se ha podido descifrar el token almacenado. "
        "Si has cambiado OAUTH_TOKEN_ENCRYPTION_KEY, vuelve a conectar el canal."
    )


def generate_key() -> str:
    """Genera una clave Fernet nueva, lista para el fichero `.env`."""
    return Fernet.generate_key().decode()


@lru_cache(maxsize=1)
def _cipher() -> Fernet:
    raw = settings.oauth_token_encryption_key.strip()
    if not raw:
        raise EncryptionNotConfiguredError(detail="OAUTH_TOKEN_ENCRYPTION_KEY vacía")
    try:
        return Fernet(raw.encode())
    except (ValueError, TypeError) as exc:
        raise EncryptionNotConfiguredError(
            "La clave de cifrado de tokens no tiene un formato válido. "
            "Debe ser una clave Fernet (base64 urlsafe de 32 bytes).",
            detail=str(exc),
        ) from exc


def encryption_available() -> bool:
    """Indica si el cifrado puede usarse, sin lanzar."""
    try:
        _cipher()
        return True
    except EncryptionNotConfiguredError:
        return False


def encrypt(value: str) -> bytes:
    """Cifra un token. Nunca registra el valor."""
    return _cipher().encrypt(value.encode())


def decrypt(value: bytes | memoryview | None) -> str | None:
    """Descifra un token almacenado. Devuelve `None` si no había nada."""
    if value is None:
        return None
    raw = bytes(value)
    if not raw:
        return None
    try:
        return _cipher().decrypt(raw).decode()
    except InvalidToken as exc:
        raise DecryptionError(detail="Fernet: token inválido o clave distinta") from exc


def reset_cache() -> None:
    """Limpia la clave cacheada. Sólo para pruebas."""
    _cipher.cache_clear()


__all__ = [
    "DecryptionError",
    "EncryptionNotConfiguredError",
    "decrypt",
    "encrypt",
    "encryption_available",
    "generate_key",
    "reset_cache",
]
