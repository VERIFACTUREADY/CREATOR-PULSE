"""Etapa 4 del pipeline: extracción de intenciones.

Un comentario puede tener varias intenciones a la vez (por ejemplo elogio +
petición de tutorial), así que la clasificación es multietiqueta.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import IntentLabel
from app.services.analysis.lexicons import INTENT_PATTERNS

#: Intenciones que se consideran una petición accionable para el creador.
REQUEST_INTENTS: frozenset[str] = frozenset(
    {
        IntentLabel.CONTENT_REQUEST,
        IntentLabel.TUTORIAL_REQUEST,
        IntentLabel.PRODUCT_REQUEST,
    }
)

#: Intenciones que representan crítica (constructiva o no).
CRITICISM_INTENTS: frozenset[str] = frozenset(
    {IntentLabel.CONSTRUCTIVE_CRITICISM, IntentLabel.INSULT}
)


@dataclass(slots=True)
class IntentResult:
    labels: list[str]
    is_question: bool
    is_request: bool

    @property
    def has_criticism(self) -> bool:
        return bool(set(self.labels) & CRITICISM_INTENTS)


def extract_intents(
    normalised_text: str,
    *,
    sentiment_label: str | None = None,
    toxicity: float | None = None,
    is_spam: bool = False,
    has_aspect: bool = False,
) -> IntentResult:
    """Detecta las intenciones presentes en un comentario ya normalizado."""
    labels: set[str] = set()

    if is_spam:
        labels.add(IntentLabel.SPAM)

    text = normalised_text or ""
    if text:
        for intent, patterns in INTENT_PATTERNS.items():
            if any(pattern.search(text) for pattern in patterns):
                labels.add(intent)

    # Una toxicidad alta implica insulto aunque no case ningún patrón concreto.
    if toxicity is not None and toxicity >= 0.7:
        labels.add(IntentLabel.INSULT)

    # Un insulto no se cuenta también como crítica constructiva.
    if IntentLabel.INSULT in labels:
        labels.discard(IntentLabel.CONSTRUCTIVE_CRITICISM)

    # Una petición de tutorial es también una petición de contenido.
    if IntentLabel.TUTORIAL_REQUEST in labels:
        labels.add(IntentLabel.CONTENT_REQUEST)

    # Un comentario negativo que señala un aspecto concreto del vídeo se cuenta
    # como crítica constructiva aunque no use una fórmula de sugerencia. Si no
    # señala ningún aspecto, se queda como rechazo subjetivo: no es accionable.
    if (
        sentiment_label in {"negative", "mixed"}
        and has_aspect
        and IntentLabel.INSULT not in labels
        and not labels & {IntentLabel.CONSTRUCTIVE_CRITICISM, IntentLabel.SPAM}
    ):
        labels.add(IntentLabel.CONSTRUCTIVE_CRITICISM)

    if not labels:
        labels.add(IntentLabel.OTHER)

    is_question = IntentLabel.QUESTION in labels
    is_request = bool(labels & REQUEST_INTENTS)
    return IntentResult(labels=sorted(labels), is_question=is_question, is_request=is_request)


__all__ = ["CRITICISM_INTENTS", "REQUEST_INTENTS", "IntentResult", "extract_intents"]
