"""Etapa 5 del pipeline: extracción de aspectos.

Combina una taxonomía inicial amplia con temas dinámicos descubiertos por el
clustering. Ningún comentario se fuerza a encajar en una etiqueta: si no hay
coincidencia, la lista de aspectos queda vacía.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from app.services.analysis.lexicons import ASPECT_KEYWORDS, ASPECT_LABELS_ES

#: Palabras vacías que nunca son buenas palabras clave de un tema.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "al",
        "y",
        "o",
        "que",
        "en",
        "con",
        "por",
        "para",
        "es",
        "son",
        "ser",
        "está",
        "esta",
        "este",
        "esto",
        "eso",
        "esa",
        "ese",
        "muy",
        "más",
        "mas",
        "pero",
        "como",
        "cuando",
        "donde",
        "porque",
        "si",
        "no",
        "me",
        "te",
        "se",
        "lo",
        "le",
        "les",
        "mi",
        "tu",
        "su",
        "sus",
        "mis",
        "tus",
        "yo",
        "tú",
        "he",
        "ha",
        "han",
        "hay",
        "eres",
        "soy",
        "todo",
        "toda",
        "todos",
        "todas",
        "the",
        "and",
        "you",
        "your",
        "this",
        "that",
        "is",
        "are",
        "was",
        "were",
        "for",
        "with",
        "have",
        "has",
        "but",
        "not",
        "what",
        "when",
        "how",
        "why",
        "just",
        "like",
        "really",
        "very",
        "too",
        "also",
        "there",
        "their",
        "they",
        "it",
        "its",
        "of",
        "to",
        "in",
        "on",
        "at",
        "a",
        "an",
        "i",
        "im",
        "ive",
        "vídeo",
        "video",
        "vídeos",
        "videos",
        "canal",
        "channel",
        "gracias",
        "thanks",
        "hola",
        "hello",
        "enlace",
    }
)

_WORD_RE = re.compile(r"[a-záéíóúüñ][\w'’]{2,}", re.UNICODE)

#: Aspectos compilados a expresión regular para emparejar por palabra completa.
_ASPECT_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    aspect: [
        re.compile(kw if " " in kw else rf"\b{re.escape(kw)}\w{{0,3}}\b", re.IGNORECASE)
        for kw in keywords
    ]
    for aspect, keywords in ASPECT_KEYWORDS.items()
}


@dataclass(slots=True)
class AspectResult:
    aspects: list[str]
    keywords: list[str]


def extract_aspects(normalised_text: str) -> AspectResult:
    """Devuelve los aspectos de la taxonomía presentes y las palabras clave."""
    text = normalised_text or ""
    if not text:
        return AspectResult(aspects=[], keywords=[])

    found: list[str] = []
    for aspect, patterns in _ASPECT_PATTERNS.items():
        if any(pattern.search(text) for pattern in patterns):
            found.append(aspect)

    keywords = [w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS and len(w) > 3]
    return AspectResult(aspects=sorted(found), keywords=keywords[:20])


def aspect_label_es(aspect: str) -> str:
    """Etiqueta legible en español de un aspecto de la taxonomía."""
    return ASPECT_LABELS_ES.get(aspect, aspect.replace("_", " ").capitalize())


def top_keywords(keyword_lists: list[list[str]], limit: int = 6) -> list[str]:
    """Palabras clave más frecuentes de un conjunto de comentarios."""
    counter: Counter[str] = Counter()
    for keywords in keyword_lists:
        counter.update(set(keywords))
    return [word for word, _count in counter.most_common(limit)]


def distinctive_keywords(
    keyword_lists: list[list[str]],
    corpus_document_frequency: Counter[str],
    corpus_size: int,
    *,
    limit: int = 6,
    min_occurrences: int = 3,
) -> list[str]:
    """Palabras que caracterizan a este grupo frente al resto del canal.

    Una palabra frecuente en todo el canal («vídeo», «gracias») no distingue
    nada. Se pondera la frecuencia dentro del grupo por lo rara que es en el
    conjunto, de forma que salgan los términos realmente característicos.
    """
    if not keyword_lists or corpus_size <= 0:
        return []

    local: Counter[str] = Counter()
    for keywords in keyword_lists:
        local.update(set(keywords))

    group_size = len(keyword_lists)
    scored: list[tuple[float, str]] = []
    for word, count in local.items():
        if count < min_occurrences:
            continue
        local_rate = count / group_size
        global_rate = max(1, corpus_document_frequency.get(word, 1)) / corpus_size
        # Cociente de tasas: cuánto más habitual es la palabra aquí que en general.
        scored.append((local_rate / global_rate, word))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [word for _score, word in scored[:limit]]


def build_document_frequency(keyword_lists: list[list[str]]) -> Counter[str]:
    """Frecuencia de documento de cada palabra en toda la muestra."""
    counter: Counter[str] = Counter()
    for keywords in keyword_lists:
        counter.update(set(keywords))
    return counter


def dominant_aspect(aspect_lists: list[list[str]]) -> str | None:
    """Aspecto más frecuente de un conjunto de comentarios, si lo hay."""
    counter: Counter[str] = Counter()
    for aspects in aspect_lists:
        counter.update(set(aspects))
    if not counter:
        return None
    return counter.most_common(1)[0][0]


__all__ = [
    "AspectResult",
    "aspect_label_es",
    "build_document_frequency",
    "distinctive_keywords",
    "dominant_aspect",
    "extract_aspects",
    "top_keywords",
]
