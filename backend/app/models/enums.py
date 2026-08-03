"""Enumeraciones del dominio.

Se almacenan como texto en la base de datos para que añadir valores nuevos no
requiera una migración de tipo enum de PostgreSQL.
"""

from __future__ import annotations

from enum import StrEnum


class AnalysisStatus(StrEnum):
    QUEUED = "queued"
    FETCHING = "fetching"
    PREPROCESSING = "preprocessing"
    EMBEDDING = "embedding"
    CLUSTERING = "clustering"
    SCORING = "scoring"
    RECOMMENDING = "recommending"
    COMPLETED = "completed"
    FAILED = "failed"


#: Progreso (0-100) asociado al inicio de cada etapa.
STAGE_PROGRESS: dict[AnalysisStatus, int] = {
    AnalysisStatus.QUEUED: 0,
    AnalysisStatus.FETCHING: 10,
    AnalysisStatus.PREPROCESSING: 45,
    AnalysisStatus.EMBEDDING: 60,
    AnalysisStatus.CLUSTERING: 72,
    AnalysisStatus.SCORING: 84,
    AnalysisStatus.RECOMMENDING: 92,
    AnalysisStatus.COMPLETED: 100,
    AnalysisStatus.FAILED: 100,
}

#: Etiqueta en español que se muestra en la pantalla de progreso.
STAGE_LABELS_ES: dict[AnalysisStatus, str] = {
    AnalysisStatus.QUEUED: "En cola",
    AnalysisStatus.FETCHING: "Descargando vídeos y comentarios",
    AnalysisStatus.PREPROCESSING: "Limpiando datos",
    AnalysisStatus.EMBEDDING: "Analizando el lenguaje",
    AnalysisStatus.CLUSTERING: "Detectando temas",
    AnalysisStatus.SCORING: "Calculando tendencias",
    AnalysisStatus.RECOMMENDING: "Generando recomendaciones",
    AnalysisStatus.COMPLETED: "Completado",
    AnalysisStatus.FAILED: "Fallido",
}


class SamplingStrategy(StrEnum):
    """Cómo se eligen los comentarios que se descargan de cada vídeo."""

    RECENT = "recent"
    RELEVANT = "relevant"
    MIXED = "mixed"


class SentimentLabel(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"
    UNCERTAIN = "uncertain"


SENTIMENT_LABELS_ES: dict[str, str] = {
    SentimentLabel.POSITIVE: "Positivo",
    SentimentLabel.NEUTRAL: "Neutral",
    SentimentLabel.NEGATIVE: "Negativo",
    SentimentLabel.MIXED: "Mixto",
    SentimentLabel.UNCERTAIN: "Incierto",
}


class IntentLabel(StrEnum):
    PRAISE = "praise"
    CONSTRUCTIVE_CRITICISM = "constructive_criticism"
    INSULT = "insult"
    QUESTION = "question"
    CONTENT_REQUEST = "content_request"
    TUTORIAL_REQUEST = "tutorial_request"
    PRODUCT_REQUEST = "product_request"
    AGREEMENT = "agreement"
    DISAGREEMENT = "disagreement"
    PERSONAL_STORY = "personal_story"
    SPAM = "spam"
    OTHER = "other"


INTENT_LABELS_ES: dict[str, str] = {
    IntentLabel.PRAISE: "Elogio",
    IntentLabel.CONSTRUCTIVE_CRITICISM: "Crítica constructiva",
    IntentLabel.INSULT: "Insulto o acoso",
    IntentLabel.QUESTION: "Pregunta",
    IntentLabel.CONTENT_REQUEST: "Petición de contenido",
    IntentLabel.TUTORIAL_REQUEST: "Petición de tutorial",
    IntentLabel.PRODUCT_REQUEST: "Petición de producto o enlace",
    IntentLabel.AGREEMENT: "Acuerdo",
    IntentLabel.DISAGREEMENT: "Desacuerdo",
    IntentLabel.PERSONAL_STORY: "Historia personal",
    IntentLabel.SPAM: "Spam o promoción",
    IntentLabel.OTHER: "Otro",
}


class RecommendationCategory(StrEnum):
    DOUBLE_DOWN = "double_down"
    AUDIENCE_DEMAND = "audience_demand"
    FIX_ISSUE = "fix_issue"
    TEST_HYPOTHESIS = "test_hypothesis"
    COMMUNITY_OPPORTUNITY = "community_opportunity"
    SAFETY_ALERT = "safety_alert"


RECOMMENDATION_LABELS_ES: dict[str, str] = {
    RecommendationCategory.DOUBLE_DOWN: "Refuerza una fortaleza",
    RecommendationCategory.AUDIENCE_DEMAND: "Responde a la demanda de tu audiencia",
    RecommendationCategory.FIX_ISSUE: "Corrige un problema repetido",
    RecommendationCategory.TEST_HYPOTHESIS: "Pon a prueba una hipótesis",
    RecommendationCategory.COMMUNITY_OPPORTUNITY: "Oportunidad de comunidad",
    RecommendationCategory.SAFETY_ALERT: "Aviso de seguridad y moderación",
}


class ConfidenceLevel(StrEnum):
    LOW = "baja"
    MEDIUM = "media"
    HIGH = "alta"


class TrendDirection(StrEnum):
    RISING = "rising"
    STABLE = "stable"
    FALLING = "falling"
    UNKNOWN = "unknown"


TREND_LABELS_ES: dict[str, str] = {
    TrendDirection.RISING: "Al alza",
    TrendDirection.STABLE: "Estable",
    TrendDirection.FALLING: "A la baja",
    TrendDirection.UNKNOWN: "Sin datos suficientes",
}


class ContentFormat(StrEnum):
    SHORT = "short"
    LONG_FORM = "long_form"
    TUTORIAL = "tutorial"
    QA = "qa"
    REACTION = "reaction"
    STORYTIME = "storytime"
    SERIES = "series"


CONTENT_FORMAT_LABELS_ES: dict[str, str] = {
    ContentFormat.SHORT: "Short",
    ContentFormat.LONG_FORM: "Vídeo largo",
    ContentFormat.TUTORIAL: "Tutorial",
    ContentFormat.QA: "Preguntas y respuestas",
    ContentFormat.REACTION: "Reacción",
    ContentFormat.STORYTIME: "Storytime",
    ContentFormat.SERIES: "Serie",
}


class DataSource(StrEnum):
    """Distingue los datos reales de la API de los datos de demostración."""

    YOUTUBE_API = "youtube_api"
    DEMO = "demo"


__all__ = [
    "CONTENT_FORMAT_LABELS_ES",
    "INTENT_LABELS_ES",
    "RECOMMENDATION_LABELS_ES",
    "SENTIMENT_LABELS_ES",
    "STAGE_LABELS_ES",
    "STAGE_PROGRESS",
    "TREND_LABELS_ES",
    "AnalysisStatus",
    "ConfidenceLevel",
    "ContentFormat",
    "DataSource",
    "IntentLabel",
    "RecommendationCategory",
    "SamplingStrategy",
    "SentimentLabel",
    "TrendDirection",
]
