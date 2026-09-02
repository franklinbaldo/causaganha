"""Tests for resolving official TCU bulk URLs from the published files manifest.

The fixture below is a verbatim excerpt of the official manifest TCU itself publishes at
https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/jurisprudencia-arquivos.csv
(observed 2026-09-02). Parsing this manifest is the non-fragile alternative to scraping the
portal's client-rendered HTML page.
"""

from __future__ import annotations

import pytest

from tcu_acordaos.catalog import ManifestEntry, parse_manifest, resolve_acordaos_url

_MANIFEST_FIXTURE = """\
"28/08/2026"
"BASE"|"ANO"|"TAMANHO"|"ARQUIVO"
"Acórdãos"|"2025"|"394.40 MB"|"https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/acordao-completo/acordao-completo-2025.csv"
"Acórdãos"|"2026"|"275.27 MB"|"https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/acordao-completo/acordao-completo-2026.csv"
"Acórdãos"|""|"54.85 MB"|"https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/acordao-completo/acordao-completo-resumo.csv"
"Súmulas"|""|"800.20 KB"|"https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/sumula/sumula.csv"
"""


def test_parse_manifest_skips_generation_date_and_header() -> None:
    entries = parse_manifest(_MANIFEST_FIXTURE)

    assert entries == [
        ManifestEntry(
            base="Acórdãos",
            ano="2025",
            tamanho="394.40 MB",
            url="https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/acordao-completo/acordao-completo-2025.csv",
        ),
        ManifestEntry(
            base="Acórdãos",
            ano="2026",
            tamanho="275.27 MB",
            url="https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/acordao-completo/acordao-completo-2026.csv",
        ),
        ManifestEntry(
            base="Acórdãos",
            ano="",
            tamanho="54.85 MB",
            url="https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/acordao-completo/acordao-completo-resumo.csv",
        ),
        ManifestEntry(
            base="Súmulas",
            ano="",
            tamanho="800.20 KB",
            url="https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/sumula/sumula.csv",
        ),
    ]


def test_resolve_acordaos_url_selects_the_requested_year() -> None:
    entries = parse_manifest(_MANIFEST_FIXTURE)

    url = resolve_acordaos_url(entries, year="2026")

    assert (
        url
        == "https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/acordao-completo/acordao-completo-2026.csv"
    )


def test_resolve_acordaos_url_ignores_other_bases() -> None:
    entries = parse_manifest(_MANIFEST_FIXTURE)

    with pytest.raises(ValueError, match="no official Acórdãos manifest entry for year 1900"):
        resolve_acordaos_url(entries, year="1900")


def test_resolve_acordaos_url_rejects_non_official_url() -> None:
    entries = [
        ManifestEntry(
            base="Acórdãos",
            ano="2026",
            tamanho="1 MB",
            url="https://example.org/acordao-completo-2026.csv",
        )
    ]

    with pytest.raises(ValueError, match="hosted on tcu.gov.br"):
        resolve_acordaos_url(entries, year="2026")


def test_resolve_acordaos_url_rejects_ambiguous_year() -> None:
    entries = [
        ManifestEntry(
            base="Acórdãos",
            ano="2026",
            tamanho="1 MB",
            url="https://sites.tcu.gov.br/a-2026.csv",
        ),
        ManifestEntry(
            base="Acórdãos",
            ano="2026",
            tamanho="1 MB",
            url="https://sites.tcu.gov.br/b-2026.csv",
        ),
    ]

    with pytest.raises(ValueError, match="multiple official Acórdãos manifest entries"):
        resolve_acordaos_url(entries, year="2026")


def test_parse_manifest_rejects_missing_header() -> None:
    with pytest.raises(ValueError, match="missing the expected header"):
        parse_manifest('"28/08/2026"\n"Acórdãos"|"2026"|"1 MB"|"https://sites.tcu.gov.br/x.csv"\n')


def test_parse_manifest_rejects_malformed_data_row() -> None:
    malformed = '"28/08/2026"\n"BASE"|"ANO"|"TAMANHO"|"ARQUIVO"\n"Acórdãos"|"2026"|"1 MB"\n'

    with pytest.raises(ValueError, match="row 3 has 3 fields; expected 4"):
        parse_manifest(malformed)
