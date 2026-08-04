"""Pruebas del motor de confianza, recomendaciones e ideas."""

from __future__ import annotations

import uuid

from app.models.enums import ConfidenceLevel, RecommendationCategory, TrendDirection
from app.services.analysis.dtos import AnalysedComment, AnalysisContext, TopicSummary
from app.services.analysis.performance import ChannelBaseline, VideoPerformance
from app.services.analysis.quality import DataQuality
from app.services.recommendations.confidence import (
    ConfidenceInput,
    compute_confidence,
    level_label_es,
)
from app.services.recommendations.generator import (
    Evidence,
    build_safety_recommendation,
    generate_recommendations,
)
from app.services.recommendations.ideas import build_ideas_from_recommendations

# --- Confianza --------------------------------------------------------------


def test_confidence_grows_with_evidence() -> None:
    weak = compute_confidence(ConfidenceInput(supporting_comments=3, supporting_videos=1))
    strong = compute_confidence(
        ConfidenceInput(
            supporting_comments=60,
            supporting_videos=8,
            total_videos=10,
            classifier_confidence=0.9,
            cluster_quality=0.9,
            trend_confidence=0.8,
        )
    )
    assert strong.score > weak.score
    assert strong.level == ConfidenceLevel.HIGH


def test_confidence_never_high_with_single_supporting_video() -> None:
    outcome = compute_confidence(
        ConfidenceInput(
            supporting_comments=200,
            supporting_videos=1,
            total_videos=10,
            classifier_confidence=1.0,
            cluster_quality=1.0,
            trend_confidence=1.0,
        )
    )
    assert outcome.level != ConfidenceLevel.HIGH
    assert any("dos vídeos" in cap for cap in outcome.caps_es)


def test_confidence_is_low_with_a_single_comment() -> None:
    outcome = compute_confidence(
        ConfidenceInput(supporting_comments=1, supporting_videos=1, total_videos=5)
    )
    assert outcome.level == ConfidenceLevel.LOW
    assert any("único comentario" in cap for cap in outcome.caps_es)


def test_viral_video_concentration_penalises_confidence() -> None:
    base = ConfidenceInput(
        supporting_comments=80,
        supporting_videos=6,
        total_videos=10,
        classifier_confidence=0.9,
        cluster_quality=0.9,
    )
    spread = compute_confidence(base)
    concentrated = compute_confidence(
        ConfidenceInput(**{**base.__dict__, "dominant_video_share": 0.75})
    )
    assert concentrated.score < spread.score
    assert concentrated.level != ConfidenceLevel.HIGH
    assert concentrated.penalties_es


def test_spam_heavy_topic_is_low_confidence() -> None:
    outcome = compute_confidence(
        ConfidenceInput(
            supporting_comments=100,
            supporting_videos=9,
            total_videos=10,
            spam_or_duplicate_share=0.6,
        )
    )
    assert outcome.level == ConfidenceLevel.LOW


def test_low_classifier_certainty_caps_confidence() -> None:
    outcome = compute_confidence(
        ConfidenceInput(
            supporting_comments=100,
            supporting_videos=9,
            total_videos=10,
            classifier_confidence=0.2,
            cluster_quality=1.0,
        )
    )
    assert outcome.level != ConfidenceLevel.HIGH


def test_confidence_score_is_bounded_and_has_factors() -> None:
    outcome = compute_confidence(
        ConfidenceInput(supporting_comments=10_000, supporting_videos=500, total_videos=500)
    )
    assert 0.0 <= outcome.score <= 1.0
    assert outcome.factors


def test_level_labels() -> None:
    assert level_label_es("alta") == "Alta"
    assert level_label_es("desconocido") == "Baja"


# --- Contexto de prueba -----------------------------------------------------


def _topic(
    key: str,
    *,
    comments: int = 30,
    videos: int = 5,
    positive: int = 20,
    negative: int = 2,
    requests: int = 0,
    questions: int = 0,
    aspects: list[str] | None = None,
    trend: str = TrendDirection.STABLE,
    dominant: float = 0.2,
    association: dict | None = None,
) -> TopicSummary:
    neutral = max(0, comments - positive - negative)
    return TopicSummary(
        cluster_key=key,
        label_es=f"Tema {key}",
        description_es="",
        comment_count=comments,
        unique_video_count=videos,
        positive_count=positive,
        neutral_count=neutral,
        negative_count=negative,
        request_count=requests,
        question_count=questions,
        share_of_comments=comments / 200,
        mentions_per_1000=comments * 5,
        video_coverage=videos / 10,
        recent_share=0.5,
        previous_share=0.4,
        trend_change=0.25,
        trend_direction=trend,
        trend_confidence=0.6,
        trend_note_es=None,
        coverage_score=videos / 10,
        confidence_score=0.0,
        confidence_level="baja",
        confidence_factors={},
        confidence_penalties_es=[],
        dominant_video_share=dominant,
        top_aspects=aspects or ["humor"],
        keywords=["humor", "risa"],
        representative_comments=[{"text": "ejemplo", "sentiment": "positive", "likes": 3}],
        centroid=None,
        is_noise=False,
        video_ids={f"v{i}" for i in range(videos)},
        association=association or {},
        mean_sentiment_confidence=0.7,
    )


def _comment(
    index: int, cluster: str, *, toxicity: float = 0.0, intents: list[str] | None = None
) -> AnalysedComment:
    return AnalysedComment(
        comment_id=uuid.uuid4(),
        video_id=uuid.uuid4(),
        youtube_video_id=f"v{index % 6}",
        text=f"comentario {index}",
        normalised=f"comentario {index}",
        published_at=None,
        like_count=1,
        language="es",
        sentiment_label="positive",
        sentiment_score=0.6,
        sentiment_confidence=0.7,
        intents=intents or ["praise"],
        aspects=["humor"],
        keywords=["humor"],
        toxicity=toxicity,
        is_question=False,
        is_request=False,
        is_spam=False,
        is_duplicate=False,
        cluster_key=cluster,
    )


def _context(topics: list[TopicSummary], comments: list[AnalysedComment]) -> AnalysisContext:
    return AnalysisContext(
        run_id=uuid.uuid4(),
        channel_title="Canal de prueba",
        comments=comments,
        topics=topics,
        baseline=ChannelBaseline(median_views=10_000, median_comments_per_1000=5.0, video_count=10),
        performances={
            f"v{i}": VideoPerformance(video_id=f"v{i}", views_relative_to_median=1.0)
            for i in range(6)
        },
        video_titles={f"v{i}": f"Vídeo {i}" for i in range(6)},
        quality=DataQuality(videos_sampled=10, comments_sampled=200, comments_analysed=200),
        total_videos=10,
        total_comments_analysed=200,
    )


# --- Recomendaciones --------------------------------------------------------


def test_strength_recommendation_is_generated() -> None:
    context = _context([_topic("c0", positive=25)], [_comment(i, "c0") for i in range(25)])
    categories = [r.category for r in generate_recommendations(context)]
    assert RecommendationCategory.DOUBLE_DOWN in categories


def test_demand_recommendation_is_generated() -> None:
    topic = _topic("c0", requests=12, positive=5)
    context = _context([topic], [_comment(i, "c0") for i in range(20)])
    recs = [
        r
        for r in generate_recommendations(context)
        if r.category == RecommendationCategory.AUDIENCE_DEMAND
    ]
    assert recs
    assert recs[0].evidence.supporting_comments == 12
    assert recs[0].priority == 1


def test_issue_recommendation_requires_multiple_videos() -> None:
    """Una crítica concentrada en un solo vídeo no es un patrón del canal."""
    single_video = _topic("c0", comments=20, positive=1, negative=10, videos=1)
    context = _context([single_video], [_comment(i, "c0") for i in range(11)])
    assert not [
        r
        for r in generate_recommendations(context)
        if r.category == RecommendationCategory.FIX_ISSUE
    ]


def test_issue_recommendation_is_generated_when_spread_across_videos() -> None:
    spread = _topic("c1", comments=20, positive=1, negative=10, videos=4, aspects=["audio"])
    context = _context([spread], [_comment(i, "c1") for i in range(11)])
    issues = [
        r
        for r in generate_recommendations(context)
        if r.category == RecommendationCategory.FIX_ISSUE
    ]
    assert issues
    # El experimento propuesto es específico del aspecto criticado.
    assert "micrófono" in issues[0].suggested_experiment_es


def test_community_recommendation_for_repeated_questions() -> None:
    topic = _topic("c0", questions=9, positive=2)
    context = _context([topic], [_comment(i, "c0") for i in range(15)])
    assert [
        r
        for r in generate_recommendations(context)
        if r.category == RecommendationCategory.COMMUNITY_OPPORTUNITY
    ]


def test_hypothesis_recommendation_never_claims_causality() -> None:
    association = {
        "available": True,
        "direction": "positiva",
        "view_lift": 0.4,
        "videos_with_topic": 4,
        "videos_without_topic": 4,
        "strength": 0.5,
    }
    topic = _topic("c0", association=association)
    context = _context([topic], [_comment(i, "c0") for i in range(30)])
    hypotheses = [
        r
        for r in generate_recommendations(context)
        if r.category == RecommendationCategory.TEST_HYPOTHESIS
    ]
    assert hypotheses
    assert "no demuestra causalidad" in hypotheses[0].caveat_es


def test_every_recommendation_has_evidence_and_confidence() -> None:
    topic = _topic("c0", requests=8, questions=6, negative=6, videos=5)
    context = _context([topic], [_comment(i, "c0") for i in range(40)])
    recommendations = generate_recommendations(context)
    assert recommendations
    for rec in recommendations:
        assert rec.confidence.level in {"baja", "media", "alta"}
        assert rec.caveat_es
        assert rec.kpi_es
        assert isinstance(rec.evidence, Evidence)
        assert rec.evidence.total_comments_analysed == 200


def test_no_recommendations_without_evidence() -> None:
    """Un canal sin señal no genera recomendaciones inventadas."""
    context = _context([], [])
    assert generate_recommendations(context) == []


def test_safety_alert_triggers_on_repeated_harassment() -> None:
    comments = [_comment(i, "c0", toxicity=0.9, intents=["insult"]) for i in range(8)]
    comments += [_comment(100 + i, "c0") for i in range(50)]
    context = _context([_topic("c0")], comments)
    alerts = build_safety_recommendation(context)
    assert alerts
    assert alerts[0].category == RecommendationCategory.SAFETY_ALERT
    assert "moderación" in alerts[0].title_es.lower()


def test_safety_alert_absent_without_toxic_comments() -> None:
    context = _context([_topic("c0")], [_comment(i, "c0") for i in range(50)])
    assert build_safety_recommendation(context) == []


def test_safety_alert_does_not_drive_content_ideas() -> None:
    """Ninguna idea de contenido puede nacer de una alerta de acoso."""
    comments = [_comment(i, "c0", toxicity=0.9, intents=["insult"]) for i in range(10)]
    context = _context([_topic("c0", comments=10, positive=0, negative=10)], comments)

    safety = build_safety_recommendation(context)
    assert safety

    # Alimentando el generador SÓLO con la alerta de seguridad, no debe salir
    # ninguna idea derivada de ella: se cae al respaldo exploratorio.
    ideas = build_ideas_from_recommendations(context, safety)
    assert all(idea.topic_cluster_key is None for idea in ideas)
    assert all(idea.confidence_level == ConfidenceLevel.LOW for idea in ideas)


# --- Ideas de contenido -----------------------------------------------------


def test_ideas_are_backed_by_topic_evidence() -> None:
    topic = _topic("c0", requests=10, positive=15)
    context = _context([topic], [_comment(i, "c0") for i in range(30)])
    ideas = build_ideas_from_recommendations(context, generate_recommendations(context))
    assert ideas
    for idea in ideas:
        assert idea.evidence["bullets_es"]
        assert idea.overinterpretation_risk_es
        assert idea.confidence_level in {"baja", "media", "alta"}
        assert idea.hook_es
        assert idea.kpi_es


def test_exploratory_ideas_when_no_evidence() -> None:
    """Sin datos se generan ideas exploratorias etiquetadas de baja confianza."""
    context = _context([], [])
    ideas = build_ideas_from_recommendations(context, [])
    assert ideas
    assert all(idea.confidence_level == "baja" for idea in ideas)
    assert all(idea.overinterpretation_risk_es for idea in ideas)


def test_ideas_are_deduplicated_per_topic() -> None:
    topic = _topic("c0", requests=10, questions=8, positive=20, negative=8, videos=5)
    context = _context([topic], [_comment(i, "c0") for i in range(40)])
    ideas = build_ideas_from_recommendations(context, generate_recommendations(context))
    keys = [idea.topic_cluster_key for idea in ideas if idea.topic_cluster_key]
    assert len(keys) == len(set(keys))


def test_evidence_matches_the_claim_of_each_category() -> None:
    """La cifra de evidencia debe contar lo mismo que afirma el texto.

    Si la explicación habla de comentarios positivos y la evidencia muestra el
    total del tema, el creador ve dos números distintos para la misma
    conclusión y deja de fiarse del informe.
    """
    topic = _topic(
        "c0",
        comments=50,
        positive=30,
        negative=8,
        requests=12,
        questions=9,
        videos=6,
    )
    context = _context([topic], [_comment(i, "c0") for i in range(50)])

    by_category = {r.category: r for r in generate_recommendations(context)}

    assert by_category[RecommendationCategory.DOUBLE_DOWN].evidence.supporting_comments == 30
    assert by_category[RecommendationCategory.AUDIENCE_DEMAND].evidence.supporting_comments == 12
    assert (
        by_category[RecommendationCategory.COMMUNITY_OPPORTUNITY].evidence.supporting_comments == 9
    )


def test_issue_evidence_counts_negative_comments() -> None:
    topic = _topic("c0", comments=20, positive=1, negative=11, videos=4, aspects=["audio"])
    context = _context([topic], [_comment(i, "c0") for i in range(20)])

    issues = [
        r
        for r in generate_recommendations(context)
        if r.category == RecommendationCategory.FIX_ISSUE
    ]
    assert issues
    assert issues[0].evidence.supporting_comments == 11
