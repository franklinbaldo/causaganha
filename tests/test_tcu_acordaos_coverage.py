"""Tests for measuring the cost of TCU Acórdãos historical bulk expansion.

#984 requires measuring size/cost of expanding beyond a single proven year before any
historical backfill is scheduled. These tests use a fixture manifest excerpt (not live
network) covering a resumo file (no year), an ambiguous non-Acórdãos base, and three real
Acórdãos years, mirroring the shapes observed in the official manifest on 2026-09-02.
"""

from __future__ import annotations

import pytest

from tcu_acordaos.catalog import ManifestEntry
from tcu_acordaos.coverage import (
    parse_size_to_bytes,
    total_acordaos_size_bytes,
    years_available,
)

_ENTRIES = [
    ManifestEntry(base="Acórdãos", ano="1992", tamanho="15.07 MB", url="https://tcu.gov.br/1992.csv"),
    ManifestEntry(base="Acórdãos", ano="2026", tamanho="275.27 MB", url="https://tcu.gov.br/2026.csv"),
    ManifestEntry(base="Acórdãos", ano="", tamanho="54.85 MB", url="https://tcu.gov.br/resumo.csv"),
    ManifestEntry(base="Súmulas", ano="", tamanho="800.20 KB", url="https://tcu.gov.br/sumula.csv"),
]


@pytest.mark.parametrize(
    ("tamanho", "expected_bytes"),
    [
        ("800.20 KB", round(800.20 * 1024)),
        ("15.07 MB", round(15.07 * 1024**2)),
        ("1.50 GB", round(1.50 * 1024**3)),
        ("0 KB", 0),
    ],
)
def test_parse_size_to_bytes_handles_documented_units(tamanho: str, expected_bytes: int) -> None:
    assert parse_size_to_bytes(tamanho) == expected_bytes


def test_parse_size_to_bytes_rejects_unrecognized_unit() -> None:
    with pytest.raises(ValueError, match="unrecognized TCU manifest size"):
        parse_size_to_bytes("15.07 TB")


def test_years_available_excludes_resumo_and_other_bases() -> None:
    assert years_available(_ENTRIES) == ["1992", "2026"]


def test_total_acordaos_size_bytes_excludes_resumo_and_other_bases() -> None:
    expected = round(15.07 * 1024**2) + round(275.27 * 1024**2)

    assert total_acordaos_size_bytes(_ENTRIES) == expected
