"""Etapa 10 del pipeline: generación de recomendaciones.

Las recomendaciones se construyen **después** de calcular la evidencia numérica.
Un LLM puede reescribir el texto, pero nunca inventa las cifras: todo número que
aparece en una recomendación procede del objeto `evidence`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.models.enums import (
    ContentFormat,
    IntentLabel,
    RecommendationCategory,
    TrendDirection,
)
from app.services.analysis.aspects import aspect_label_es
from app.services.analysis.dtos import AnalysisContext, TopicSummary
from app.services.recommendations.confidence import (
    ConfidenceInput,
    ConfidenceOutcome,
    compute_confidence,
)

#: Mínimos por debajo de los cuales no se emite una recomendación de ese tipo.
MIN_COMMENTS_FOR_STRENGTH = 6
MIN_COMMENTS_FOR_REQUEST = 4
MIN_COMMENTS_FOR_ISSUE = 4
MIN_VIDEOS_FOR_ISSUE = 2
#: Toxicidad a partir de la cual un comentario cuenta como acoso.
TOXICITY_ALERT_THRESHOLD = 0.6
#: Cuota de comentarios tóxicos que dispara el aviso de seguridad.
TOXICITY_ALERT_SHARE = 0.04


@dataclass
class Evidence:
    """Evidencia numérica que respalda una recomendación."""

    supporting_comments: int = 0
    supporting_videos: int = 0
    total_comments_analysed: int = 0
    total_videos_analysed: int = 0
    share_of_comments: float = 0.0
    mentions_per_1000: float = 0.0
    video_coverage: float = 0.0
    trend_direction: str = TrendDirection.UNKNOWN
    trend_change: float | None = None
    recent_share: float | None = None
    previous_share: float | None = None
    dominant_video_share: float = 0.0
    positive_count: int = 0
    negative_count: int = 0
    request_count: int = 0
    question_count: int = 0
    performance_association: dict[str, Any] = field(default_factory=dict)
    representative_comments: list[dict[str, Any]] = field(default_factory=list)
    confidence_factors: dict[str, float] = field(default_factory=dict)
    confidence_penalties_es: list[str] = field(default_factory=list)
    topic_cluster_key: str | None = None
    source_es: str = "Comentarios públicos analizados en esta ejecución."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedRecommendation:
    """Recomendación completa lista para persistir."""

    category: str
    title_es: str
    explanation_es: str
    reason_es: str
    evidence: Evidence
    confidence: ConfidenceOutcome
    priority: int
    suggested_format: str | None
    suggested_hook_es: str
    suggested_experiment_es: str
    kpi_es: str
    caveat_es: str
    topic_cluster_key: str | None = None


def _evidence_from_topic(topic: TopicSummary, context: AnalysisContext) -> Evidence:
    return Evidence(
        supporting_comments=topic.comment_count,
        supporting_videos=topic.unique_video_count,
        total_comments_analysed=context.total_comments_analysed,
        total_videos_analysed=context.total_videos,
        share_of_comments=round(topic.share_of_comments, 4),
        mentions_per_1000=topic.mentions_per_1000,
        video_coverage=topic.video_coverage,
        trend_direction=topic.trend_direction,
        trend_change=topic.trend_change,
        recent_share=topic.recent_share,
        previous_share=topic.previous_share,
        dominant_video_share=topic.dominant_video_share,
        positive_count=topic.positive_count,
        negative_count=topic.negative_count,
        request_count=topic.request_count,
        question_count=topic.question_count,
        performance_association=topic.association,
        representative_comments=topic.representative_comments[:3],
        confidence_factors=topic.confidence_factors,
        confidence_penalties_es=topic.confidence_penalties_es,
        topic_cluster_key=topic.cluster_key,
    )


def _confidence_for_topic(
    topic: TopicSummary, context: AnalysisContext, *, classifier_confidence: float | None = None
) -> ConfidenceOutcome:
    association = topic.association or {}
    return compute_confidence(
        ConfidenceInput(
            supporting_comments=topic.comment_count,
            supporting_videos=topic.unique_video_count,
            total_videos=context.total_videos,
            total_comments=context.total_comments_analysed,
            dominant_video_share=topic.dominant_video_share,
            trend_confidence=topic.trend_confidence,
            trend_consistent=topic.trend_direction
            in (TrendDirection.RISING, TrendDirection.FALLING),
            classifier_confidence=(
                classifier_confidence
                if classifier_confidence is not None
                else topic.mean_sentiment_confidence
            ),
            cluster_quality=1.0 - min(1.0, topic.spam_share * 2),
            recency_share=topic.recent_share or 0.0,
            spam_or_duplicate_share=topic.spam_share,
            association_available=bool(association.get("available")),
            association_strength=float(association.get("strength") or 0.0),
        )
    )


def _trend_phrase(topic: TopicSummary) -> str:
    if topic.trend_direction == TrendDirection.RISING:
        if topic.trend_change is not None:
            return (
                f" Además, el tema ha crecido un {topic.trend_change:.0%} "
                "respecto al periodo anterior."
            )
        return " Además, es un tema que no aparecía en el periodo anterior."
    if topic.trend_direction == TrendDirection.FALLING and topic.trend_change is not None:
        return f" El tema ha bajado un {abs(topic.trend_change):.0%} respecto al periodo anterior."
    if topic.trend_direction == TrendDirection.UNKNOWN:
        return " No hay histórico suficiente para saber si el tema está creciendo."
    return " El peso del tema se mantiene estable entre periodos."


def _association_phrase(topic: TopicSummary) -> str:
    association = topic.association or {}
    if not association.get("available"):
        return ""
    direction = association.get("direction")
    if direction == "positiva":
        return (
            f" Los {association.get('videos_with_topic')} vídeos donde aparece este tema tienden "
            "a rendir por encima de la mediana del canal (es una asociación, no una causa)."
        )
    if direction == "negativa":
        return (
            f" Los {association.get('videos_with_topic')} vídeos donde aparece este tema tienden "
            "a rendir por debajo de la mediana del canal (es una asociación, no una causa)."
        )
    return " No se observa una asociación clara con el rendimiento de los vídeos."


def _base_caveat(topic: TopicSummary, confidence: ConfidenceOutcome) -> str:
    parts: list[str] = []
    parts.extend(confidence.penalties_es)
    parts.extend(confidence.caps_es)
    if topic.trend_note_es:
        parts.append(topic.trend_note_es)
    if not parts:
        parts.append(
            "Es una asociación estadística sobre una muestra de comentarios, "
            "no una garantía de resultados."
        )
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Generadores por categoría
# ---------------------------------------------------------------------------


def build_strength_recommendations(context: AnalysisContext) -> list[GeneratedRecommendation]:
    """«Refuerza una fortaleza»: temas con feedback positivo repetido."""
    out: list[GeneratedRecommendation] = []
    candidates = [
        t
        for t in context.topics
        if not t.is_noise
        and t.positive_count >= MIN_COMMENTS_FOR_STRENGTH
        and t.positive_share >= 0.5
    ]
    candidates.sort(key=lambda t: (-t.positive_count, -t.unique_video_count))

    for topic in candidates[:3]:
        confidence = _confidence_for_topic(topic, context)
        evidence = _evidence_from_topic(topic, context)
        # La afirmación habla del feedback *positivo*, así que la evidencia debe
        # contar lo mismo. Si dejara el total del tema, el texto y la evidencia
        # mostrarían dos cifras distintas para la misma conclusión.
        evidence.supporting_comments = topic.positive_count
        aspect = topic.top_aspects[0] if topic.top_aspects else None
        aspect_text = aspect_label_es(aspect).lower() if aspect else topic.label_es.lower()

        explanation = (
            f"«{topic.label_es}» aparece de forma positiva en {topic.positive_count} comentarios "
            f"repartidos por {topic.unique_video_count} de los {context.total_videos} vídeos "
            f"analizados ({topic.share_of_comments:.0%} de la muestra)."
            + _trend_phrase(topic)
            + _association_phrase(topic)
        )
        out.append(
            GeneratedRecommendation(
                category=RecommendationCategory.DOUBLE_DOWN,
                title_es=f"Refuerza lo que tu audiencia ya valora: {topic.label_es.lower()}",
                explanation_es=explanation,
                reason_es=(
                    f"Es el tipo de feedback positivo más repetido y aparece en varios vídeos, "
                    f"no en uno solo ({topic.video_coverage:.0%} de cobertura del canal)."
                ),
                evidence=evidence,
                confidence=confidence,
                priority=1 if confidence.is_high else 2,
                suggested_format=ContentFormat.SHORT,
                suggested_hook_es=(
                    f"«Me decís mucho que lo que más os gusta de mis vídeos es {aspect_text}…»"
                ),
                suggested_experiment_es=(
                    f"Publica dos vídeos seguidos que apoyen claramente en {aspect_text} y compara "
                    "los comentarios por cada 1.000 visualizaciones con la mediana del canal."
                ),
                kpi_es="Comentarios por cada 1.000 visualizaciones",
                caveat_es=_base_caveat(topic, confidence),
                topic_cluster_key=topic.cluster_key,
            )
        )
    return out


def build_demand_recommendations(context: AnalysisContext) -> list[GeneratedRecommendation]:
    """«Responde a la demanda»: peticiones de contenido repetidas."""
    out: list[GeneratedRecommendation] = []
    candidates = [
        t for t in context.topics if not t.is_noise and t.request_count >= MIN_COMMENTS_FOR_REQUEST
    ]
    candidates.sort(key=lambda t: (-t.request_count, -t.unique_video_count))

    for topic in candidates[:3]:
        confidence = _confidence_for_topic(topic, context)
        evidence = _evidence_from_topic(topic, context)
        # La evidencia de una petición es el número de peticiones, no el del tema.
        evidence.supporting_comments = topic.request_count

        tutorial = any(
            IntentLabel.TUTORIAL_REQUEST in c.intents
            for c in context.usable_comments
            if c.cluster_key == topic.cluster_key
        )
        fmt = ContentFormat.TUTORIAL if tutorial else ContentFormat.LONG_FORM

        explanation = (
            f"{topic.request_count} comentarios piden explícitamente contenido relacionado con "
            f"«{topic.label_es}», en {topic.unique_video_count} vídeos distintos."
            + _trend_phrase(topic)
        )
        out.append(
            GeneratedRecommendation(
                category=RecommendationCategory.AUDIENCE_DEMAND,
                title_es=f"Tu audiencia te está pidiendo: {topic.label_es.lower()}",
                explanation_es=explanation,
                reason_es=(
                    "Son peticiones explícitas y repetidas en varios vídeos, "
                    "no una única sugerencia aislada."
                ),
                evidence=evidence,
                confidence=confidence,
                priority=1,
                suggested_format=fmt,
                suggested_hook_es=(
                    f"«Me lo habéis pedido {topic.request_count} veces en los comentarios, "
                    "así que vamos a ello.»"
                ),
                suggested_experiment_es=(
                    "Publica el vídeo mencionando explícitamente que responde a esas peticiones y "
                    "compara sus comentarios por cada 1.000 visualizaciones con la mediana."
                ),
                kpi_es="Comentarios por cada 1.000 visualizaciones y retención de la audiencia",
                caveat_es=_base_caveat(topic, confidence),
                topic_cluster_key=topic.cluster_key,
            )
        )
    return out


def build_issue_recommendations(context: AnalysisContext) -> list[GeneratedRecommendation]:
    """«Corrige un problema»: crítica constructiva repetida en varios vídeos."""
    out: list[GeneratedRecommendation] = []
    candidates = [
        t
        for t in context.topics
        if not t.is_noise
        and t.negative_count >= MIN_COMMENTS_FOR_ISSUE
        and t.unique_video_count >= MIN_VIDEOS_FOR_ISSUE
        and t.negative_share >= 0.35
    ]
    candidates.sort(key=lambda t: (-t.negative_count, -t.unique_video_count))

    for topic in candidates[:3]:
        confidence = _confidence_for_topic(topic, context)
        evidence = _evidence_from_topic(topic, context)
        evidence.supporting_comments = topic.negative_count

        aspect = topic.top_aspects[0] if topic.top_aspects else None
        fix = _fix_suggestion(aspect)

        explanation = (
            f"«{topic.label_es}» recibe críticas en {topic.negative_count} comentarios repartidos "
            f"por {topic.unique_video_count} vídeos distintos."
            + _trend_phrase(topic)
            + _association_phrase(topic)
        )
        out.append(
            GeneratedRecommendation(
                category=RecommendationCategory.FIX_ISSUE,
                title_es=f"Problema repetido a corregir: {topic.label_es.lower()}",
                explanation_es=explanation,
                reason_es=(
                    "La crítica se repite en varios vídeos, así que es un patrón y "
                    "no la opinión de un espectador concreto."
                ),
                evidence=evidence,
                confidence=confidence,
                priority=1 if topic.unique_video_count >= 3 else 2,
                suggested_format=None,
                suggested_hook_es=(
                    "«He leído vuestros comentarios y he cambiado una cosa en este vídeo…»"
                ),
                suggested_experiment_es=fix,
                kpi_es="Número de comentarios críticos sobre este aspecto en los próximos vídeos",
                caveat_es=_base_caveat(topic, confidence),
                topic_cluster_key=topic.cluster_key,
            )
        )
    return out


def _fix_suggestion(aspect: str | None) -> str:
    """Experimento concreto según el aspecto criticado."""
    suggestions = {
        "audio": (
            "Graba el próximo vídeo con el micrófono más cerca y baja la música de fondo entre "
            "6 y 8 dB. Comprueba si desaparecen los comentarios sobre el sonido."
        ),
        "musica": (
            "Baja el volumen de la música de fondo en el próximo vídeo y comprueba si siguen "
            "apareciendo comentarios sobre ella."
        ),
        "iluminacion": (
            "Añade una fuente de luz frontal en el próximo vídeo y compara los comentarios sobre "
            "la imagen con los del vídeo anterior."
        ),
        "ritmo": (
            "Recorta las pausas del próximo vídeo para reducir su duración un 20% y compara la "
            "proporción de comentarios que mencionan el ritmo."
        ),
        "duracion": (
            "Publica una versión más corta del mismo contenido y compara comentarios por cada "
            "1.000 visualizaciones."
        ),
        "edicion": (
            "Simplifica los cortes y las transiciones en el próximo vídeo y comprueba si bajan "
            "las críticas sobre el montaje."
        ),
        "claridad": (
            "Añade un resumen inicial de 20 segundos explicando qué se va a ver y comprueba si "
            "bajan las preguntas repetidas en comentarios."
        ),
        "repeticion": (
            "Alterna el formato en los próximos tres vídeos y comprueba si baja el número de "
            "comentarios sobre repetición."
        ),
        "titulo": (
            "Prueba títulos más descriptivos y menos ambiguos en los próximos tres vídeos y "
            "compara los comentarios que mencionan el título."
        ),
        "miniatura": (
            "Prueba una miniatura con menos elementos y texto más grande, y compara los "
            "comentarios por cada 1.000 visualizaciones."
        ),
    }
    return suggestions.get(
        aspect or "",
        (
            "Aplica un cambio concreto en el próximo vídeo, indícalo en la descripción y compara "
            "el número de comentarios críticos sobre este aspecto con los vídeos anteriores."
        ),
    )


def build_hypothesis_recommendations(context: AnalysisContext) -> list[GeneratedRecommendation]:
    """«Pon a prueba una hipótesis»: asociaciones con muestra aún limitada."""
    out: list[GeneratedRecommendation] = []
    candidates = [
        t
        for t in context.topics
        if not t.is_noise
        and (t.association or {}).get("available")
        and (t.association or {}).get("direction") in {"positiva", "negativa"}
    ]
    candidates.sort(key=lambda t: -abs(float((t.association or {}).get("view_lift") or 0.0)))

    for topic in candidates[:2]:
        association = topic.association
        confidence = _confidence_for_topic(topic, context)
        evidence = _evidence_from_topic(topic, context)

        lift = association.get("view_lift")
        lift_text = f"{abs(float(lift)):.0%}" if lift is not None else "una diferencia apreciable"
        sign = "por encima" if association.get("direction") == "positiva" else "por debajo"

        explanation = (
            f"Los {association.get('videos_with_topic')} vídeos donde aparece «{topic.label_es}» "
            f"tienen una mediana de visualizaciones {lift_text} {sign} de los "
            f"{association.get('videos_without_topic')} vídeos donde no aparece. La muestra sigue "
            "siendo pequeña, así que es una hipótesis a comprobar, no una conclusión."
        )
        out.append(
            GeneratedRecommendation(
                category=RecommendationCategory.TEST_HYPOTHESIS,
                title_es=f"Hipótesis a probar: el peso de «{topic.label_es.lower()}»",
                explanation_es=explanation,
                reason_es=(
                    "Hay una asociación observable entre el tema y el rendimiento, pero el número "
                    "de vídeos no permite descartar que sea casualidad."
                ),
                evidence=evidence,
                confidence=confidence,
                priority=3,
                suggested_format=ContentFormat.SERIES,
                suggested_hook_es="«Vamos a probar una cosa durante los próximos tres vídeos…»",
                suggested_experiment_es=(
                    f"Publica tres vídeos que traten «{topic.label_es.lower()}» de forma clara y "
                    "tres que no, y compara la mediana de visualizaciones y de comentarios por "
                    "cada 1.000 visualizaciones entre ambos grupos."
                ),
                kpi_es="Mediana de visualizaciones y comentarios por cada 1.000 visualizaciones",
                caveat_es=(
                    "Una asociación estadística no demuestra causalidad: puede haber otros "
                    "factores (fecha, miniatura, tendencia externa) detrás de la diferencia. "
                    + _base_caveat(topic, confidence)
                ),
                topic_cluster_key=topic.cluster_key,
            )
        )
    return out


def build_community_recommendations(context: AnalysisContext) -> list[GeneratedRecommendation]:
    """«Oportunidad de comunidad»: preguntas repetidas sin respuesta clara."""
    out: list[GeneratedRecommendation] = []
    candidates = [t for t in context.topics if not t.is_noise and t.question_count >= 3]
    candidates.sort(key=lambda t: (-t.question_count, -t.unique_video_count))

    for topic in candidates[:2]:
        confidence = _confidence_for_topic(topic, context)
        evidence = _evidence_from_topic(topic, context)
        evidence.supporting_comments = topic.question_count

        explanation = (
            f"{topic.question_count} comentarios hacen preguntas sobre «{topic.label_es}» en "
            f"{topic.unique_video_count} vídeos distintos. Una pregunta que se repite en varios "
            "vídeos indica que la respuesta no está siendo fácil de encontrar."
        )
        out.append(
            GeneratedRecommendation(
                category=RecommendationCategory.COMMUNITY_OPPORTUNITY,
                title_es=f"Pregunta repetida sin respuesta clara: {topic.label_es.lower()}",
                explanation_es=explanation,
                reason_es=(
                    "La misma duda reaparece en vídeos distintos, así que responderla una vez "
                    "de forma visible ahorra trabajo y mejora la experiencia."
                ),
                evidence=evidence,
                confidence=confidence,
                priority=2,
                suggested_format=ContentFormat.QA,
                suggested_hook_es=(
                    f"«Me preguntáis esto en todos los vídeos, así que lo respondo de una vez: "
                    f"{topic.label_es.lower()}.»"
                ),
                suggested_experiment_es=(
                    "Fija un comentario con la respuesta o añade una sección de preguntas "
                    "frecuentes en la descripción, y comprueba si baja la frecuencia de la duda."
                ),
                kpi_es="Número de veces que se repite la pregunta en los próximos vídeos",
                caveat_es=_base_caveat(topic, confidence),
                topic_cluster_key=topic.cluster_key,
            )
        )
    return out


def build_safety_recommendation(context: AnalysisContext) -> list[GeneratedRecommendation]:
    """«Aviso de seguridad»: acoso público dirigido al creador.

    Es una función de seguridad para el creador, no una herramienta de
    vigilancia: no identifica autores ni expone perfiles.
    """
    usable = context.usable_comments
    if not usable:
        return []

    toxic = [c for c in usable if (c.toxicity or 0.0) >= TOXICITY_ALERT_THRESHOLD]
    if not toxic:
        return []

    share = len(toxic) / len(usable)
    affected_videos = {c.youtube_video_id for c in toxic}
    if len(toxic) < 3 and share < TOXICITY_ALERT_SHARE:
        return []

    confidence = compute_confidence(
        ConfidenceInput(
            supporting_comments=len(toxic),
            supporting_videos=len(affected_videos),
            total_videos=context.total_videos,
            total_comments=context.total_comments_analysed,
            classifier_confidence=0.6,
            cluster_quality=0.6,
        )
    )

    evidence = Evidence(
        supporting_comments=len(toxic),
        supporting_videos=len(affected_videos),
        total_comments_analysed=context.total_comments_analysed,
        total_videos_analysed=context.total_videos,
        share_of_comments=round(share, 4),
        confidence_factors=confidence.factors,
        confidence_penalties_es=confidence.penalties_es,
        source_es="Detección automática de lenguaje ofensivo en comentarios públicos.",
    )

    return [
        GeneratedRecommendation(
            category=RecommendationCategory.SAFETY_ALERT,
            title_es="Revisa la moderación: hay comentarios ofensivos recurrentes",
            explanation_es=(
                f"Se han detectado {len(toxic)} comentarios con lenguaje ofensivo o de acoso "
                f"({share:.1%} de la muestra) en {len(affected_videos)} vídeos. Esta señal existe "
                "para tu seguridad, no para que respondas a cada mensaje."
            ),
            reason_es=(
                "El acoso repetido afecta al bienestar del creador y a la conversación de la "
                "comunidad, y se puede reducir con la configuración de moderación de YouTube."
            ),
            evidence=evidence,
            confidence=confidence,
            priority=1 if share >= 0.1 else 2,
            suggested_format=None,
            suggested_hook_es="",
            suggested_experiment_es=(
                "Activa la retención de comentarios inapropiados en YouTube Studio y añade "
                "palabras bloqueadas. Revisa la evolución en el próximo análisis."
            ),
            kpi_es="Proporción de comentarios ofensivos sobre el total",
            caveat_es=(
                "La detección automática de lenguaje ofensivo comete errores, tanto falsos "
                "positivos como falsos negativos. Revisa los vídeos afectados antes de actuar. "
                "Ninguna recomendación de contenido de este informe se basa en estos comentarios."
            ),
        )
    ]


def generate_recommendations(context: AnalysisContext) -> list[GeneratedRecommendation]:
    """Genera todas las recomendaciones y las ordena por prioridad y confianza."""
    recommendations: list[GeneratedRecommendation] = []
    recommendations.extend(build_demand_recommendations(context))
    recommendations.extend(build_issue_recommendations(context))
    recommendations.extend(build_strength_recommendations(context))
    recommendations.extend(build_community_recommendations(context))
    recommendations.extend(build_hypothesis_recommendations(context))
    recommendations.extend(build_safety_recommendation(context))

    # Nunca se emite una recomendación de contenido basada en acoso: las de
    # seguridad son una categoría aparte y no alimentan las ideas de contenido.
    recommendations.sort(key=lambda r: (r.priority, -r.confidence.score))
    return recommendations


__all__ = [
    "MIN_COMMENTS_FOR_ISSUE",
    "MIN_COMMENTS_FOR_REQUEST",
    "MIN_COMMENTS_FOR_STRENGTH",
    "TOXICITY_ALERT_SHARE",
    "TOXICITY_ALERT_THRESHOLD",
    "Evidence",
    "GeneratedRecommendation",
    "build_community_recommendations",
    "build_demand_recommendations",
    "build_hypothesis_recommendations",
    "build_issue_recommendations",
    "build_safety_recommendation",
    "build_strength_recommendations",
    "generate_recommendations",
]
