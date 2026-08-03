"""Pruebas del parser de referencias de canal."""

from __future__ import annotations

import pytest
from app.core.errors import UnsupportedChannelReferenceError
from app.services.youtube.parser import (
    ReferenceKind,
    is_valid_channel_id,
    is_valid_video_id,
    parse_channel_reference,
)

VALID_ID = "UCX6OQ3DkcsbYNE6H8uQQuVA"


@pytest.mark.parametrize(
    ("raw", "kind", "value"),
    [
        (VALID_ID, ReferenceKind.CHANNEL_ID, VALID_ID),
        (f"https://www.youtube.com/channel/{VALID_ID}", ReferenceKind.CHANNEL_ID, VALID_ID),
        (f"http://youtube.com/channel/{VALID_ID}", ReferenceKind.CHANNEL_ID, VALID_ID),
        (f"https://m.youtube.com/channel/{VALID_ID}/videos", ReferenceKind.CHANNEL_ID, VALID_ID),
        ("@creador", ReferenceKind.HANDLE, "creador"),
        ("https://www.youtube.com/@creador", ReferenceKind.HANDLE, "creador"),
        ("youtube.com/@creador", ReferenceKind.HANDLE, "creador"),
        ("www.youtube.com/@creador/videos", ReferenceKind.HANDLE, "creador"),
        ("https://youtube.com/user/viejoUsuario", ReferenceKind.LEGACY_USER, "viejoUsuario"),
        (
            "https://youtube.com/c/NombrePersonalizado",
            ReferenceKind.LEGACY_CUSTOM,
            "NombrePersonalizado",
        ),
        ("https://youtube.com/NombreSuelto", ReferenceKind.LEGACY_CUSTOM, "NombreSuelto"),
        ("nombresuelto", ReferenceKind.HANDLE, "nombresuelto"),
    ],
)
def test_parse_valid_references(raw: str, kind: ReferenceKind, value: str) -> None:
    reference = parse_channel_reference(raw)
    assert reference.kind is kind
    assert reference.value == value


def test_parse_strips_whitespace_and_handles_at_sign() -> None:
    assert parse_channel_reference("  @Creador_1.x  ").value == "Creador_1.x"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "https://vimeo.com/@creador",
        "https://evil.example.com/@creador",
        "ftp://youtube.com/@creador",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/playlist?list=PL123",
        "https://www.youtube.com/results?search_query=algo",
        "@a",
        "https://www.youtube.com/channel/NOESUNID",
        "https://www.youtube.com/channel/",
    ],
)
def test_parse_invalid_references(raw: str) -> None:
    with pytest.raises(UnsupportedChannelReferenceError):
        parse_channel_reference(raw)


def test_parse_rejects_overlong_input() -> None:
    with pytest.raises(UnsupportedChannelReferenceError):
        parse_channel_reference("@" + "a" * 3000)


def test_error_messages_are_in_spanish() -> None:
    with pytest.raises(UnsupportedChannelReferenceError) as excinfo:
        parse_channel_reference("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert "canal" in excinfo.value.message.lower()


def test_ssrf_protection_rejects_non_youtube_hosts() -> None:
    """El parser nunca acepta un host arbitrario: evita SSRF."""
    for host in ("http://169.254.169.254/latest/meta-data", "https://localhost/@x"):
        with pytest.raises(UnsupportedChannelReferenceError):
            parse_channel_reference(host)


def test_channel_id_validation() -> None:
    assert is_valid_channel_id(VALID_ID)
    assert not is_valid_channel_id("UC123")
    assert not is_valid_channel_id("XCX6OQ3DkcsbYNE6H8uQQuVA")


def test_video_id_validation() -> None:
    assert is_valid_video_id("dQw4w9WgXcQ")
    assert not is_valid_video_id("corto")
    assert not is_valid_video_id("demasiado-largo-id")


def test_display_representation() -> None:
    assert parse_channel_reference("@creador").as_display() == "@creador"
    assert parse_channel_reference(VALID_ID).as_display() == VALID_ID
