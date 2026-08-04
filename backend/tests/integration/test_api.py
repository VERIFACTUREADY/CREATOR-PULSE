"""Pruebas de los endpoints HTTP."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from app.core.config import ALGORITHM_VERSION, settings
from app.db.session import get_db
from app.main import create_app
from app.models.enums import AnalysisStatus, DataSource, SamplingStrategy
from app.repositories.analysis import AnalysisRunRepository
from app.services.analysis.orchestrator import AnalysisOrchestrator
from app.services.demo import DemoLoader
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


@pytest.fixture
def client(session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Cliente de pruebas que reutiliza la sesión de la prueba."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    # La cola no está disponible en las pruebas: el análisis se ejecuta a mano.
    monkeypatch.setattr("app.api.routes.channels.enqueue_analysis", lambda *a, **k: True)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _completed_demo_run(session: Session, handle: str = "luciaglowdemo") -> Any:
    channel = DemoLoader(session).load(handle)
    run = AnalysisRunRepository(session).create(
        channel_id=channel.id,
        status=AnalysisStatus.QUEUED,
        progress=0,
        max_videos=20,
        max_comments_per_video=250,
        max_comments_per_channel=3000,
        include_replies=False,
        sampling_strategy=SamplingStrategy.MIXED,
        algorithm_version=ALGORITHM_VERSION,
        source=DataSource.DEMO,
    )
    session.commit()
    AnalysisOrchestrator(session).execute(run.id)
    session.commit()
    return run


# --- Sistema ----------------------------------------------------------------


def test_health_reports_components(client: TestClient) -> None:
    response = client.get("/api/health")
    body = response.json()
    assert response.status_code in (200, 503)
    names = {c["name"] for c in body["components"]}
    assert {"api", "database", "redis"} <= names


def test_public_config_never_exposes_secrets(client: TestClient) -> None:
    body = client.get("/api/config/public").json()
    serialised = str(body).lower()
    assert "api_key" not in serialised
    assert "secret" not in serialised
    assert body["algorithm_version"] == ALGORITHM_VERSION
    assert body["disclaimer_es"]
    assert body["criticism_notice_es"]
    assert "limits" in body


def test_openapi_is_generated(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert "/api/channels/analyse" in spec["paths"]
    assert "/api/analysis-runs/{run_id}/dashboard" in spec["paths"]


def test_request_id_header_is_returned(client: TestClient) -> None:
    assert client.get("/api/health").headers.get("X-Request-ID")


def test_request_id_is_propagated(client: TestClient) -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "mi-id-123"})
    assert response.headers["X-Request-ID"] == "mi-id-123"


# --- Errores ----------------------------------------------------------------


def test_unknown_route_returns_spanish_error(client: TestClient) -> None:
    body = client.get("/api/no-existe").json()
    assert body["ok"] is False
    assert body["error"]["code"] == "http_404"
    assert "no existe" in body["error"]["message"].lower()


def test_invalid_payload_returns_validation_error(client: TestClient) -> None:
    response = client.post("/api/channels/resolve", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "entrada_invalida"
    assert body["request_id"]


def test_unsupported_channel_reference_is_rejected(client: TestClient) -> None:
    response = client.post("/api/channels/resolve", json={"reference": "https://vimeo.com/algo"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "referencia_canal_no_soportada"


def test_missing_run_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/analysis-runs/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "no_encontrado"


def test_technical_detail_is_hidden_in_production(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    body = client.post("/api/channels/resolve", json={"reference": "https://vimeo.com/x"}).json()
    assert "detail" not in body["error"]


def test_technical_detail_is_visible_in_development(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "app_env", "development")
    body = client.post("/api/channels/resolve", json={"reference": "https://vimeo.com/x"}).json()
    assert "detail" in body["error"]


# --- Canales ----------------------------------------------------------------


def test_channel_list_is_empty_initially(client: TestClient) -> None:
    assert client.get("/api/channels").json() == []


def test_demo_channels_endpoint(client: TestClient) -> None:
    body = client.get("/api/channels/demo").json()
    assert len(body) >= 3
    assert {"handle", "title", "videos", "comments"} <= set(body[0])


def test_resolve_demo_channel(client: TestClient) -> None:
    body = client.post("/api/channels/resolve", json={"reference": "@luciaglowdemo"}).json()
    assert body["is_demo"] is True
    assert body["kind"] == "demo"
    assert "ficticios" in body["message_es"]


def test_resolve_without_api_key_validates_format_only(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "")
    body = client.post("/api/channels/resolve", json={"reference": "@algunhandle"}).json()
    assert body["is_demo"] is False
    assert body["channel"] is None
    assert "clave" in body["message_es"].lower()


def test_analyse_requires_api_key_for_real_channels(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "")
    response = client.post("/api/channels/analyse", json={"reference": "@uncanalreal"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "youtube_sin_clave"


def test_workload_estimate(client: TestClient) -> None:
    body = client.get(
        "/api/channels/estimate", params={"max_videos": 20, "max_comments_per_video": 250}
    ).json()
    assert body["estimated_quota_units"] > 0
    assert body["daily_quota_reference"] == 10_000
    assert "cuota" in body["note_es"]


def test_estimate_rejects_limits_beyond_maximum(client: TestClient) -> None:
    assert client.get("/api/channels/estimate", params={"max_videos": 5000}).status_code == 422


def test_analyse_demo_channel_queues_run(client: TestClient) -> None:
    response = client.post(
        "/api/channels/analyse", json={"reference": "@luciaglowdemo", "demo": True}
    )
    assert response.status_code == 202
    body = response.json()
    assert body["is_demo"] is True
    assert body["queued"] is True
    assert body["estimated_quota_units"] == 0
    assert "demostración" in body["message_es"]


def test_analyse_unknown_demo_channel_returns_404(client: TestClient) -> None:
    response = client.post("/api/channels/analyse", json={"reference": "@noexiste", "demo": True})
    assert response.status_code == 404


def test_analyse_rejects_concurrent_runs(client: TestClient) -> None:
    client.post("/api/channels/analyse", json={"reference": "@luciaglowdemo", "demo": True})
    response = client.post(
        "/api/channels/analyse", json={"reference": "@luciaglowdemo", "demo": True}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "analisis_en_curso"


def test_analyse_clamps_limits_to_safe_maximum(client: TestClient, session: Session) -> None:
    response = client.post(
        "/api/channels/analyse",
        json={
            "reference": "@luciaglowdemo",
            "demo": True,
            "max_videos": 50,
            "max_comments_per_video": 500,
        },
    )
    run_id = uuid.UUID(response.json()["run_id"])
    run = AnalysisRunRepository(session).get(run_id)
    assert run is not None
    assert run.max_videos <= settings.youtube_hard_max_videos
    assert run.max_comments_per_video <= settings.youtube_hard_max_comments_per_video


def test_delete_channel_removes_data(client: TestClient, session: Session) -> None:
    channel = DemoLoader(session).load("luciaglowdemo")
    session.commit()
    assert client.delete(f"/api/channels/{channel.id}").status_code == 204
    assert client.get("/api/channels").json() == []


def test_delete_unknown_channel_returns_404(client: TestClient) -> None:
    assert client.delete(f"/api/channels/{uuid.uuid4()}").status_code == 404


# --- Dashboard --------------------------------------------------------------


def test_dashboard_of_completed_run(client: TestClient, session: Session) -> None:
    run = _completed_demo_run(session)
    body = client.get(f"/api/analysis-runs/{run.id}/dashboard").json()

    assert body["run"]["status"] == "completed"
    assert body["run"]["is_demo"] is True
    assert body["channel"]["title"]
    assert body["summary"]["comments_analysed"] > 0
    assert body["topics"]
    assert body["recommendations"]
    assert body["content_ideas"]
    assert body["videos"]
    assert body["data_quality"]["is_demo"] is True
    assert "causalidad" in body["disclaimer_es"]


def test_dashboard_of_pending_run_is_not_found(client: TestClient, session: Session) -> None:
    channel = DemoLoader(session).load("luciaglowdemo")
    run = AnalysisRunRepository(session).create(
        channel_id=channel.id,
        status=AnalysisStatus.QUEUED,
        progress=0,
        max_videos=5,
        max_comments_per_video=50,
        max_comments_per_channel=200,
        include_replies=False,
        sampling_strategy=SamplingStrategy.MIXED,
        algorithm_version=ALGORITHM_VERSION,
        source=DataSource.DEMO,
    )
    session.commit()
    response = client.get(f"/api/analysis-runs/{run.id}/dashboard")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "analisis_no_completado"


def test_status_endpoint_reports_progress(client: TestClient, session: Session) -> None:
    run = _completed_demo_run(session)
    body = client.get(f"/api/analysis-runs/{run.id}/status").json()
    assert body["progress"] == 100
    assert body["status_label_es"] == "Completado"


def test_topics_endpoint_excludes_noise_by_default(client: TestClient, session: Session) -> None:
    run = _completed_demo_run(session)
    without = client.get(f"/api/analysis-runs/{run.id}/topics").json()
    with_noise = client.get(
        f"/api/analysis-runs/{run.id}/topics", params={"include_noise": True}
    ).json()
    assert all(not t["is_noise"] for t in without)
    assert len(with_noise) >= len(without)


def test_recommendations_carry_evidence_and_confidence(
    client: TestClient, session: Session
) -> None:
    run = _completed_demo_run(session)
    body = client.get(f"/api/analysis-runs/{run.id}/recommendations").json()
    assert body
    for rec in body:
        assert rec["confidence_level"] in {"baja", "media", "alta"}
        assert rec["evidence"]["total_comments_analysed"] > 0
        assert rec["caveat_es"]
        assert rec["category_label_es"]


def test_videos_endpoint_includes_youtube_links(client: TestClient, session: Session) -> None:
    run = _completed_demo_run(session)
    body = client.get(f"/api/analysis-runs/{run.id}/videos").json()
    assert body
    assert all(v["youtube_url"].startswith("https://www.youtube.com/watch?v=") for v in body)


def test_data_quality_endpoint_lists_limitations(client: TestClient, session: Session) -> None:
    run = _completed_demo_run(session)
    body = client.get(f"/api/analysis-runs/{run.id}/data-quality").json()
    assert body["level"] in {"baja", "media", "alta"}
    assert body["biases_es"]
    assert body["sampling_strategy"]


def test_requests_strengths_and_criticism_endpoints(client: TestClient, session: Session) -> None:
    run = _completed_demo_run(session)
    assert client.get(f"/api/analysis-runs/{run.id}/requests").status_code == 200
    assert client.get(f"/api/analysis-runs/{run.id}/strengths").status_code == 200

    criticism = client.get(f"/api/analysis-runs/{run.id}/criticism").json()
    kinds = {group["kind"] for group in criticism}
    assert kinds == {"constructive", "subjective", "harassment", "spam"}


def test_content_ideas_endpoint(client: TestClient, session: Session) -> None:
    run = _completed_demo_run(session)
    body = client.get(f"/api/analysis-runs/{run.id}/content-ideas").json()
    assert body
    for idea in body:
        assert idea["overinterpretation_risk_es"]
        assert idea["suggested_format_label_es"]


def test_delete_run(client: TestClient, session: Session) -> None:
    run = _completed_demo_run(session)
    assert client.delete(f"/api/analysis-runs/{run.id}").status_code == 204
    assert client.get(f"/api/analysis-runs/{run.id}").status_code == 404


# --- Exportación ------------------------------------------------------------


def test_export_json(client: TestClient, session: Session) -> None:
    run = _completed_demo_run(session)
    response = client.get(f"/api/export/{run.id}.json")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert response.json()["summary"]["comments_analysed"] > 0


def test_export_csv(client: TestClient, session: Session) -> None:
    run = _completed_demo_run(session)
    response = client.get(f"/api/export/{run.id}.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    text = response.text
    assert "temas" in text
    assert "videos" in text


# --- Comparador -------------------------------------------------------------


def test_comparison_of_two_channels(client: TestClient, session: Session) -> None:
    first = _completed_demo_run(session, "luciaglowdemo")
    second = _completed_demo_run(session, "pixelraptordemo")

    response = client.post("/api/comparisons", json={"run_ids": [str(first.id), str(second.id)]})
    assert response.status_code == 200
    body = response.json()
    assert len(body["channels"]) == 2
    assert body["warnings_es"]
    assert any("no es una clasificación" in w for w in body["warnings_es"])
    assert all(row["is_demo"] for row in body["channels"])


def test_comparison_requires_at_least_two_runs(client: TestClient, session: Session) -> None:
    run = _completed_demo_run(session)
    response = client.post("/api/comparisons", json={"run_ids": [str(run.id)]})
    assert response.status_code == 422


def test_comparison_rejects_more_than_four(client: TestClient) -> None:
    ids = [str(uuid.uuid4()) for _ in range(5)]
    assert client.post("/api/comparisons", json={"run_ids": ids}).status_code == 422


def test_saved_comparisons_are_listed(client: TestClient, session: Session) -> None:
    first = _completed_demo_run(session, "luciaglowdemo")
    second = _completed_demo_run(session, "codigoclarodemo")
    client.post("/api/comparisons", json={"run_ids": [str(first.id), str(second.id)]})
    assert len(client.get("/api/comparisons").json()) == 1


# --- Uso de API -------------------------------------------------------------


def test_usage_endpoint_states_it_is_an_estimate(client: TestClient) -> None:
    body = client.get("/api/usage/youtube").json()
    assert body["daily_quota_reference"] == 10_000
    assert "estimación" in body["note_es"]
    assert "No reflejan la cuota real" in body["note_es"]


# --- Modo propietario -------------------------------------------------------


def test_owner_mode_is_disabled_by_default(client: TestClient) -> None:
    """El modo propietario existe, pero viene apagado de fábrica."""
    body = client.get("/api/oauth/status").json()
    assert body["enabled"] is False
    assert body["ready"] is False
    assert "ENABLE_OWNER_MODE=true" in body["missing_config"]
    assert "contraseña" in body["message_es"]


def test_owner_endpoints_are_blocked_when_disabled(client: TestClient, session: Session) -> None:
    """Con el modo apagado, ningún endpoint de propietario responde datos."""
    channel = DemoLoader(session).load("luciaglowdemo")
    session.commit()

    for response in (
        client.get(f"/api/oauth/google/start?channel_id={channel.id}"),
        client.get(f"/api/oauth/analytics/{channel.id}"),
        client.request("DELETE", f"/api/oauth/google/{channel.id}"),
    ):
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "modo_propietario_desactivado"


def test_owner_status_declares_only_readonly_scopes(client: TestClient) -> None:
    body = client.get("/api/oauth/status").json()
    assert body["scopes"]
    assert all("readonly" in scope for scope in body["scopes"])


# --- Cola de trabajos -------------------------------------------------------


def test_job_id_is_valid_for_rq() -> None:
    """RQ sólo admite letras, números, guiones y guiones bajos en el ID."""
    import re

    from app.workers.queue import analysis_job_id

    job_id = analysis_job_id(uuid.uuid4())
    assert re.fullmatch(r"[A-Za-z0-9_-]+", job_id), job_id
