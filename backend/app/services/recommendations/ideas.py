"""Generador de ideas de contenido respaldadas por evidencia.

Cada idea nace de una oportunidad concreta detectada en los comentarios del
canal analizado. No se generan ideas genéricas: si no hay evidencia, se generan
ideas exploratorias explícitamente etiquetadas como de baja confianza.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.enums import ContentFormat, IntentLabel, RecommendationCategory
from app.services.analysis.aspects import aspect_label_es
from app.services.analysis.dtos import AnalysisContext, TopicSummary
from app.services.recommendations.confidence import ConfidenceOutcome
from app.services.recommendations.generator import GeneratedRecommendation

#: Número máximo de ideas que se muestran.
MAX_IDEAS = 6


@dataclass
class GeneratedIdea:
    """Idea de vídeo lista para persistir."""

    title_es: str
    concept_es: str
    why_es: str
    evidence: dict[str, Any]
    suggested_format: str
    hook_es: str
    call_to_action_es: str
    experiment_es: str
    kpi_es: str
    confidence_score: float
    confidence_level: str
    overinterpretation_risk_es: str
    topic_cluster_key: str | None = None


def _format_for_topic(topic: TopicSummary, context: AnalysisContext) -> str:
    """Elige el formato en función de las intenciones observadas en el tema."""
    comments = [c for c in context.usable_comments if c.cluster_key == topic.cluster_key]
    intents = [intent for c in comments for intent in c.intents]

    if intents.count(IntentLabel.TUTORIAL_REQUEST) >= 2:
        return ContentFormat.TUTORIAL
    if intents.count(IntentLabel.QUESTION) >= 3:
        return ContentFormat.QA
    if intents.count(IntentLabel.PERSONAL_STORY) >= 3:
        return ContentFormat.STORYTIME
    if topic.comment_count >= 40 and topic.unique_video_count >= 4:
        return ContentFormat.SERIES
    if topic.comment_count <= 12:
        return ContentFormat.SHORT
    return ContentFormat.LONG_FORM


def _evidence_lines(topic: TopicSummary, context: AnalysisContext) -> dict[str, Any]:
    return {
        "supporting_comments": topic.comment_count,
        "supporting_videos": topic.unique_video_count,
        "total_videos_analysed": context.total_videos,
        "total_comments_analysed": context.total_comments_analysed,
        "share_of_comments": round(topic.share_of_comments, 4),
        "request_count": topic.request_count,
        "question_count": topic.question_count,
        "positive_count": topic.positive_count,
        "negative_count": topic.negative_count,
        "trend_direction": topic.trend_direction,
        "dominant_video_share": topic.dominant_video_share,
        "bullets_es": _evidence_bullets(topic, context),
        "representative_comments": topic.representative_comments[:2],
    }


def _evidence_bullets(topic: TopicSummary, context: AnalysisContext) -> list[str]:
    bullets = [
        f"{topic.comment_count} comentarios mencionan «{topic.label_es}» "
        f"({topic.share_of_comments:.0%} de la muestra analizada).",
        f"El tema aparece en {topic.unique_video_count} de los {context.total_videos} "
        "vídeos analizados.",
    ]
    if topic.request_count:
        bullets.append(f"{topic.request_count} comentarios lo piden explícitamente.")
    if topic.question_count:
        bullets.append(f"{topic.question_count} comentarios formulan preguntas sobre ello.")
    if topic.trend_direction == "rising" and topic.trend_change is not None:
        bullets.append(
            f"Las menciones han crecido un {topic.trend_change:.0%} respecto al periodo anterior."
        )
    return bullets


def _risk_text(topic: TopicSummary, confidence_level: str) -> str:
    risks: list[str] = []
    if topic.dominant_video_share >= 0.5:
        risks.append(
            f"El {topic.dominant_video_share:.0%} de la evidencia viene de un único vídeo, "
            "así que puede reflejar la reacción a ese vídeo y no un interés estable."
        )
    if topic.unique_video_count < 2:
        risks.append("Sólo un vídeo respalda este tema.")
    if confidence_level == "baja":
        risks.append("La muestra es pequeña: trátalo como un experimento, no como una certeza.")
    if topic.trend_direction == "unknown":
        risks.append("No hay histórico suficiente para saber si el interés está creciendo.")
    if not risks:
        risks.append(
            "El interés observado procede de una muestra de comentarios, "
            "no de toda tu audiencia. No garantiza que el vídeo funcione."
        )
    return " ".join(risks)


def build_ideas_from_recommendations(
    context: AnalysisContext, recommendations: list[GeneratedRecommendation]
) -> list[GeneratedIdea]:
    """Convierte las oportunidades de mayor prioridad en ideas concretas."""
    topics_by_key = {t.cluster_key: t for t in context.topics}
    ideas: list[GeneratedIdea] = []
    used_keys: set[str] = set()

    for rec in recommendations:
        if len(ideas) >= MAX_IDEAS:
            break
        # Las alertas de seguridad nunca generan ideas de contenido.
        if rec.category == RecommendationCategory.SAFETY_ALERT:
            continue
        key = rec.topic_cluster_key
        if not key or key in used_keys:
            continue
        topic = topics_by_key.get(key)
        if topic is None:
            continue
        used_keys.add(key)
        ideas.append(_idea_from_topic(topic, context, rec.confidence, rec.category))

    if not ideas:
        ideas.extend(_exploratory_ideas(context))
    return ideas[:MAX_IDEAS]


def _idea_from_topic(
    topic: TopicSummary,
    context: AnalysisContext,
    confidence: ConfidenceOutcome,
    category: str,
) -> GeneratedIdea:
    fmt = _format_for_topic(topic, context)
    aspect = topic.top_aspects[0] if topic.top_aspects else None
    aspect_text = aspect_label_es(aspect).lower() if aspect else topic.label_es.lower()

    if category == RecommendationCategory.AUDIENCE_DEMAND:
        title = f"«{topic.label_es}»: el vídeo que te están pidiendo"
        concept = (
            f"Un vídeo centrado exclusivamente en {aspect_text}, respondiendo de forma directa a "
            f"las {topic.request_count} peticiones que has recibido en los comentarios."
        )
        hook = (
            f"«Me habéis pedido esto {topic.request_count} veces en los comentarios, "
            "así que hoy lo hacemos.»"
        )
    elif category == RecommendationCategory.FIX_ISSUE:
        title = f"«Lo he arreglado»: {topic.label_es.lower()}"
        concept = (
            f"Un vídeo en el que aplicas el cambio que pide la audiencia sobre {aspect_text} "
            "y lo mencionas de forma explícita al principio."
        )
        hook = "«He leído lo que me decís sobre esto y he cambiado cómo lo hago.»"
    elif category == RecommendationCategory.COMMUNITY_OPPORTUNITY:
        title = f"Respondo de una vez: {topic.label_es.lower()}"
        concept = (
            f"Un vídeo de preguntas y respuestas centrado en las {topic.question_count} dudas "
            f"repetidas sobre {aspect_text}."
        )
        hook = "«Esta pregunta me la hacéis en todos los vídeos, así que la respondo entera.»"
    else:
        title = f"Cómo consigo {aspect_text}"
        concept = (
            f"Un vídeo que profundiza en {aspect_text}, el aspecto que tu audiencia menciona con "
            "más frecuencia de forma positiva."
        )
        hook = f"«Me preguntáis muchísimo por {aspect_text}…»"

    return GeneratedIdea(
        title_es=title,
        concept_es=concept,
        why_es=(
            f"Encaja con tu audiencia porque «{topic.label_es}» aparece en {topic.comment_count} "
            f"comentarios repartidos por {topic.unique_video_count} vídeos, no en uno solo."
        ),
        evidence=_evidence_lines(topic, context),
        suggested_format=fmt,
        hook_es=hook,
        call_to_action_es=(
            "«Si queréis que profundice en alguna parte concreta, decídmelo en los comentarios "
            "y lo convierto en el próximo vídeo.»"
        ),
        experiment_es=(
            f"Publica un {'Short de 30-45 segundos' if fmt == ContentFormat.SHORT else 'vídeo'} "
            "sobre esta idea y compara sus comentarios por cada 1.000 visualizaciones con la "
            f"mediana del canal ({context.baseline.median_comments_per_1000:.1f})."
        ),
        kpi_es="Comentarios por cada 1.000 visualizaciones frente a la mediana del canal",
        confidence_score=confidence.score,
        confidence_level=confidence.level,
        overinterpretation_risk_es=_risk_text(topic, confidence.level),
        topic_cluster_key=topic.cluster_key,
    )


def _exploratory_ideas(context: AnalysisContext) -> list[GeneratedIdea]:
    """Ideas de bajo compromiso cuando el canal aporta muy pocos datos.

    Siguen ancladas al canal: usan sus vídeos con mejor rendimiento relativo y
    los aspectos que sí se han observado, y se etiquetan como experimentos.
    """
    ideas: list[GeneratedIdea] = []

    best_videos = sorted(
        (
            (vid, perf)
            for vid, perf in context.performances.items()
            if perf.views_relative_to_median is not None and not perf.age_caveat
        ),
        key=lambda item: -(item[1].views_relative_to_median or 0.0),
    )[:2]

    for youtube_video_id, perf in best_videos:
        title = context.video_titles.get(youtube_video_id, "tu vídeo con mejor rendimiento")
        ideas.append(
            GeneratedIdea(
                title_es=f"Segunda parte de «{title}»",
                concept_es=(
                    f"Retoma el enfoque de «{title}», que acumula "
                    f"{perf.views_relative_to_median:.2f}× la mediana de visualizaciones del "
                    "canal, y desarrolla la parte que quedó fuera."
                ),
                why_es=(
                    "No hay comentarios suficientes para detectar temas, así que la única señal "
                    "fiable disponible es el rendimiento relativo de tus propios vídeos."
                ),
                evidence={
                    "supporting_comments": 0,
                    "supporting_videos": 1,
                    "total_videos_analysed": context.total_videos,
                    "total_comments_analysed": context.total_comments_analysed,
                    "views_relative_to_median": perf.views_relative_to_median,
                    "bullets_es": [
                        f"«{title}» tiene {perf.views_relative_to_median:.2f}× la mediana de "
                        "visualizaciones del canal.",
                        "No hay suficientes comentarios analizados para detectar temas.",
                    ],
                },
                suggested_format=ContentFormat.LONG_FORM,
                hook_es="«Muchos me pedisteis más sobre esto, así que aquí va la segunda parte.»",
                call_to_action_es=(
                    "«Dime en los comentarios qué parte quieres que desarrolle más.»"
                ),
                experiment_es=(
                    "Publica la segunda parte y compara sus visualizaciones y sus comentarios por "
                    "cada 1.000 visualizaciones con los del vídeo original."
                ),
                kpi_es="Visualizaciones y comentarios por cada 1.000 visualizaciones",
                confidence_score=0.2,
                confidence_level="baja",
                overinterpretation_risk_es=(
                    "Esta idea es un experimento exploratorio: no hay comentarios suficientes "
                    "para saber qué quiere tu audiencia. Un solo vídeo con buen rendimiento "
                    "puede deberse al azar, a la fecha de publicación o a factores externos."
                ),
            )
        )

    if not ideas:
        ideas.append(
            GeneratedIdea(
                title_es="Vídeo de presentación para generar conversación",
                concept_es=(
                    "Un vídeo corto que pregunte de forma explícita a la audiencia qué quiere ver, "
                    "para conseguir la base de comentarios que ahora falta."
                ),
                why_es=(
                    "El canal no tiene comentarios públicos suficientes para extraer conclusiones. "
                    "El primer paso es generar feedback que analizar."
                ),
                evidence={
                    "supporting_comments": 0,
                    "supporting_videos": 0,
                    "total_videos_analysed": context.total_videos,
                    "total_comments_analysed": context.total_comments_analysed,
                    "bullets_es": [
                        f"Sólo se han analizado {context.total_comments_analysed} comentarios "
                        f"en {context.total_videos} vídeos.",
                        "No hay evidencia suficiente para recomendar un tema concreto.",
                    ],
                },
                suggested_format=ContentFormat.SHORT,
                hook_es="«Necesito que me ayudéis a decidir el próximo vídeo.»",
                call_to_action_es="«Escribe en los comentarios qué quieres ver primero.»",
                experiment_es=(
                    "Publica el Short, fija un comentario con la pregunta y vuelve a lanzar el "
                    "análisis cuando tengas al menos 100 comentarios nuevos."
                ),
                kpi_es="Número de comentarios recibidos",
                confidence_score=0.15,
                confidence_level="baja",
                overinterpretation_risk_es=(
                    "Es una idea genérica precisamente porque no hay datos del canal en los que "
                    "basarse. No la interpretes como una conclusión sobre tu audiencia."
                ),
            )
        )
    return ideas


__all__ = ["MAX_IDEAS", "GeneratedIdea", "build_ideas_from_recommendations"]
