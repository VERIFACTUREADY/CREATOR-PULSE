"""Verificación de propiedad del canal antes de guardar un token OAuth.

Que el usuario elija un canal en la pantalla no prueba que sea suyo. Antes de
persistir nada se pregunta a Google de quién es la cuenta autorizada, y si no
coincide el token no llega a guardarse: se intenta revocar.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import httpx
import pytest
import respx
from app.api.deps import get_db
from app.core.config import settings
from app.core.crypto import generate_key, reset_cache
from app.main import create_app
from app.models.entities import Channel
from app.repositories.oauth import OAuthTokenRepository
from app.services.demo import DemoLoader
from app.services.youtube.oauth import SCOPES, TOKEN_ENDPOINT
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

KEY = generate_key()
CHANNELS_ENDPOINT = "https://www.googleapis.com/youtube/v3/channels"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"


@pytest.fixture
def owner_ready(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(settings, "enable_owner_mode", True)
    monkeypatch.setattr(settings, "google_oauth_client_id", "cliente.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "secreto")
    monkeypatch.setattr(settings, "oauth_token_encryption_key", KEY)
    reset_cache()
    yield
    reset_cache()


class _FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.data[key] = value.encode()

    def get(self, key: str) -> bytes | None:
        return self.data.get(key)

    def delete(self, key: str) -> int:
        return 1 if self.data.pop(key, None) is not None else 0


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    store = _FakeRedis()
    monkeypatch.setattr("app.api.routes.oauth.get_redis", lambda: store)
    return store


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _channel(session: Session) -> Channel:
    channel = DemoLoader(session).load("luciaglowdemo")
    session.commit()
    return channel


def _mock_token_exchange() -> None:
    respx.post(TOKEN_ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "ya29.acceso",
                "refresh_token": "1//refresco",
                "expires_in": 3600,
                "scope": " ".join(SCOPES),
            },
        )
    )


def _callback(client: TestClient, state: str) -> httpx.Response:
    return client.get(
        f"/api/oauth/google/callback?code=codigo&state={state}", follow_redirects=False
    )


def _start(client: TestClient, channel: Channel) -> str:
    respuesta = client.get(f"/api/oauth/google/start?channel_id={channel.id}")
    assert respuesta.status_code == 200, respuesta.text
    return str(respuesta.json()["state"])


# --- Casos ------------------------------------------------------------------


@respx.mock
def test_canal_autorizado_coincide_y_se_guarda(
    client: TestClient, session: Session, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    channel = _channel(session)
    state = _start(client, channel)
    _mock_token_exchange()
    respx.get(CHANNELS_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"items": [{"id": channel.youtube_channel_id}]})
    )

    response = _callback(client, state)

    assert response.status_code == 303
    assert "oauth=conectado" in response.headers["location"]
    assert OAuthTokenRepository(session).get_for_channel(channel.id) is not None


@respx.mock
def test_canal_autorizado_distinto_no_guarda_el_token(
    client: TestClient, session: Session, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    """El caso que la auditoría marcaba como crítico."""
    channel = _channel(session)
    state = _start(client, channel)
    _mock_token_exchange()
    respx.get(CHANNELS_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"items": [{"id": "UCotracuentaajena12345678"}]})
    )
    revoke = respx.post(REVOKE_ENDPOINT).mock(return_value=httpx.Response(200))

    response = _callback(client, state)

    assert response.status_code == 303
    assert "oauth=oauth_canal_no_coincide" in response.headers["location"]
    # Lo importante: no se ha persistido nada.
    assert OAuthTokenRepository(session).get_for_channel(channel.id) is None
    # Y se ha intentado revocar el token recién obtenido.
    assert revoke.called


@respx.mock
def test_cuenta_sin_canal_de_youtube(
    client: TestClient, session: Session, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    channel = _channel(session)
    state = _start(client, channel)
    _mock_token_exchange()
    respx.get(CHANNELS_ENDPOINT).mock(return_value=httpx.Response(200, json={"items": []}))
    revoke = respx.post(REVOKE_ENDPOINT).mock(return_value=httpx.Response(200))

    response = _callback(client, state)

    assert response.status_code == 303
    assert "oauth=oauth_sin_canal" in response.headers["location"]
    assert OAuthTokenRepository(session).get_for_channel(channel.id) is None
    assert revoke.called


@respx.mock
def test_error_de_channels_list_no_guarda_nada(
    client: TestClient, session: Session, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    channel = _channel(session)
    state = _start(client, channel)
    _mock_token_exchange()
    respx.get(CHANNELS_ENDPOINT).mock(return_value=httpx.Response(500, json={"error": {}}))
    revoke = respx.post(REVOKE_ENDPOINT).mock(return_value=httpx.Response(200))

    response = _callback(client, state)

    assert response.status_code == 303
    assert "oauth=oauth_intercambio_fallido" in response.headers["location"]
    assert OAuthTokenRepository(session).get_for_channel(channel.id) is None
    assert revoke.called


@respx.mock
def test_un_fallo_de_red_al_verificar_tampoco_guarda(
    client: TestClient, session: Session, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    channel = _channel(session)
    state = _start(client, channel)
    _mock_token_exchange()
    respx.get(CHANNELS_ENDPOINT).mock(side_effect=httpx.ConnectError("sin red"))
    respx.post(REVOKE_ENDPOINT).mock(return_value=httpx.Response(200))

    response = _callback(client, state)

    assert response.status_code == 303
    assert OAuthTokenRepository(session).get_for_channel(channel.id) is None


@respx.mock
def test_si_la_revocacion_falla_el_token_sigue_sin_guardarse(
    client: TestClient, session: Session, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    """Revocar es lo deseable, pero no guardar es lo obligatorio."""
    channel = _channel(session)
    state = _start(client, channel)
    _mock_token_exchange()
    respx.get(CHANNELS_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"items": [{"id": "UCajeno000000000000000aa"}]})
    )
    respx.post(REVOKE_ENDPOINT).mock(return_value=httpx.Response(400))

    response = _callback(client, state)

    assert "oauth=oauth_canal_no_coincide" in response.headers["location"]
    assert OAuthTokenRepository(session).get_for_channel(channel.id) is None


@respx.mock
def test_no_se_registran_tokens_ni_codigos(
    client: TestClient,
    session: Session,
    owner_ready: None,
    fake_redis: _FakeRedis,
    caplog: pytest.LogCaptureFixture,
) -> None:
    channel = _channel(session)
    state = _start(client, channel)
    _mock_token_exchange()
    respx.get(CHANNELS_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"items": [{"id": "UCajeno000000000000000aa"}]})
    )
    respx.post(REVOKE_ENDPOINT).mock(return_value=httpx.Response(200))

    with caplog.at_level("DEBUG"):
        _callback(client, state)

    registro = caplog.text
    assert "ya29.acceso" not in registro
    assert "1//refresco" not in registro
    assert "codigo" not in registro


def test_el_callback_sigue_exigiendo_un_state_valido(
    client: TestClient, session: Session, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    """La verificación de propiedad no sustituye a la protección CSRF."""
    response = client.get(
        f"/api/oauth/google/callback?code=codigo&state={uuid.uuid4()}", follow_redirects=False
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "oauth_estado_invalido"


# --- Cuentas con varios canales --------------------------------------------


def _pagina(ids: list[str], token: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"items": [{"id": cid} for cid in ids]}
    if token:
        payload["nextPageToken"] = token
    return payload


@respx.mock
def test_el_canal_elegido_es_el_segundo_de_la_lista(
    client: TestClient, session: Session, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    """Una cuenta puede administrar varios canales; el orden no significa nada."""
    channel = _channel(session)
    state = _start(client, channel)
    _mock_token_exchange()
    respx.get(CHANNELS_ENDPOINT).mock(
        return_value=httpx.Response(
            200, json=_pagina(["UCotro0000000000000000aa", channel.youtube_channel_id])
        )
    )

    response = _callback(client, state)

    assert "oauth=conectado" in response.headers["location"]
    assert OAuthTokenRepository(session).get_for_channel(channel.id) is not None


@respx.mock
def test_el_canal_elegido_aparece_en_una_pagina_posterior(
    client: TestClient, session: Session, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    channel = _channel(session)
    state = _start(client, channel)
    _mock_token_exchange()
    respx.get(CHANNELS_ENDPOINT).mock(
        side_effect=[
            httpx.Response(200, json=_pagina(["UCprimero000000000000aa"], token="pagina2")),
            httpx.Response(200, json=_pagina(["UCsegundo00000000000aa"], token="pagina3")),
            httpx.Response(200, json=_pagina([channel.youtube_channel_id])),
        ]
    )

    response = _callback(client, state)

    assert "oauth=conectado" in response.headers["location"]
    assert OAuthTokenRepository(session).get_for_channel(channel.id) is not None


@respx.mock
def test_varios_canales_pero_ninguno_coincide(
    client: TestClient, session: Session, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    channel = _channel(session)
    state = _start(client, channel)
    _mock_token_exchange()
    respx.get(CHANNELS_ENDPOINT).mock(
        return_value=httpx.Response(
            200, json=_pagina(["UCajeno1000000000000aa", "UCajeno2000000000000aa"])
        )
    )
    revoke = respx.post(REVOKE_ENDPOINT).mock(return_value=httpx.Response(200))

    response = _callback(client, state)

    assert "oauth=oauth_canal_no_coincide" in response.headers["location"]
    assert OAuthTokenRepository(session).get_for_channel(channel.id) is None
    assert revoke.called


@respx.mock
def test_un_error_en_una_pagina_posterior_no_guarda_nada(
    client: TestClient, session: Session, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    """Fallar a mitad de la paginación no puede dar un conjunto incompleto por bueno."""
    channel = _channel(session)
    state = _start(client, channel)
    _mock_token_exchange()
    respx.get(CHANNELS_ENDPOINT).mock(
        side_effect=[
            httpx.Response(200, json=_pagina(["UCprimero000000000000aa"], token="pagina2")),
            httpx.Response(500, json={"error": {}}),
        ]
    )
    revoke = respx.post(REVOKE_ENDPOINT).mock(return_value=httpx.Response(200))

    response = _callback(client, state)

    assert "oauth=oauth_intercambio_fallido" in response.headers["location"]
    assert OAuthTokenRepository(session).get_for_channel(channel.id) is None
    assert revoke.called


@respx.mock
def test_no_se_registran_los_identificadores_de_otros_canales(
    client: TestClient,
    session: Session,
    owner_ready: None,
    fake_redis: _FakeRedis,
    caplog: pytest.LogCaptureFixture,
) -> None:
    channel = _channel(session)
    state = _start(client, channel)
    _mock_token_exchange()
    respx.get(CHANNELS_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_pagina(["UCsecretodetercero00aa"]))
    )
    respx.post(REVOKE_ENDPOINT).mock(return_value=httpx.Response(200))

    with caplog.at_level("DEBUG"):
        _callback(client, state)

    assert "UCsecretodetercero00aa" not in caplog.text
