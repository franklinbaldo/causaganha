"""Tests for the canonical IA ``x-archive-meta-*`` header encoder.

``causaganha.pipeline.ia_s3.meta_value`` is shared by stj_acordaos,
tjro_juris and datajud archive.py modules (do not reimplement — see
CLAUDE.md).
"""

from __future__ import annotations

from urllib.parse import unquote

from causaganha.pipeline.ia_s3 import meta_value


def test_ascii_value_passes_through_unchanged():
    assert meta_value("STJ Acordaos") == "STJ Acordaos"


def test_non_ascii_value_is_wrapped_in_uri_percent_encoding():
    value = "Espelhos de acórdãos — Superior Tribunal de Justiça (STJ)"
    encoded = meta_value(value)
    assert encoded.startswith("uri(")
    assert encoded.endswith(")")
    assert encoded.isascii()
    assert unquote(encoded[len("uri(") : -1]) == value


def test_empty_string_passes_through():
    assert meta_value("") == ""
