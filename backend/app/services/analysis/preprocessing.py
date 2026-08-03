"""Etapa 2 del pipeline: limpieza y normalización de texto.

El objetivo es preparar el texto sin destruir su significado: los emojis se
conservan (aportan señal de sentimiento) y no se traduce nada, porque los
modelos usados son multilingües.
"""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from dataclasses import dataclass, field

from app.services.analysis.lexicons import LANGUAGE_CHAR_HINTS, LANGUAGE_MARKERS

_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_TIMESTAMP_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
_WHITESPACE_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[\w'’]+", re.UNICODE)
_REPEATED_CHAR_RE = re.compile(r"(.)\1{3,}")
_EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001f9ff"
    "\U0001fa00-\U0001faff"
    "\U00002600-\U000027bf"
    "\U0001f1e6-\U0001f1ff"
    "\U00002190-\U000021ff"
    "\U00002700-\U000027bf"
    "\U0000fe0f"
    "\U00002b00-\U00002bff"
    "]",
    flags=re.UNICODE,
)

#: Patrones que casi siempre indican spam o autopromoción.
_SPAM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(sub4sub|subs?\s*for\s*subs?|suscr[ií]bete a mi canal|visita mi canal)\b", re.I),
    re.compile(
        r"\b(free\s+(bitcoin|crypto|money|robux|vbucks)|ganar dinero (r[áa]pido|f[áa]cil))\b", re.I
    ),
    re.compile(r"(t\.me/|bit\.ly/|wa\.me/|whatsapp\s*\+?\d{6,})", re.I),
    re.compile(r"\b(telegram|onlyfans|casino|apuestas)\b.{0,30}(https?://|@\w+)", re.I),
)

#: Longitud mínima para considerar que un comentario tiene contenido analizable.
MIN_MEANINGFUL_CHARS = 3


@dataclass(slots=True)
class CleanedText:
    """Resultado de limpiar un comentario."""

    original: str
    text: str
    normalised: str
    language: str
    language_confidence: float
    emojis: list[str] = field(default_factory=list)
    has_url: bool = False
    is_spam: bool = False
    spam_reason: str | None = None
    word_count: int = 0
    fingerprint: str = ""
    is_empty: bool = False


def strip_html(text: str) -> str:
    """Elimina etiquetas HTML y decodifica entidades de forma segura.

    La API puede devolver `textDisplay` con `<br>` y `&amp;`. Se decodifica dos
    veces como máximo para cubrir el doble escapado, sin permitir que sobreviva
    ninguna etiqueta.
    """
    if not text:
        return ""
    decoded = html.unescape(text)
    # Segundo paso: algunos textos vienen con doble escapado (`&amp;lt;`).
    if "&" in decoded:
        decoded = html.unescape(decoded)
    without_tags = _TAG_RE.sub(" ", decoded)
    # Se vuelve a limpiar por si la decodificación reveló etiquetas nuevas.
    return _TAG_RE.sub(" ", without_tags)


def normalise_unicode(text: str) -> str:
    """Normaliza a NFKC y elimina caracteres de control."""
    normalised = unicodedata.normalize("NFKC", text)
    return "".join(
        ch for ch in normalised if ch == "\n" or not unicodedata.category(ch).startswith("C")
    )


def extract_emojis(text: str) -> list[str]:
    return _EMOJI_RE.findall(text)


def collapse_repeats(text: str) -> str:
    """`holaaaaaa` -> `holaaa`: conserva el énfasis sin romper el vocabulario."""
    return _REPEATED_CHAR_RE.sub(r"\1\1\1", text)


def detect_spam(text: str) -> tuple[bool, str | None]:
    """Detección de spam basada en patrones y en densidad de enlaces."""
    for pattern in _SPAM_PATTERNS:
        if pattern.search(text):
            return True, "patrón de autopromoción o estafa"
    urls = _URL_RE.findall(text)
    words = _WORD_RE.findall(text)
    if len(urls) >= 2 and len(words) < 25:
        return True, "exceso de enlaces"
    if len(urls) >= 1 and len(words) <= 3:
        return True, "sólo un enlace"
    return False, None


def detect_language(text: str) -> tuple[str, float]:
    """Detección de idioma ligera y determinista.

    No pretende sustituir a un detector estadístico: identifica los idiomas
    frecuentes en comentarios y devuelve `und` cuando no hay señal suficiente.
    """
    lowered = text.lower()
    words = set(_WORD_RE.findall(lowered))
    if not words:
        return "und", 0.0

    scores: dict[str, float] = {}
    for lang, markers in LANGUAGE_MARKERS.items():
        hits = len(words & markers)
        scores[lang] = hits / max(1, min(len(words), 20))

    for lang, chars in LANGUAGE_CHAR_HINTS.items():
        if any(ch in lowered for ch in chars):
            scores[lang] = scores.get(lang, 0.0) + 0.35

    best_lang = max(scores, key=lambda k: scores[k])
    best_score = scores[best_lang]
    if best_score < 0.12:
        return "und", round(best_score, 3)

    ordered = sorted(scores.values(), reverse=True)
    margin = ordered[0] - (ordered[1] if len(ordered) > 1 else 0.0)
    confidence = min(1.0, best_score + margin)
    return best_lang, round(confidence, 3)


def fingerprint(text: str) -> str:
    """Huella para detectar duplicados y casi-duplicados.

    Normaliza acentos, elimina puntuación y ordena las palabras, de modo que
    «Gran vídeo!!!» y «gran video» comparten huella.
    """
    lowered = text.lower()
    decomposed = unicodedata.normalize("NFKD", lowered)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    words = sorted(set(_WORD_RE.findall(stripped)))
    if not words:
        # Comentarios sólo con emojis: la huella son los propios emojis.
        words = sorted(set(extract_emojis(text)))
    return hashlib.sha1("|".join(words).encode(), usedforsecurity=False).hexdigest()[:20]


def clean_comment(raw_text: str) -> CleanedText:
    """Aplica el pipeline completo de limpieza a un comentario."""
    original = raw_text or ""
    text = strip_html(original)
    text = normalise_unicode(text)
    text = _TIMESTAMP_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()

    emojis = extract_emojis(text)
    has_url = bool(_URL_RE.search(text))
    is_spam, spam_reason = detect_spam(text)

    # El texto normalizado se usa para emparejar patrones y embeddings.
    normalised = collapse_repeats(text.lower())
    normalised = _URL_RE.sub(" [enlace] ", normalised)
    normalised = _WHITESPACE_RE.sub(" ", normalised).strip()

    words = _WORD_RE.findall(normalised)
    language, confidence = detect_language(text)

    return CleanedText(
        original=original,
        text=text,
        normalised=normalised,
        language=language,
        language_confidence=confidence,
        emojis=emojis,
        has_url=has_url,
        is_spam=is_spam,
        spam_reason=spam_reason,
        word_count=len(words),
        fingerprint=fingerprint(text),
        is_empty=len(text) < MIN_MEANINGFUL_CHARS and not emojis,
    )


#: Veces que puede repetirse una misma huella en toda la muestra antes de
#: considerarse copia-pega o brigading.
MAX_GLOBAL_REPEATS = 8


def mark_duplicates(
    cleaned: list[CleanedText],
    video_ids: list[str] | None = None,
    *,
    max_global_repeats: int = MAX_GLOBAL_REPEATS,
) -> list[bool]:
    """Marca los comentarios duplicados de la muestra.

    Un comentario se considera duplicado si:

    * la misma huella ya apareció **en el mismo vídeo** (copia-pega o el mismo
      mensaje recogido por dos estrategias de muestreo), o
    * la huella aparece más de `max_global_repeats` veces en toda la muestra,
      lo que indica copia-pega masivo.

    Repetir el mismo elogio corto («gran vídeo») en vídeos distintos **no** es
    un duplicado: es precisamente la señal de un patrón de audiencia, y
    descartarlo vaciaría el análisis.
    """
    ids = video_ids if video_ids is not None else [""] * len(cleaned)
    seen_per_video: set[tuple[str, str]] = set()
    global_counts: dict[str, int] = {}
    flags: list[bool] = []

    for item, video_id in zip(cleaned, ids, strict=True):
        key = (video_id, item.fingerprint)
        count = global_counts.get(item.fingerprint, 0) + 1
        global_counts[item.fingerprint] = count

        if key in seen_per_video or count > max_global_repeats:
            flags.append(True)
        else:
            seen_per_video.add(key)
            flags.append(False)
    return flags


__all__ = [
    "MAX_GLOBAL_REPEATS",
    "MIN_MEANINGFUL_CHARS",
    "CleanedText",
    "clean_comment",
    "collapse_repeats",
    "detect_language",
    "detect_spam",
    "extract_emojis",
    "fingerprint",
    "mark_duplicates",
    "normalise_unicode",
    "strip_html",
]
