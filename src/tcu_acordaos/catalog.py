"""Resolve official TCU bulk CSV URLs from TCU's own published files manifest.

The jurisprudência portal page is rendered client-side (its download links are Vue
templates such as ``{{acordao.arquivo}}``), so scraping the HTML is fragile. TCU instead
publishes a stable, machine-readable manifest of every bulk file it offers:
https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/jurisprudencia-arquivos.csv
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Iterable

from tcu_acordaos.acquisition import validate_official_url

_EXPECTED_HEADER = ("BASE", "ANO", "TAMANHO", "ARQUIVO")
_ACORDAOS_BASE = "Acórdãos"


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    """One row of the official TCU files manifest."""

    base: str
    ano: str
    tamanho: str
    url: str


def parse_manifest(text: str) -> list[ManifestEntry]:
    """Parse the official ``BASE|ANO|TAMANHO|ARQUIVO`` manifest.

    The first line is a bare generation date with no delimiter, followed by a pipe-delimited
    header and one row per published file.
    """
    lines = text.splitlines()
    if len(lines) < 2:
        msg = "TCU files manifest is missing the expected header"
        raise ValueError(msg)

    reader = csv.reader(lines[1:], delimiter="|", quotechar='"')
    rows = list(reader)
    if not rows or tuple(rows[0]) != _EXPECTED_HEADER:
        msg = "TCU files manifest is missing the expected header"
        raise ValueError(msg)

    entries: list[ManifestEntry] = []
    for line_number, row in enumerate(rows[1:], start=3):
        if len(row) != len(_EXPECTED_HEADER):
            msg = f"TCU files manifest row {line_number} has {len(row)} fields; expected 4"
            raise ValueError(msg)
        entries.append(ManifestEntry(base=row[0], ano=row[1], tamanho=row[2], url=row[3]))
    return entries


def resolve_acordaos_url(entries: Iterable[ManifestEntry], *, year: str) -> str:
    """Return the official Acórdãos bulk CSV URL for ``year``, validated as tcu.gov.br."""
    matches = [entry for entry in entries if entry.base == _ACORDAOS_BASE and entry.ano == year]
    if not matches:
        msg = f"no official Acórdãos manifest entry for year {year}"
        raise ValueError(msg)
    if len(matches) > 1:
        msg = f"multiple official Acórdãos manifest entries for year {year}"
        raise ValueError(msg)

    url = matches[0].url
    validate_official_url(url)
    return url
