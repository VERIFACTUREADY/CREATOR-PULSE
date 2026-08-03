"""Pruebas de sentimiento, intenciones y aspectos."""

from __future__ import annotations

import pytest
from app.models.enums import IntentLabel, SentimentLabel
from app.services.analysis.aspects import (
    build_document_frequency,
    distinctive_keywords,
    extract_aspects,
    top_keywords,
)
from app.services.analysis.intents import extract_intents
from app.services.analysis.sentiment import (
    LexiconSentimentBackend,
    build_sentiment_backend,
    normalise_label,
)

backend = LexiconSentimentBackend()


# --- Sentimiento ------------------------------------------------------------


def test_positive_comment() -> None:
    result = backend.analyse("Me encanta este vídeo, es genial")
    assert result.label == SentimentLabel.POSITIVE
    assert result.score > 0


def test_negative_comment() -> None:
    result = backend.analyse("Es horrible, el peor vídeo del canal")
    assert result.label == SentimentLabel.NEGATIVE
    assert result.score < 0


def test_negation_inverts_polarity() -> None:
    positive = backend.analyse("Es genial")
    negated = backend.analyse("No es genial")
    assert positive.score > 0
    assert negated.score < 0


def test_intensifier_increases_magnitude() -> None:
    plain = backend.analyse("Es bueno")
    intense = backend.analyse("Es muy bueno")
    assert abs(intense.score) >= abs(plain.score)


def test_mixed_sentiment_with_contrast_marker() -> None:
    result = backend.analyse("El contenido es genial pero el audio es horrible")
    assert result.label == SentimentLabel.MIXED
    assert result.uncertain_reason


def test_emoji_only_comment_is_scored() -> None:
    result = backend.analyse("", emojis=["😍", "❤️"])
    assert result.label == SentimentLabel.POSITIVE


def test_empty_comment_is_neutral_with_low_confidence() -> None:
    result = backend.analyse("")
    assert result.label == SentimentLabel.NEUTRAL
    assert result.confidence < 0.5


def test_short_comment_reduces_confidence() -> None:
    short = backend.analyse("genial")
    long = backend.analyse("Me parece un vídeo genial, muy útil y muy bien explicado")
    assert short.confidence < long.confidence


def test_sarcasm_marker_reduces_confidence_without_flipping() -> None:
    plain = backend.analyse("Qué bueno")
    sarcastic = backend.analyse("sí claro qué bueno")
    assert sarcastic.confidence < plain.confidence


def test_neutral_comment() -> None:
    assert backend.analyse("Vengo del short").label == SentimentLabel.NEUTRAL


def test_toxicity_is_detected() -> None:
    result = backend.analyse("Eres un idiota, cállate")
    assert result.toxicity is not None
    assert result.toxicity >= 0.7


def test_toxicity_absent_in_neutral_comment() -> None:
    assert not backend.analyse("Buen vídeo").toxicity


def test_multiword_negative_phrase() -> None:
    assert backend.analyse("No se escucha la voz").label == SentimentLabel.NEGATIVE


def test_english_comment_is_supported() -> None:
    assert backend.analyse("This is an amazing video, I love it").label == SentimentLabel.POSITIVE


def test_scores_are_bounded() -> None:
    for text in ("increíble genial perfecto excelente" * 5, "horrible basura fatal" * 5):
        result = backend.analyse(text)
        assert -1.0 <= result.score <= 1.0
        assert 0.0 <= result.confidence <= 1.0


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("POSITIVE", SentimentLabel.POSITIVE),
        ("LABEL_2", SentimentLabel.POSITIVE),
        ("5 stars", SentimentLabel.POSITIVE),
        ("negative", SentimentLabel.NEGATIVE),
        ("LABEL_0", SentimentLabel.NEGATIVE),
        ("1 star", SentimentLabel.NEGATIVE),
        ("neutral", SentimentLabel.NEUTRAL),
        ("LABEL_1", SentimentLabel.NEUTRAL),
        ("algo raro", SentimentLabel.UNCERTAIN),
    ],
)
def test_normalise_label(raw: str, expected: str) -> None:
    assert normalise_label(raw) == expected


def test_build_sentiment_backend_defaults_to_lexicon() -> None:
    assert isinstance(build_sentiment_backend(), LexiconSentimentBackend)


# --- Intenciones ------------------------------------------------------------


def test_question_requires_interrogative_or_question_mark() -> None:
    assert extract_intents("¿qué micrófono usas?").is_question
    assert extract_intents("cómo lo haces").is_question
    # `que` sin tilde es conjunción: no convierte la frase en pregunta.
    assert not extract_intents("me alegro de que subas vídeos").is_question


def test_tutorial_request_is_also_a_content_request() -> None:
    result = extract_intents("haz un tutorial paso a paso porfa")
    assert IntentLabel.TUTORIAL_REQUEST in result.labels
    assert IntentLabel.CONTENT_REQUEST in result.labels
    assert result.is_request


def test_product_request() -> None:
    result = extract_intents("¿qué cámara usas? déjanos el enlace")
    assert IntentLabel.PRODUCT_REQUEST in result.labels
    assert result.is_request


def test_praise_intent() -> None:
    assert IntentLabel.PRAISE in extract_intents("me encanta, eres un crack").labels


def test_insult_overrides_constructive_criticism() -> None:
    result = extract_intents(
        "eres un idiota, deberías mejorar el audio", sentiment_label="negative", toxicity=0.9
    )
    assert IntentLabel.INSULT in result.labels
    assert IntentLabel.CONSTRUCTIVE_CRITICISM not in result.labels


def test_high_toxicity_implies_insult_without_pattern() -> None:
    assert IntentLabel.INSULT in extract_intents("texto neutro", toxicity=0.85).labels


def test_spam_intent() -> None:
    assert IntentLabel.SPAM in extract_intents("mira mi canal", is_spam=True).labels


def test_negative_with_aspect_becomes_constructive_criticism() -> None:
    result = extract_intents("el audio suena mal", sentiment_label="negative", has_aspect=True)
    assert IntentLabel.CONSTRUCTIVE_CRITICISM in result.labels


def test_negative_without_aspect_stays_subjective() -> None:
    """Un rechazo sin aspecto concreto no es una crítica accionable."""
    result = extract_intents("no me gusta nada", sentiment_label="negative", has_aspect=False)
    assert IntentLabel.CONSTRUCTIVE_CRITICISM not in result.labels


def test_multiple_intents_can_coexist() -> None:
    result = extract_intents("me encanta el canal, ¿puedes hacer un tutorial paso a paso?")
    assert IntentLabel.PRAISE in result.labels
    assert IntentLabel.TUTORIAL_REQUEST in result.labels
    assert result.is_question


def test_other_intent_when_nothing_matches() -> None:
    assert extract_intents("xyz abc").labels == [IntentLabel.OTHER]


def test_empty_text_returns_other() -> None:
    assert extract_intents("").labels == [IntentLabel.OTHER]


# --- Aspectos ---------------------------------------------------------------


def test_extract_aspects_audio() -> None:
    assert "audio" in extract_aspects("el micrófono suena mal, no se escucha").aspects


def test_extract_aspects_multiple() -> None:
    aspects = extract_aspects("el humor es genial pero la iluminación está oscura").aspects
    assert "humor" in aspects
    assert "iluminacion" in aspects


def test_extract_aspects_returns_empty_when_nothing_matches() -> None:
    """Ningún comentario se fuerza a encajar en la taxonomía."""
    assert extract_aspects("primero jaja").aspects == []


def test_extract_aspects_keywords_exclude_stopwords() -> None:
    keywords = extract_aspects("el vídeo sobre maquillaje profesional está muy bien").keywords
    assert "que" not in keywords
    assert "maquillaje" in keywords


def test_top_keywords_ranks_by_frequency() -> None:
    assert top_keywords([["audio", "voz"], ["audio"], ["audio", "ruido"]], limit=1) == ["audio"]


def test_distinctive_keywords_ignores_channel_wide_terms() -> None:
    """Una palabra común a todo el canal no distingue a ningún tema."""
    group = [["audio", "gracias"], ["audio", "gracias"], ["audio", "gracias"]]
    corpus = build_document_frequency(group + [["gracias"]] * 60)
    result = distinctive_keywords(group, corpus, corpus_size=63, limit=2)
    assert result[0] == "audio"


def test_distinctive_keywords_handles_empty_input() -> None:
    assert distinctive_keywords([], build_document_frequency([]), 0) == []
