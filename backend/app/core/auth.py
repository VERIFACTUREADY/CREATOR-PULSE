"""Control de acceso delegado en un proxy autenticado.

Esta aplicación **no tiene usuarios propios**. Para una beta privada el patrón
razonable es ponerla detrás de algo que ya sepa autenticar (Cloudflare Access,
Azure Easy Auth, un reverse proxy con OIDC…) y que inyecte una cabecera
compartida.

Eso sólo es seguro si se cumplen dos condiciones, y las dos se comprueban aquí:

1. La cabecera se acepta **únicamente** si la petición llega desde una red de
   confianza configurada. Si la API queda expuesta directamente a internet,
   cualquiera podría añadir la cabecera a mano.
2. La comparación del valor es en tiempo constante, para no filtrar el secreto
   a través del tiempo de respuesta.

En `APP_ENV=production` la aplicación se niega a arrancar con `AUTH_MODE=none`:
es preferible un despliegue que falla a uno abierto al mundo sin saberlo.
"""

from __future__ import annotations

import ipaddress
from secrets import compare_digest

from fastapi import Request

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthenticationRequiredError(AppError):
    code = "autenticacion_requerida"
    status_code = 401
    message = "Esta instalación requiere autenticación para acceder."


class AuthMisconfiguredError(AppError):
    code = "autenticacion_mal_configurada"
    status_code = 500
    message = (
        "El control de acceso está activado pero incompleto. "
        "Revisa TRUSTED_AUTH_HEADER, TRUSTED_AUTH_VALUE y TRUSTED_PROXY_NETWORKS."
    )


class InsecureDeploymentError(RuntimeError):
    """Se lanza al arrancar: producción sin ninguna protección de acceso."""


def verify_startup_configuration() -> None:
    """Impide arrancar en producción sin control de acceso.

    Se llama al construir la aplicación, no en cada petición: un despliegue mal
    configurado debe fallar de inmediato y de forma visible.
    """
    # El modo propietario maneja tokens de Google de canales reales. Dejarlo
    # accesible sin ninguna protección de acceso es peor que en el modo
    # público: cualquiera con acceso de red podría iniciar una conexión OAuth
    # o leer las analíticas privadas de un canal ya conectado.
    if settings.enable_owner_mode and settings.auth_mode == "none":
        raise InsecureDeploymentError(
            "ENABLE_OWNER_MODE=true con AUTH_MODE=none. El modo propietario da acceso a "
            "métricas privadas y a la conexión OAuth de un canal real, así que exige "
            "control de acceso. Configura AUTH_MODE=trusted_proxy o desactiva el modo "
            "propietario."
        )

    if not settings.is_production:
        if settings.auth_mode == "none":
            logger.warning(
                "sin_autenticacion",
                mensaje=(
                    "La API está abierta: cualquiera con acceso de red puede lanzar "
                    "análisis, borrar canales y consumir cuota. Vale para desarrollo; "
                    "no expongas esto a internet."
                ),
            )
        return

    if settings.auth_mode == "none":
        raise InsecureDeploymentError(
            "APP_ENV=production con AUTH_MODE=none. Esta aplicación no tiene "
            "usuarios propios: colócala detrás de un proxy autenticado y configura "
            "AUTH_MODE=trusted_proxy con TRUSTED_AUTH_HEADER, TRUSTED_AUTH_VALUE y "
            "TRUSTED_PROXY_NETWORKS."
        )
    if not settings.auth_configured:
        raise InsecureDeploymentError(
            "AUTH_MODE=trusted_proxy incompleto: faltan TRUSTED_AUTH_HEADER, "
            "TRUSTED_AUTH_VALUE o TRUSTED_PROXY_NETWORKS."
        )


def peer_is_trusted(request: Request) -> bool:
    """¿La conexión viene de una red desde la que se acepta la cabecera?"""
    peer = request.client.host if request.client else None
    if not peer:
        return False
    try:
        address = ipaddress.ip_address(peer)
    except ValueError:
        return False

    for raw in settings.trusted_proxy_network_list:
        try:
            network = ipaddress.ip_network(raw, strict=False)
        except ValueError:
            logger.warning("red_de_confianza_invalida", valor=raw)
            continue
        if address in network:
            return True
    return False


def require_access(request: Request) -> None:
    """Dependencia de FastAPI que protege una ruta."""
    if settings.auth_mode == "none":
        # En producción esto no ocurre: el arranque ya habría fallado.
        return

    if not settings.auth_configured:
        raise AuthMisconfiguredError(detail="trusted_proxy sin cabecera, valor o redes")

    if not peer_is_trusted(request):
        # No se dice si la cabecera era válida: desde fuera de la red de
        # confianza la respuesta es siempre la misma.
        logger.warning("acceso_desde_red_no_confiable")
        raise AuthenticationRequiredError(detail="origen fuera de las redes de confianza")

    presented = request.headers.get(settings.trusted_auth_header, "")
    if not compare_digest(presented, settings.trusted_auth_value):
        raise AuthenticationRequiredError(detail="cabecera de autenticación ausente o incorrecta")


__all__ = [
    "AuthMisconfiguredError",
    "AuthenticationRequiredError",
    "InsecureDeploymentError",
    "peer_is_trusted",
    "require_access",
    "verify_startup_configuration",
]
