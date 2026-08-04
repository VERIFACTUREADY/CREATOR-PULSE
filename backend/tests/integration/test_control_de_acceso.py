"""Control de acceso delegado en un proxy autenticado.

La aplicación no tiene usuarios propios, así que la única protección honesta
para una beta es exigir un proxy autenticado delante. Lo que se comprueba aquí
es que esa protección no sea decorativa: que producción no arranque sin ella y
que la cabecera no valga desde cualquier sitio.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from app.api.deps import get_db
from app.core.auth import InsecureDeploymentError, verify_startup_configuration
from app.core.config import settings
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

CABECERA = "X-Auth-Token"
SECRETO = "un-secreto-largo-de-proxy"


@pytest.fixture
def proxy_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "auth_mode", "trusted_proxy")
    monkeypatch.setattr(settings, "trusted_auth_header", CABECERA)
    monkeypatch.setattr(settings, "trusted_auth_value", SECRETO)
    # El TestClient se presenta como `testclient`, no como una IP, así que las
    # pruebas que necesiten un origen de confianza lo simulan explícitamente.
    monkeypatch.setattr(settings, "trusted_proxy_networks", "127.0.0.1/32")


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app, raise_server_exceptions=False, client=("127.0.0.1", 1234)) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def client_externo(session: Session) -> Iterator[TestClient]:
    """Cliente que llega desde una IP fuera de las redes de confianza."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app, raise_server_exceptions=False, client=("203.0.113.7", 1234)) as test:
        yield test
    app.dependency_overrides.clear()


# --- Arranque ---------------------------------------------------------------


def test_produccion_sin_autenticacion_no_arranca(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "auth_mode", "none")

    with pytest.raises(InsecureDeploymentError) as excinfo:
        verify_startup_configuration()

    assert "AUTH_MODE" in str(excinfo.value)


def test_produccion_con_trusted_proxy_incompleto_no_arranca(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "auth_mode", "trusted_proxy")
    monkeypatch.setattr(settings, "trusted_auth_header", CABECERA)
    monkeypatch.setattr(settings, "trusted_auth_value", "")

    with pytest.raises(InsecureDeploymentError):
        verify_startup_configuration()


def test_produccion_bien_configurada_arranca(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "auth_mode", "trusted_proxy")
    monkeypatch.setattr(settings, "trusted_auth_header", CABECERA)
    monkeypatch.setattr(settings, "trusted_auth_value", SECRETO)
    monkeypatch.setattr(settings, "trusted_proxy_networks", "10.0.0.0/8")

    verify_startup_configuration()  # no debe lanzar


def test_desarrollo_sin_autenticacion_arranca_con_aviso(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Arranca, pero deja constancia de que la instalación está abierta."""
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "auth_mode", "none")

    avisos: list[str] = []
    monkeypatch.setattr(
        "app.core.auth.logger",
        type("L", (), {"warning": lambda _self, evento, **_kw: avisos.append(evento)})(),
    )

    verify_startup_configuration()

    assert "sin_autenticacion" in avisos


# --- Rutas protegidas -------------------------------------------------------


def test_health_sigue_abierto(client: TestClient, proxy_auth: None) -> None:
    """Un chequeo de salud debe responder aunque no haya proxy delante."""
    respuesta = client.get("/api/health")
    assert respuesta.status_code in {200, 503}


def test_sin_cabecera_se_rechaza(client: TestClient, proxy_auth: None) -> None:
    respuesta = client.get("/api/channels")
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "autenticacion_requerida"


def test_con_cabecera_correcta_se_permite(client: TestClient, proxy_auth: None) -> None:
    respuesta = client.get("/api/channels", headers={CABECERA: SECRETO})
    assert respuesta.status_code == 200


def test_cabecera_incorrecta_se_rechaza(client: TestClient, proxy_auth: None) -> None:
    respuesta = client.get("/api/channels", headers={CABECERA: "casi-el-secreto"})
    assert respuesta.status_code == 401


def test_cabecera_valida_desde_red_no_confiable_se_rechaza(
    client_externo: TestClient, proxy_auth: None
) -> None:
    """El punto entero: la cabecera sólo vale desde donde está el proxy."""
    respuesta = client_externo.get("/api/channels", headers={CABECERA: SECRETO})
    assert respuesta.status_code == 401


def test_configuracion_publica_esta_protegida(client: TestClient, proxy_auth: None) -> None:
    assert client.get("/api/config/public").status_code == 401
    assert client.get("/api/config/public", headers={CABECERA: SECRETO}).status_code == 200


@pytest.mark.parametrize(
    "metodo,ruta",
    [
        ("POST", "/api/channels/analyse"),
        ("POST", "/api/channels/resolve"),
        ("POST", "/api/comparisons"),
        ("GET", "/api/usage/youtube"),
        ("GET", "/api/channels/demo"),
        ("GET", "/api/channels/estimate"),
    ],
)
def test_rutas_sensibles_exigen_acceso(
    client: TestClient, proxy_auth: None, metodo: str, ruta: str
) -> None:
    respuesta = client.request(metodo, ruta, json={} if metodo == "POST" else None)
    assert respuesta.status_code == 401, f"{metodo} {ruta} quedó sin protección"


def test_borrar_un_canal_exige_acceso(client: TestClient, proxy_auth: None) -> None:
    respuesta = client.delete(f"/api/channels/{uuid.uuid4()}")
    assert respuesta.status_code == 401


def test_exportar_exige_acceso(client: TestClient, proxy_auth: None) -> None:
    respuesta = client.get(f"/api/export/{uuid.uuid4()}.csv")
    assert respuesta.status_code == 401


def test_oauth_exige_acceso_salvo_el_retorno(client: TestClient, proxy_auth: None) -> None:
    assert client.get("/api/oauth/status").status_code == 401
    assert client.get(f"/api/oauth/google/start?channel_id={uuid.uuid4()}").status_code == 401
    assert client.delete(f"/api/oauth/google/{uuid.uuid4()}").status_code == 401
    assert client.get(f"/api/oauth/analytics/{uuid.uuid4()}").status_code == 401

    # El retorno de Google lo abre el navegador del creador: no puede exigir la
    # cabecera del proxy. Sigue protegido por el `state` de un solo uso.
    retorno = client.get("/api/oauth/google/callback?error=access_denied", follow_redirects=False)
    assert retorno.status_code != 401


def test_con_auth_mode_none_no_se_exige_nada(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El modo de desarrollo sigue siendo cómodo; el arranque ya avisó."""
    monkeypatch.setattr(settings, "auth_mode", "none")
    assert client.get("/api/channels").status_code == 200


def test_trusted_proxy_mal_configurado_da_error_de_servidor(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si falta el valor, no se abre la puerta: se falla."""
    monkeypatch.setattr(settings, "auth_mode", "trusted_proxy")
    monkeypatch.setattr(settings, "trusted_auth_header", CABECERA)
    monkeypatch.setattr(settings, "trusted_auth_value", "")

    respuesta = client.get("/api/channels")
    assert respuesta.status_code == 500
    assert respuesta.json()["error"]["code"] == "autenticacion_mal_configurada"
