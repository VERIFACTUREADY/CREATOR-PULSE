"""Etapa 3 del pipeline: análisis de sentimiento multilingüe.

Backend por defecto: un clasificador léxico determinista que tiene en cuenta
negación, intensificadores, emojis, contraste y longitud del comentario. Es
explicable y no requiere descargar ningún modelo.

Backend opcional `transformers`: usa el modelo configurado en `SENTIMENT_MODEL`
si el extra `ml` está instalado. Si no puede cargarse, se degrada al léxico y
se registra el motivo, nunca se interrumpe el análisis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from app.core.config import settings
from app.core.logging import get_logger
from app.models.enums import SentimentLabel
from app.services.analysis.lexicons import (
    CONTRAST_MARKERS,
    DIMINISHER_TERMS,
    INTENSIFIER_TERMS,
    NEGATION_TERMS,
    NEGATIVE_TERMS,
    POSITIVE_TERMS,
    SARCASM_MARKERS,
    TOXIC_TERMS,
)

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[\w'’]+|[^\w\s]", re.UNICODE)
#: Ventana de tokens hacia atrás en la que una negación afecta a un término.
_NEGATION_WINDOW = 3
#: Por debajo de esta puntuación absoluta el comentario se considera neutral.
_NEUTRAL_BAND = 0.12
#: Por debajo de esta confianza el resultado se marca como incierto.
_UNCERTAIN_THRESHOLD = 0.35


@dataclass(slots=True)
class SentimentResult:
    """Resultado normalizado de sentimiento."""

    label: str
    score: float
    confidence: float
    positive_hits: int = 0
    negative_hits: int = 0
    toxicity: float | None = None
    uncertain_reason: str | None = None


class SentimentBackend(Protocol):
    def analyse(self, text: str, *, emojis: list[str] | None = None) -> SentimentResult: ...


def _lookup(term: str, table: dict[str, float]) -> float:
    return table.get(term, 0.0)


def _multiword_hits(text: str, table: dict[str, float]) -> list[tuple[str, float]]:
    """Busca las entradas del léxico formadas por varias palabras."""
    return [(term, weight) for term, weight in table.items() if " " in term and term in text]


class LexiconSentimentBackend:
    """Clasificador léxico determinista con soporte de negación y énfasis."""

    def analyse(self, text: str, *, emojis: list[str] | None = None) -> SentimentResult:
        lowered = text.lower().strip()
        if not lowered and not emojis:
            return SentimentResult(
                label=SentimentLabel.NEUTRAL,
                score=0.0,
                confidence=0.2,
                uncertain_reason="comentario vacío",
            )

        tokens = _TOKEN_RE.findall(lowered)
        positive_total = 0.0
        negative_total = 0.0
        positive_hits = 0
        negative_hits = 0

        for index, token in enumerate(tokens):
            pos_weight = _lookup(token, POSITIVE_TERMS)
            neg_weight = _lookup(token, NEGATIVE_TERMS)
            if pos_weight == 0.0 and neg_weight == 0.0:
                continue

            modifier = 1.0
            negated = False
            window = tokens[max(0, index - _NEGATION_WINDOW) : index]
            for prev in window:
                if prev in NEGATION_TERMS:
                    negated = True
                modifier *= INTENSIFIER_TERMS.get(prev, 1.0)
                modifier *= DIMINISHER_TERMS.get(prev, 1.0)
            modifier = min(modifier, 2.0)

            if pos_weight:
                value = pos_weight * modifier
                if negated:
                    negative_total += value * 0.8
                    negative_hits += 1
                else:
                    positive_total += value
                    positive_hits += 1
            if neg_weight:
                value = neg_weight * modifier
                if negated:
                    positive_total += value * 0.6
                    positive_hits += 1
                else:
                    negative_total += value
                    negative_hits += 1

        # Entradas de varias palabras («no se escucha», «too long»).
        for _term, weight in _multiword_hits(lowered, NEGATIVE_TERMS):
            negative_total += weight
            negative_hits += 1
        for _term, weight in _multiword_hits(lowered, POSITIVE_TERMS):
            positive_total += weight
            positive_hits += 1

        # Emojis: aportan señal, sobre todo en comentarios muy cortos.
        for emoji in emojis or []:
            positive_total += POSITIVE_TERMS.get(emoji, 0.0)
            negative_total += NEGATIVE_TERMS.get(emoji, 0.0)
            if emoji in POSITIVE_TERMS:
                positive_hits += 1
            if emoji in NEGATIVE_TERMS:
                negative_hits += 1

        toxicity = self._toxicity(lowered) if settings.enable_toxicity_analysis else None
        if toxicity:
            negative_total += toxicity
            negative_hits += 1

        total = positive_total + negative_total
        score = 0.0 if total == 0 else (positive_total - negative_total) / total

        label, confidence, reason = self._decide(
            score=score,
            total=total,
            positive_hits=positive_hits,
            negative_hits=negative_hits,
            text=lowered,
            token_count=len(tokens),
        )

        return SentimentResult(
            label=label,
            score=round(score, 4),
            confidence=round(confidence, 4),
            positive_hits=positive_hits,
            negative_hits=negative_hits,
            toxicity=round(toxicity, 4) if toxicity is not None else None,
            uncertain_reason=reason,
        )

    @staticmethod
    def _toxicity(lowered: str) -> float:
        """Probabilidad aproximada de acoso o insulto (seguridad del creador)."""
        best = 0.0
        for term, weight in TOXIC_TERMS.items():
            if " " in term:
                if term in lowered:
                    best = max(best, weight)
            elif re.search(rf"\b{re.escape(term)}\b", lowered):
                best = max(best, weight)
        return best

    @staticmethod
    def _decide(
        *,
        score: float,
        total: float,
        positive_hits: int,
        negative_hits: int,
        text: str,
        token_count: int,
    ) -> tuple[str, float, str | None]:
        reason: str | None = None

        if total == 0.0:
            return SentimentLabel.NEUTRAL, 0.3, "sin términos de sentimiento reconocidos"

        # Elogio y crítica en el mismo comentario.
        has_contrast = any(marker in text for marker in CONTRAST_MARKERS)
        if positive_hits >= 1 and negative_hits >= 1 and (has_contrast or abs(score) < 0.35):
            confidence = min(0.6, 0.3 + total / 6.0)
            return SentimentLabel.MIXED, confidence, "elogio y crítica en el mismo comentario"

        # La confianza crece con la evidencia acumulada y con la polaridad.
        confidence = min(0.95, (total / 3.0) * 0.5 + abs(score) * 0.5)

        # Comentarios muy cortos son menos fiables.
        if token_count <= 2:
            confidence *= 0.7
            reason = "comentario muy corto"

        # Posible sarcasmo: se reduce la confianza, nunca se invierte la etiqueta.
        if any(marker in text for marker in SARCASM_MARKERS):
            confidence *= 0.5
            reason = "posible ironía o sarcasmo"

        if abs(score) < _NEUTRAL_BAND:
            return SentimentLabel.NEUTRAL, max(0.25, confidence), reason

        label = SentimentLabel.POSITIVE if score > 0 else SentimentLabel.NEGATIVE
        if confidence < _UNCERTAIN_THRESHOLD:
            return (
                SentimentLabel.UNCERTAIN,
                confidence,
                reason or "señal de sentimiento débil",
            )
        return label, confidence, reason


class TransformersSentimentBackend:
    """Backend neuronal opcional. Requiere el extra `ml`."""

    def __init__(self, model_name: str) -> None:
        from transformers import pipeline

        self._pipeline = pipeline(
            "sentiment-analysis", model=model_name, truncation=True, max_length=256
        )
        self._fallback = LexiconSentimentBackend()

    def analyse(self, text: str, *, emojis: list[str] | None = None) -> SentimentResult:
        if not text.strip():
            return self._fallback.analyse(text, emojis=emojis)
        try:
            raw = self._pipeline(text[:1000])[0]
        except Exception as exc:  # pragma: no cover - depende del entorno
            logger.warning("transformers_sentiment_failed", error=str(exc))
            return self._fallback.analyse(text, emojis=emojis)

        label_raw = str(raw.get("label", "")).lower()
        confidence = float(raw.get("score", 0.0))
        label = normalise_label(label_raw)
        polarity: dict[str, float] = {
            SentimentLabel.POSITIVE: confidence,
            SentimentLabel.NEGATIVE: -confidence,
        }
        score = polarity.get(label, 0.0)
        if confidence < _UNCERTAIN_THRESHOLD:
            label = SentimentLabel.UNCERTAIN
        toxicity = (
            LexiconSentimentBackend._toxicity(text.lower())
            if settings.enable_toxicity_analysis
            else None
        )
        return SentimentResult(
            label=label,
            score=round(score, 4),
            confidence=round(confidence, 4),
            toxicity=toxicity,
        )


def normalise_label(raw_label: str) -> str:
    """Normaliza las múltiples convenciones de etiqueta de los modelos públicos.

    Cubre `POSITIVE`/`NEGATIVE`, `LABEL_0..2`, `1 star`..`5 stars` y variantes
    en español.
    """
    label = raw_label.strip().lower()
    if label in {"positive", "positivo", "pos", "label_2", "5 stars", "4 stars"}:
        return SentimentLabel.POSITIVE
    if label in {"negative", "negativo", "neg", "label_0", "1 star", "2 stars"}:
        return SentimentLabel.NEGATIVE
    if label in {"neutral", "neutro", "label_1", "3 stars"}:
        return SentimentLabel.NEUTRAL
    if label in {"mixed", "mixto"}:
        return SentimentLabel.MIXED
    return SentimentLabel.UNCERTAIN


def build_sentiment_backend() -> SentimentBackend:
    """Crea el backend configurado, degradando al léxico si no está disponible."""
    if settings.sentiment_backend == "transformers":
        try:
            return TransformersSentimentBackend(settings.sentiment_model)
        except Exception as exc:
            logger.warning(
                "sentiment_backend_fallback",
                requested="transformers",
                error=str(exc),
                using="lexicon",
            )
    return LexiconSentimentBackend()


__all__ = [
    "LexiconSentimentBackend",
    "SentimentBackend",
    "SentimentResult",
    "TransformersSentimentBackend",
    "build_sentiment_backend",
    "normalise_label",
]
