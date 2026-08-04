"""Pruebas de integración del modo propietario: almacén de tokens y endpoints."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from app.core.config import settings
from app.core.crypto import generate_key, reset_cache
from app.db.session import get_db
from app.main import create_app
from app.models.entities import Channel, OAuthToken
from app.repositories.oauth import OAuthTokenRepository, describe
from app.services.demo import DemoLoader
from app.services.youtube.analytics import ANALYTICS_ENDPOINT
from app.services.youtube.oauth import SCOPES, TOKEN_ENDPOINT, TokenBundle
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

KEY = generate_key()


@pytest.fixture
def owner_ready(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Modo propietario activo, configurado y con cifrado listo."""
    monkeypatch.setattr(settings, "enable_owner_mode", True)
    monkeypatch.setattr(settings, "google_oauth_client_id", "cliente.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "secreto")
    monkeypatch.setattr(settings, "oauth_token_encryption_key", KEY)
    reset_cache()
    yield
    reset_cache()


class _FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.data[key] = value

    def get(self, key: str) -> str | None:
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


def _bundle(**overrides: object) -> TokenBundle:
    defaults = {
        "access_token": "ya29.acceso",
        "refresh_token": "1//refresco",
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
        "scopes": list(SCOPES),
    }
    defaults.update(overrides)
    return TokenBundle(**defaults)  # type: ignore[arg-type]


# --- Almacén de tokens -------------------------------------------------------


def test_tokens_are_stored_encrypted(session: Session, owner_ready: None) -> None:
    """En la base de datos no puede quedar ningún token en claro."""
    channel = _channel(session)
    repo = OAuthTokenRepository(session)
    repo.store(
        provider="google",
        external_account_id=channel.youtube_channel_id,
        channel_id=channel.id,
        bundle=_bundle(),
    )
    session.commit()

    stored = session.get(OAuthToken, repo.get_for_channel(channel.id).id)  # type: ignore[union-attr]
    assert stored is not None
    assert b"ya29.acceso" not in bytes(stored.access_token_encrypted or b"")
    assert b"1//refresco" not in bytes(stored.refresh_token_encrypted or b"")


def test_store_is_idempotent_per_account(session: Session, owner_ready: None) -> None:
    channel = _channel(session)
    repo = OAuthTokenRepository(session)
    first = repo.store(
        provider="google",
        external_account_id=channel.youtube_channel_id,
        channel_id=channel.id,
        bundle=_bundle(),
    )
    second = repo.store(
        provider="google",
        external_account_id=channel.youtube_channel_id,
        channel_id=channel.id,
        bundle=_bundle(access_token="ya29.otro"),
    )
    session.commit()
    assert first.id == second.id
    assert len(repo.list_connected()) == 1


def test_refresh_token_is_kept_when_google_omits_it(session: Session, owner_ready: None) -> None:
    """Google sólo manda el refresh token la primera vez: no puede perderse."""
    channel = _channel(session)
    repo = OAuthTokenRepository(session)
    repo.store(
        provider="google",
        external_account_id=channel.youtube_channel_id,
        channel_id=channel.id,
        bundle=_bundle(),
    )
    repo.store(
        provider="google",
        external_account_id=channel.youtube_channel_id,
        channel_id=channel.id,
        bundle=_bundle(refresh_token=None),
    )
    session.commit()

    token = repo.get_for_channel(channel.id)
    assert token is not None
    assert token.refresh_token_encrypted is not None


def test_describe_never_exposes_tokens(session: Session, owner_ready: None) -> None:
    channel = _channel(session)
    repo = OAuthTokenRepository(session)
    token = repo.store(
        provider="google",
        external_account_id=channel.youtube_channel_id,
        channel_id=channel.id,
        bundle=_bundle(),
    )
    session.commit()

    info = str(describe(token))
    assert "ya29" not in info
    assert "1//refresco" not in info
    assert "has_refresh_token" in info


def test_valid_token_is_reused_without_calling_google(session: Session, owner_ready: None) -> None:
    channel = _channel(session)
    repo = OAuthTokenRepository(session)
    token = repo.store(
        provider="google",
        external_account_id=channel.youtube_channel_id,
        channel_id=channel.id,
        bundle=_bundle(),
    )
    session.commit()

    with respx.mock:
        route = respx.post(TOKEN_ENDPOINT).mock(return_value=httpx.Response(200, json={}))
        assert repo.access_token_for(token) == "ya29.acceso"
        assert route.call_count == 0


@respx.mock
def test_expired_token_is_refreshed(session: Session, owner_ready: None) -> None:
    channel = _channel(session)
    repo = OAuthTokenRepository(session)
    token = repo.store(
        provider="google",
        external_account_id=channel.youtube_channel_id,
        channel_id=channel.id,
        bundle=_bundle(expires_at=datetime.now(UTC) - timedelta(minutes=5)),
    )
    session.commit()

    respx.post(TOKEN_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"access_token": "ya29.renovado", "expires_in": 3600})
    )

    assert repo.access_token_for(token) == "ya29.renovado"
    assert token.last_refreshed_at is not None
    # Y el token nuevo también queda cifrado.
    assert b"ya29.renovado" not in bytes(token.access_token_encrypted or b"")


def test_disconnect_deletes_the_token(session: Session, owner_ready: None) -> None:
    channel = _channel(session)
    repo = OAuthTokenRepository(session)
    token = repo.store(
        provider="google",
        external_account_id=channel.youtube_channel_id,
        channel_id=channel.id,
        bundle=_bundle(),
    )
    session.commit()

    with respx.mock:
        respx.post("https://oauth2.googleapis.com/revoke").mock(return_value=httpx.Response(200))
        repo.disconnect(token)
    session.commit()

    assert repo.get_for_channel(channel.id) is None


def test_disconnect_deletes_locally_even_if_revoke_fails(
    session: Session, owner_ready: None
) -> None:
    """Si Google no responde, el token local se borra igualmente."""
    channel = _channel(session)
    repo = OAuthTokenRepository(session)
    token = repo.store(
        provider="google",
        external_account_id=channel.youtube_channel_id,
        channel_id=channel.id,
        bundle=_bundle(),
    )
    session.commit()

    with respx.mock:
        respx.post("https://oauth2.googleapis.com/revoke").mock(
            side_effect=httpx.ConnectError("sin red")
        )
        revoked = repo.disconnect(token)
    session.commit()

    assert revoked is False
    assert repo.get_for_channel(channel.id) is None


# --- Endpoints ---------------------------------------------------------------


def test_status_when_disabled(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_owner_mode", False)
    body = client.get("/api/oauth/status").json()

    assert body["enabled"] is False
    assert body["ready"] is False
    assert "ENABLE_OWNER_MODE=true" in body["missing_config"]
    assert body["connections"] == []
    assert "contraseña" in body["message_es"]


def test_status_lists_what_is_missing(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_owner_mode", True)
    monkeypatch.setattr(settings, "google_oauth_client_id", "")
    monkeypatch.setattr(settings, "oauth_token_encryption_key", "")
    reset_cache()

    body = client.get("/api/oauth/status").json()
    assert body["ready"] is False
    assert any("GOOGLE_OAUTH_CLIENT_ID" in m for m in body["missing_config"])
    assert any("OAUTH_TOKEN_ENCRYPTION_KEY" in m for m in body["missing_config"])
    reset_cache()


def test_status_reports_ready_and_connections(
    client: TestClient, session: Session, owner_ready: None
) -> None:
    channel = _channel(session)
    OAuthTokenRepository(session).store(
        provider="google",
        external_account_id=channel.youtube_channel_id,
        channel_id=channel.id,
        bundle=_bundle(),
    )
    session.commit()

    body = client.get("/api/oauth/status").json()
    assert body["ready"] is True
    assert body["missing_config"] == []
    assert len(body["connections"]) == 1
    assert body["connections"][0]["channel_title"] == channel.title
    # La respuesta nunca puede llevar el token.
    assert "ya29" not in str(body)


def test_status_declares_only_read_scopes(client: TestClient, owner_ready: None) -> None:
    body = client.get("/api/oauth/status").json()
    assert all("readonly" in scope for scope in body["scopes"])


def test_start_is_blocked_when_disabled(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "enable_owner_mode", False)
    channel = _channel(session)
    response = client.get(f"/api/oauth/google/start?channel_id={channel.id}")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "modo_propietario_desactivado"


def test_start_returns_the_authorization_url(
    client: TestClient, session: Session, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    channel = _channel(session)
    body = client.get(f"/api/oauth/google/start?channel_id={channel.id}").json()

    assert body["authorization_url"].startswith("https://accounts.google.com/")
    assert body["state"]
    assert "access_type=offline" in body["authorization_url"]
    # El secreto del cliente nunca sale hacia el navegador.
    assert "secreto" not in body["authorization_url"]


def test_start_rejects_unknown_channel(
    client: TestClient, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    response = client.get(f"/api/oauth/google/start?channel_id={uuid.uuid4()}")
    assert response.status_code == 404


@respx.mock
def test_callback_stores_the_token_and_redirects(
    client: TestClient, session: Session, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    channel = _channel(session)
    start = client.get(f"/api/oauth/google/start?channel_id={channel.id}").json()

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

    response = client.get(
        f"/api/oauth/google/callback?code=codigo&state={start['state']}",
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "oauth=conectado" in response.headers["location"]
    assert OAuthTokenRepository(session).get_for_channel(channel.id) is not None


def test_callback_rejects_a_forged_state(
    client: TestClient, session: Session, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    """Sin `state` válido no se canjea nada: es la defensa CSRF del flujo."""
    _channel(session)
    response = client.get(
        "/api/oauth/google/callback?code=codigo&state=inventado", follow_redirects=False
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "oauth_estado_invalido"


def test_callback_handles_user_denial(
    client: TestClient, owner_ready: None, fake_redis: _FakeRedis
) -> None:
    response = client.get("/api/oauth/google/callback?error=access_denied", follow_redirects=False)
    assert response.status_code == 303
    assert "oauth=denegado" in response.headers["location"]


def test_disconnect_endpoint(client: TestClient, session: Session, owner_ready: None) -> None:
    channel = _channel(session)
    OAuthTokenRepository(session).store(
        provider="google",
        external_account_id=channel.youtube_channel_id,
        channel_id=channel.id,
        bundle=_bundle(),
    )
    session.commit()

    with respx.mock:
        respx.post("https://oauth2.googleapis.com/revoke").mock(return_value=httpx.Response(200))
        body = client.request("DELETE", f"/api/oauth/google/{channel.id}").json()

    assert body["connected"] is False
    assert OAuthTokenRepository(session).get_for_channel(channel.id) is None


def test_disconnect_unknown_channel_returns_404(
    client: TestClient, session: Session, owner_ready: None
) -> None:
    channel = _channel(session)
    response = client.request("DELETE", f"/api/oauth/google/{channel.id}")
    assert response.status_code == 404


def test_analytics_requires_a_connected_channel(
    client: TestClient, session: Session, owner_ready: None
) -> None:
    channel = _channel(session)
    response = client.get(f"/api/oauth/analytics/{channel.id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "canal_no_conectado"


@respx.mock
def test_analytics_returns_owner_metrics(
    client: TestClient, session: Session, owner_ready: None
) -> None:
    channel = _channel(session)
    OAuthTokenRepository(session).store(
        provider="google",
        external_account_id=channel.youtube_channel_id,
        channel_id=channel.id,
        bundle=_bundle(),
    )
    session.commit()

    respx.get(ANALYTICS_ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={
                "columnHeaders": [
                    {"name": "views"},
                    {"name": "estimatedMinutesWatched"},
                    {"name": "averageViewDuration"},
                    {"name": "averageViewPercentage"},
                    {"name": "subscribersGained"},
                    {"name": "subscribersLost"},
                    {"name": "likes"},
                    {"name": "comments"},
                    {"name": "shares"},
                ],
                "rows": [[12000, 30000, 150.0, 45.2, 220, 30, 900, 120, 45]],
            },
        )
    )

    body = client.get(f"/api/oauth/analytics/{channel.id}").json()

    assert body["views"] == 12000
    assert body["estimated_minutes_watched"] == 30000
    assert body["net_subscribers"] == 190
    assert body["channel_title"] == channel.title
    assert "retraso" in body["note_es"]
    # El token nunca viaja en la respuesta.
    assert "ya29" not in str(body)


def test_analytics_is_blocked_when_disabled(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "enable_owner_mode", False)
    channel = _channel(session)
    response = client.get(f"/api/oauth/analytics/{channel.id}")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "modo_propietario_desactivado"


def test_public_config_reports_owner_mode_state(client: TestClient) -> None:
    """El frontend debe poder saber si el modo propietario está disponible."""
    body = client.get("/api/config/public").json()
    assert "owner_mode_enabled" in body
