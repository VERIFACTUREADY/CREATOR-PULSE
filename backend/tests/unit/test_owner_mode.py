"""Pruebas del modo propietario: cifrado, OAuth y cliente de Analytics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import respx
from app.core.config import settings
from app.core.crypto import (
    DecryptionError,
    EncryptionNotConfiguredError,
    decrypt,
    encrypt,
    encryption_available,
    generate_key,
    reset_cache,
)
from app.core.errors import FeatureDisabledError
from app.services.youtube.analytics import (
    ANALYTICS_ENDPOINT,
    AnalyticsError,
    AnalyticsForbiddenError,
    OwnerAnalytics,
    YouTubeAnalyticsClient,
    traffic_source_label,
)
from app.services.youtube.oauth import (
    AUTHORIZATION_ENDPOINT,
    REVOKE_ENDPOINT,
    SCOPES,
    TOKEN_ENDPOINT,
    OAuthExchangeError,
    OAuthNotConfiguredError,
    OAuthStateError,
    TokenBundle,
    build_authorization_url,
    consume_state,
    create_state,
    ensure_enabled,
    exchange_code,
    refresh_access_token,
    revoke_token,
)

VALID_KEY = generate_key()


@pytest.fixture
def crypto_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "oauth_token_encryption_key", VALID_KEY)
    reset_cache()
    yield
    reset_cache()


@pytest.fixture
def owner_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_owner_mode", True)
    monkeypatch.setattr(
        settings, "google_oauth_client_id", "cliente-de-prueba.apps.googleusercontent.com"
    )
    monkeypatch.setattr(settings, "google_oauth_client_secret", "secreto-de-prueba")
    monkeypatch.setattr(
        settings, "google_oauth_redirect_uri", "http://localhost:8000/api/oauth/google/callback"
    )


# --- Cifrado ----------------------------------------------------------------


def test_encrypt_decrypt_round_trip(crypto_ready: None) -> None:
    token = "ya29.token-de-acceso-de-prueba"
    cifrado = encrypt(token)
    assert cifrado != token.encode()
    assert decrypt(cifrado) == token


def test_encryption_is_not_deterministic(crypto_ready: None) -> None:
    """Dos cifrados del mismo token deben ser distintos (IV aleatorio)."""
    assert encrypt("mismo-token") != encrypt("mismo-token")


def test_ciphertext_does_not_contain_the_token(crypto_ready: None) -> None:
    token = "ya29.secreto-muy-reconocible"
    assert token.encode() not in encrypt(token)


def test_decrypt_of_none_is_none(crypto_ready: None) -> None:
    assert decrypt(None) is None
    assert decrypt(b"") is None


def test_decrypt_with_a_different_key_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cambiar la clave invalida los tokens: se pide reconectar, no se ignora."""
    monkeypatch.setattr(settings, "oauth_token_encryption_key", VALID_KEY)
    reset_cache()
    cifrado = encrypt("token")

    monkeypatch.setattr(settings, "oauth_token_encryption_key", generate_key())
    reset_cache()
    with pytest.raises(DecryptionError):
        decrypt(cifrado)
    reset_cache()


def test_missing_key_raises_instead_of_storing_plaintext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "oauth_token_encryption_key", "")
    reset_cache()
    assert not encryption_available()
    with pytest.raises(EncryptionNotConfiguredError):
        encrypt("token")
    reset_cache()


def test_invalid_key_is_reported_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "oauth_token_encryption_key", "esto-no-es-una-clave-fernet")
    reset_cache()
    with pytest.raises(EncryptionNotConfiguredError) as excinfo:
        encrypt("token")
    assert "formato válido" in excinfo.value.message
    reset_cache()


def test_generated_key_works(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "oauth_token_encryption_key", generate_key())
    reset_cache()
    assert decrypt(encrypt("hola")) == "hola"
    reset_cache()


# --- Interruptor de la función ----------------------------------------------


def test_owner_mode_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_owner_mode", False)
    with pytest.raises(FeatureDisabledError) as excinfo:
        ensure_enabled()
    assert excinfo.value.code == "modo_propietario_desactivado"


def test_owner_mode_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_owner_mode", True)
    monkeypatch.setattr(settings, "google_oauth_client_id", "")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "")
    with pytest.raises(OAuthNotConfiguredError):
        ensure_enabled()


# --- URL de autorización -----------------------------------------------------


def test_authorization_url_requests_only_read_scopes(owner_enabled: None) -> None:
    url = build_authorization_url("un-state")
    assert url.startswith(AUTHORIZATION_ENDPOINT)
    for scope in SCOPES:
        assert scope.replace(":", "%3A").replace("/", "%2F") in url or scope in url
    # Ningún permiso de escritura.
    assert "force-ssl" not in url
    assert "youtube.upload" not in url


def test_authorization_url_asks_for_offline_access(owner_enabled: None) -> None:
    """Sin `access_type=offline` Google no entrega refresh token."""
    url = build_authorization_url("un-state")
    assert "access_type=offline" in url
    assert "prompt=consent" in url


def test_authorization_url_carries_the_state(owner_enabled: None) -> None:
    assert "state=mi-state-123" in build_authorization_url("mi-state-123")


def test_authorization_url_never_contains_the_client_secret(owner_enabled: None) -> None:
    assert "secreto-de-prueba" not in build_authorization_url("s")


# --- Protección CSRF con `state` ---------------------------------------------


class _FakeRedis:
    """Redis mínimo en memoria para probar el ciclo del `state`."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.data[key] = value

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def delete(self, key: str) -> int:
        return 1 if self.data.pop(key, None) is not None else 0


def test_state_is_random_and_long(owner_enabled: None) -> None:
    store = _FakeRedis()
    primero, segundo = create_state(store), create_state(store)
    assert primero != segundo
    assert len(primero) >= 32


def test_state_round_trip(owner_enabled: None) -> None:
    store = _FakeRedis()
    state = create_state(store)
    consume_state(store, state)  # no lanza


def test_state_cannot_be_reused(owner_enabled: None) -> None:
    """Un `state` consumido no vale una segunda vez (anti-repetición)."""
    store = _FakeRedis()
    state = create_state(store)
    consume_state(store, state)
    with pytest.raises(OAuthStateError):
        consume_state(store, state)


def test_unknown_state_is_rejected() -> None:
    with pytest.raises(OAuthStateError):
        consume_state(_FakeRedis(), "state-inventado-por-un-atacante")


def test_missing_state_is_rejected() -> None:
    with pytest.raises(OAuthStateError):
        consume_state(_FakeRedis(), None)


# --- Intercambio y refresco de tokens ----------------------------------------


@respx.mock
def test_exchange_code_returns_tokens(owner_enabled: None) -> None:
    respx.post(TOKEN_ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "ya29.acceso",
                "refresh_token": "1//refresco",
                "expires_in": 3599,
                "scope": " ".join(SCOPES),
                "token_type": "Bearer",
            },
        )
    )
    bundle = exchange_code("codigo-de-google")
    assert bundle.access_token == "ya29.acceso"
    assert bundle.refresh_token == "1//refresco"
    assert not bundle.is_expired
    assert set(bundle.scopes) == set(SCOPES)


@respx.mock
def test_exchange_code_failure_is_translated(owner_enabled: None) -> None:
    respx.post(TOKEN_ENDPOINT).mock(
        return_value=httpx.Response(400, json={"error": "invalid_grant"})
    )
    with pytest.raises(OAuthExchangeError):
        exchange_code("codigo-caducado")


@respx.mock
def test_exchange_code_without_access_token_fails(owner_enabled: None) -> None:
    respx.post(TOKEN_ENDPOINT).mock(return_value=httpx.Response(200, json={"expires_in": 3600}))
    with pytest.raises(OAuthExchangeError):
        exchange_code("codigo")


@respx.mock
def test_refresh_keeps_the_existing_refresh_token(owner_enabled: None) -> None:
    """La respuesta de refresco no repite el refresh token: hay que conservarlo."""
    respx.post(TOKEN_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"access_token": "ya29.nuevo", "expires_in": 3599})
    )
    bundle = refresh_access_token("1//refresco-original")
    assert bundle.access_token == "ya29.nuevo"
    assert bundle.refresh_token == "1//refresco-original"


@respx.mock
def test_refresh_failure_asks_to_reconnect(owner_enabled: None) -> None:
    respx.post(TOKEN_ENDPOINT).mock(
        return_value=httpx.Response(400, json={"error": "invalid_grant"})
    )
    with pytest.raises(OAuthExchangeError) as excinfo:
        refresh_access_token("1//revocado")
    assert "vuelve a conectarlo" in excinfo.value.message.lower()


@respx.mock
def test_revoke_reports_success_and_failure() -> None:
    respx.post(REVOKE_ENDPOINT).mock(return_value=httpx.Response(200))
    assert revoke_token("token") is True

    respx.post(REVOKE_ENDPOINT).mock(return_value=httpx.Response(400))
    assert revoke_token("token") is False


@respx.mock
def test_revoke_never_raises_on_network_error() -> None:
    """Un fallo de revocación no debe impedir borrar el token local."""
    respx.post(REVOKE_ENDPOINT).mock(side_effect=httpx.ConnectError("sin red"))
    assert revoke_token("token") is False


# --- Caducidad ---------------------------------------------------------------


def test_bundle_expiry_uses_a_safety_margin() -> None:
    """Un token a punto de caducar se considera caducado, para no usarlo a medias."""
    casi = TokenBundle(
        access_token="a",
        refresh_token="r",
        expires_at=datetime.now(UTC) + timedelta(seconds=30),
        scopes=list(SCOPES),
    )
    holgado = TokenBundle(
        access_token="a",
        refresh_token="r",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        scopes=list(SCOPES),
    )
    assert casi.is_expired
    assert not holgado.is_expired


# --- Cliente de Analytics ----------------------------------------------------


def _analytics_response(headers: list[str], rows: list[list[Any]]) -> dict[str, Any]:
    return {
        "columnHeaders": [{"name": h} for h in headers],
        "rows": rows,
    }


@respx.mock
def test_analytics_query_sends_bearer_token() -> None:
    route = respx.get(ANALYTICS_ENDPOINT).mock(
        return_value=httpx.Response(200, json=_analytics_response(["views"], [[10]]))
    )
    with YouTubeAnalyticsClient("ya29.mi-token") as client:
        client.query(
            channel_id="UC123",
            start_date="2024-01-01",
            end_date="2024-01-28",
            metrics=("views",),
        )
    assert route.calls.last.request.headers["Authorization"] == "Bearer ya29.mi-token"
    assert route.calls.last.request.url.params["ids"] == "channel==UC123"


@respx.mock
def test_analytics_forbidden_is_translated() -> None:
    respx.get(ANALYTICS_ENDPOINT).mock(return_value=httpx.Response(403, json={}))
    with pytest.raises(AnalyticsForbiddenError) as excinfo, YouTubeAnalyticsClient("t") as client:
        client.query(
            channel_id="UC1", start_date="2024-01-01", end_date="2024-01-02", metrics=("views",)
        )
    assert "propietaria" in excinfo.value.message


@respx.mock
def test_analytics_server_error_is_translated() -> None:
    respx.get(ANALYTICS_ENDPOINT).mock(return_value=httpx.Response(500, text="boom"))
    with pytest.raises(AnalyticsError), YouTubeAnalyticsClient("t") as client:
        client.query(
            channel_id="UC1", start_date="2024-01-01", end_date="2024-01-02", metrics=("views",)
        )


def test_columnar_rows_become_dicts() -> None:
    payload = _analytics_response(["day", "views"], [["2024-01-01", 10], ["2024-01-02", 20]])
    rows = YouTubeAnalyticsClient._rows_to_dicts(payload)
    assert rows == [{"day": "2024-01-01", "views": 10}, {"day": "2024-01-02", "views": 20}]


def test_empty_report_returns_empty_dict() -> None:
    assert YouTubeAnalyticsClient._first_row({"columnHeaders": [], "rows": []}) == {}


@respx.mock
def test_full_report_maps_owner_metrics() -> None:
    from datetime import date

    def _handler(request: httpx.Request) -> httpx.Response:
        metrics = request.url.params.get("metrics", "")
        dimensions = request.url.params.get("dimensions")

        if dimensions == "day":
            return httpx.Response(
                200,
                json=_analytics_response(
                    ["day", "views", "estimatedMinutesWatched", "subscribersGained"],
                    [["2024-05-01", 100, 250, 3]],
                ),
            )
        if dimensions == "insightTrafficSourceType":
            return httpx.Response(
                200,
                json=_analytics_response(
                    ["insightTrafficSourceType", "views", "estimatedMinutesWatched"],
                    [["YT_SEARCH", 500, 1200], ["SUBSCRIBER", 300, 900]],
                ),
            )
        if dimensions == "country":
            return httpx.Response(
                200,
                json=_analytics_response(
                    ["country", "views", "estimatedMinutesWatched"], [["ES", 700, 1500]]
                ),
            )
        if dimensions == "video":
            return httpx.Response(
                200,
                json=_analytics_response(
                    [
                        "video",
                        "views",
                        "estimatedMinutesWatched",
                        "averageViewDuration",
                        "averageViewPercentage",
                    ],
                    [["abc12345678", 400, 900, 135.0, 42.5]],
                ),
            )
        if "impressions" in metrics:
            return httpx.Response(
                200,
                json=_analytics_response(
                    ["impressions", "impressionsClickThroughRate"], [[50_000, 4.8]]
                ),
            )
        return httpx.Response(
            200,
            json=_analytics_response(
                [
                    "views",
                    "estimatedMinutesWatched",
                    "averageViewDuration",
                    "averageViewPercentage",
                    "subscribersGained",
                    "subscribersLost",
                    "likes",
                    "comments",
                    "shares",
                ],
                [[12_000, 30_000, 150.0, 45.2, 220, 30, 900, 120, 45]],
            ),
        )

    respx.get(ANALYTICS_ENDPOINT).mock(side_effect=_handler)

    with YouTubeAnalyticsClient("token") as client:
        report = client.fetch_report("UC123", days=28, today=date(2024, 6, 1))

    assert report.views == 12_000
    assert report.estimated_minutes_watched == 30_000
    assert report.average_view_percentage == 45.2
    assert report.subscribers_gained == 220
    assert report.subscribers_lost == 30
    assert report.net_subscribers == 190
    assert report.impressions == 50_000
    assert report.impressions_ctr == 4.8
    assert report.daily
    assert report.traffic_sources[0]["label_es"] == "Búsqueda de YouTube"
    assert report.geography
    assert report.top_videos
    assert report.unavailable_es == []


@respx.mock
def test_report_survives_missing_impressions() -> None:
    """Si la cuenta no expone impresiones, el resto del informe llega igual."""
    from datetime import date

    def _handler(request: httpx.Request) -> httpx.Response:
        if "impressions" in request.url.params.get("metrics", ""):
            return httpx.Response(400, text="metric not supported")
        if request.url.params.get("dimensions"):
            return httpx.Response(200, json=_analytics_response([], []))
        return httpx.Response(200, json=_analytics_response(["views"], [[500]]))

    respx.get(ANALYTICS_ENDPOINT).mock(side_effect=_handler)

    with YouTubeAnalyticsClient("token") as client:
        report = client.fetch_report("UC123", today=date(2024, 6, 1))

    assert report.views == 500
    assert report.impressions is None
    assert any("impresiones" in msg for msg in report.unavailable_es)


def test_report_window_ends_before_today() -> None:
    """YouTube Analytics va con retraso: pedir hasta hoy devolvería ceros."""
    from datetime import date

    with respx.mock:
        respx.get(ANALYTICS_ENDPOINT).mock(
            return_value=httpx.Response(200, json=_analytics_response([], []))
        )
        with YouTubeAnalyticsClient("t") as client:
            report = client.fetch_report("UC1", days=28, today=date(2024, 6, 1))

    assert report.end_date == "2024-05-29"
    assert report.start_date == "2024-05-02"


def test_missing_metrics_are_none_not_zero() -> None:
    """Un dato ausente nunca se presenta como cero: sería una cifra inventada."""
    report = OwnerAnalytics(start_date="2024-01-01", end_date="2024-01-28")
    assert report.views is None
    assert report.impressions is None
    assert report.net_subscribers is None
    assert report.to_dict()["views"] is None


def test_traffic_source_labels_are_in_spanish() -> None:
    assert traffic_source_label("YT_SEARCH") == "Búsqueda de YouTube"
    assert traffic_source_label("SUBSCRIBER") == "Feed de suscriptores"
    # Un código desconocido no rompe: se muestra legible.
    assert traffic_source_label("ALGO_NUEVO") == "Algo nuevo"
