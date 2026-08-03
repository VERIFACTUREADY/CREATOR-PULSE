"""Pruebas de limpieza y normalización de texto."""

from __future__ import annotations

import pytest
from app.services.analysis.preprocessing import (
    CleanedText,
    clean_comment,
    detect_language,
    detect_spam,
    extract_emojis,
    fingerprint,
    mark_duplicates,
    normalise_unicode,
    strip_html,
)


def test_strip_html_removes_tags_and_decodes_entities() -> None:
    raw = "Hola<br>mundo &amp; &lt;b&gt;negrita&lt;/b&gt;"
    result = strip_html(raw)
    assert "<" not in result
    assert ">" not in result
    assert "&amp;" not in result
    assert "negrita" in result


def test_strip_html_handles_double_escaped_tags() -> None:
    """Una entidad doblemente escapada no debe dejar una etiqueta viva."""
    assert "<script>" not in strip_html("&amp;lt;script&amp;gt;alert(1)&amp;lt;/script&amp;gt;")


def test_strip_html_on_empty_input() -> None:
    assert strip_html("") == ""


def test_normalise_unicode_removes_control_characters() -> None:
    assert "\x00" not in normalise_unicode("hola\x00mundo")


def test_clean_comment_preserves_meaning_and_emojis() -> None:
    cleaned = clean_comment("Me <b>encanta</b> este vídeo 😍😍")
    assert "encanta" in cleaned.text
    assert "😍" in cleaned.emojis
    assert cleaned.word_count >= 3


def test_clean_comment_strips_timestamps() -> None:
    cleaned = clean_comment("En el 12:35 se ve el fallo")
    assert "12:35" not in cleaned.text


def test_clean_comment_collapses_repeated_characters() -> None:
    assert "aaaaaaa" not in clean_comment("holaaaaaaaa").normalised


def test_clean_comment_marks_emoji_only_as_non_empty() -> None:
    cleaned = clean_comment("🔥🔥🔥")
    assert not cleaned.is_empty
    assert len(cleaned.emojis) == 3


def test_clean_comment_marks_blank_as_empty() -> None:
    assert clean_comment("  ").is_empty


@pytest.mark.parametrize(
    "text",
    [
        "SUSCRÍBETE A MI CANAL y te devuelvo el sub",
        "sub4sub ahora",
        "Gana dinero rápido en t.me/oferta",
        "Free bitcoin here",
        "https://a.example https://b.example mira esto",
    ],
)
def test_detect_spam_positive(text: str) -> None:
    is_spam, reason = detect_spam(text)
    assert is_spam
    assert reason


@pytest.mark.parametrize(
    "text",
    [
        "Gran vídeo, gracias por explicarlo",
        "El enlace del vídeo anterior me ayudó mucho a entender el tema completo",
    ],
)
def test_detect_spam_negative(text: str) -> None:
    assert not detect_spam(text)[0]


def test_detect_language_spanish() -> None:
    lang, confidence = detect_language("Me encanta el vídeo, muchas gracias por la explicación")
    assert lang == "es"
    assert confidence > 0


def test_detect_language_english() -> None:
    lang, _ = detect_language("This is the best video that you have made for this channel")
    assert lang == "en"


def test_detect_language_unknown_for_short_text() -> None:
    lang, _ = detect_language("ok")
    assert lang == "und"


def test_detect_language_never_crashes_on_empty() -> None:
    assert detect_language("") == ("und", 0.0)


def test_fingerprint_ignores_case_accents_and_punctuation() -> None:
    assert fingerprint("¡Gran vídeo!") == fingerprint("gran video")
    assert fingerprint("Gran vídeo") != fingerprint("Mal vídeo")


def test_fingerprint_handles_emoji_only_comments() -> None:
    assert fingerprint("🔥🔥") == fingerprint("🔥")


def test_extract_emojis() -> None:
    assert extract_emojis("hola 😂 mundo 🔥") == ["😂", "🔥"]


def _cleaned(*texts: str) -> list[CleanedText]:
    return [clean_comment(t) for t in texts]


def test_mark_duplicates_flags_repeats_within_same_video() -> None:
    cleaned = _cleaned("Gran vídeo", "gran video", "Otro comentario")
    flags = mark_duplicates(cleaned, ["v1", "v1", "v1"])
    assert flags == [False, True, False]


def test_mark_duplicates_keeps_same_text_across_different_videos() -> None:
    """Repetir un elogio en vídeos distintos es señal, no un duplicado."""
    cleaned = _cleaned("Gran vídeo", "Gran vídeo", "Gran vídeo")
    flags = mark_duplicates(cleaned, ["v1", "v2", "v3"])
    assert flags == [False, False, False]


def test_mark_duplicates_flags_mass_copypaste() -> None:
    cleaned = _cleaned(*["Gran vídeo"] * 12)
    flags = mark_duplicates(cleaned, [f"v{i}" for i in range(12)], max_global_repeats=8)
    assert flags[:8] == [False] * 8
    assert all(flags[8:])


def test_mark_duplicates_without_video_ids() -> None:
    flags = mark_duplicates(_cleaned("a b c", "a b c"))
    assert flags == [False, True]


def test_unicode_comment_survives_cleaning() -> None:
    cleaned = clean_comment("日本語のコメントです")
    assert cleaned.text
    assert not cleaned.is_empty
