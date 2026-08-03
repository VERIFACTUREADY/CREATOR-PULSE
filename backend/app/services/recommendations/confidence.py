"""Cálculo transparente de la confianza de una conclusión.

La confianza no es una opinión del modelo: es una función explícita del tamaño
de la muestra, de cuántos vídeos la respaldan, de la concentración en un único
vídeo y de la certeza de los clasificadores. Cada penalización queda registrada
para poder mostrarla al usuario.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import ConfidenceLevel

#: Comentarios a partir de los cuales el volumen deja de aportar confianza.
SATURATION_COMMENTS = 60
#: Vídeos a partir de los cuales la cobertura deja de aportar confianza.
SATURATION_VIDEOS = 8
#: Umbrales de nivel legible.
HIGH_THRESHOLD = 0.68
MEDIUM_THRESHOLD = 0.40
#: Un tema soportado por menos de estos vídeos nunca puede ser de confianza alta.
MIN_VIDEOS_FOR_HIGH = 2


@dataclass
class ConfidenceInput:
    """Factores que entran en el cálculo."""

    supporting_comments: int = 0
    supporting_videos: int = 0
    total_videos: int = 0
    total_comments: int = 0
    dominant_video_share: float = 0.0
    trend_confidence: float = 0.0
    trend_consistent: bool = False
    classifier_confidence: float = 0.5
    cluster_quality: float = 0.5
    recency_share: float = 0.0
    spam_or_duplicate_share: float = 0.0
    association_available: bool = False
    association_strength: float = 0.0


@dataclass
class ConfidenceOutcome:
    """Resultado del cálculo, con su desglose."""

    score: float
    level: str
    factors: dict[str, float] = field(default_factory=dict)
    penalties_es: list[str] = field(default_factory=list)
    caps_es: list[str] = field(default_factory=list)

    @property
    def is_high(self) -> bool:
        return self.level == ConfidenceLevel.HIGH


def compute_confidence(data: ConfidenceInput) -> ConfidenceOutcome:
    """Devuelve la puntuación (0-1), el nivel legible y el desglose."""
    volume = min(1.0, data.supporting_comments / SATURATION_COMMENTS)
    breadth = min(1.0, data.supporting_videos / SATURATION_VIDEOS)
    coverage = (
        min(1.0, data.supporting_videos / data.total_videos) if data.total_videos > 0 else 0.0
    )

    factors = {
        "volumen_comentarios": round(volume, 3),
        "amplitud_videos": round(breadth, 3),
        "cobertura_canal": round(coverage, 3),
        "confianza_tendencia": round(data.trend_confidence, 3),
        "certeza_clasificador": round(data.classifier_confidence, 3),
        "calidad_cluster": round(data.cluster_quality, 3),
        "recencia": round(data.recency_share, 3),
    }

    score = (
        0.28 * volume
        + 0.22 * breadth
        + 0.12 * coverage
        + 0.10 * data.trend_confidence
        + 0.14 * data.classifier_confidence
        + 0.09 * data.cluster_quality
        + 0.05 * data.recency_share
    )

    if data.association_available:
        score += 0.05 * data.association_strength
        factors["asociacion_rendimiento"] = round(data.association_strength, 3)

    if data.trend_consistent:
        score += 0.03

    penalties: list[str] = []
    caps: list[str] = []

    # --- Penalizaciones ------------------------------------------------
    if data.dominant_video_share >= 0.6:
        score *= 0.65
        penalties.append(
            f"El {data.dominant_video_share:.0%} de los comentarios que respaldan esta "
            "conclusión proceden de un solo vídeo."
        )
    elif data.dominant_video_share >= 0.4:
        score *= 0.85
        penalties.append(
            f"Un único vídeo aporta el {data.dominant_video_share:.0%} de la evidencia."
        )

    if data.spam_or_duplicate_share >= 0.3:
        score *= 0.6
        penalties.append(
            f"El {data.spam_or_duplicate_share:.0%} de los comentarios del tema parecen "
            "spam o mensajes repetidos."
        )

    if data.classifier_confidence < 0.35:
        score *= 0.75
        penalties.append("La clasificación automática de estos comentarios tiene poca certeza.")

    if data.supporting_comments <= 2:
        score *= 0.5
        penalties.append("La conclusión se apoya en muy pocos comentarios.")

    score = max(0.0, min(1.0, score))
    level = _level_for(score)

    # --- Topes duros ---------------------------------------------------
    # El aviso se registra siempre que la restricción es aplicable, no sólo
    # cuando llega a recortar el nivel: al creador le sirve saber cuál es el
    # factor que impide que una conclusión sea de confianza alta.
    if data.supporting_videos < MIN_VIDEOS_FOR_HIGH:
        if level == ConfidenceLevel.HIGH:
            level = ConfidenceLevel.MEDIUM
        caps.append(
            "La confianza no puede ser alta porque menos de dos vídeos respaldan la conclusión."
        )
    if data.supporting_comments <= 1:
        level = ConfidenceLevel.LOW
        caps.append("Un único comentario no representa a la audiencia.")
    if data.dominant_video_share >= 0.7 and level == ConfidenceLevel.HIGH:
        level = ConfidenceLevel.MEDIUM
        caps.append("La confianza no puede ser alta porque un solo vídeo domina la evidencia.")
    if data.spam_or_duplicate_share >= 0.5:
        level = ConfidenceLevel.LOW
        caps.append("La mayoría de los comentarios del tema parecen duplicados o spam.")
    if data.classifier_confidence < 0.25 and level == ConfidenceLevel.HIGH:
        level = ConfidenceLevel.MEDIUM
        caps.append("El clasificador de sentimiento tiene una certeza baja en este tema.")

    return ConfidenceOutcome(
        score=round(score, 4), level=level, factors=factors, penalties_es=penalties, caps_es=caps
    )


def _level_for(score: float) -> str:
    if score >= HIGH_THRESHOLD:
        return ConfidenceLevel.HIGH
    if score >= MEDIUM_THRESHOLD:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def level_label_es(level: str) -> str:
    return {"alta": "Alta", "media": "Media", "baja": "Baja"}.get(level, "Baja")


__all__ = [
    "HIGH_THRESHOLD",
    "MEDIUM_THRESHOLD",
    "MIN_VIDEOS_FOR_HIGH",
    "SATURATION_COMMENTS",
    "SATURATION_VIDEOS",
    "ConfidenceInput",
    "ConfidenceOutcome",
    "compute_confidence",
    "level_label_es",
]
