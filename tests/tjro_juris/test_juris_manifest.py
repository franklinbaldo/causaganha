"""Tests for tjro_juris.manifest — parse, serialization, roundtrip, counts."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tjro_juris.manifest import HEADER, ManifestFormatError, ManifestJuris, ManifestJurisEntry


if TYPE_CHECKING:
    from pathlib import Path


def test_load_local_missing_file_returns_empty_manifest(tmp_path: Path) -> None:
    m = ManifestJuris.load_local(tmp_path / "nope.csv")
    assert m.all_entries() == []


def test_load_local_missing_column_raises_manifest_format_error(tmp_path: Path) -> None:
    path = tmp_path / "tjro-juris-manifest.csv"
    path.write_text("mes_ano,ia_status,n_docs,updated_at\n2024-01,uploaded,10,\n", encoding="utf-8")

    with pytest.raises(ManifestFormatError, match="tipo"):
        ManifestJuris.load_local(path)


def test_load_local_non_numeric_n_docs_raises_manifest_format_error(tmp_path: Path) -> None:
    path = tmp_path / "tjro-juris-manifest.csv"
    path.write_text(f"{HEADER}\nACÓRDÃO,2024-01,uploaded,not-a-number,\n", encoding="utf-8")

    with pytest.raises(ManifestFormatError):
        ManifestJuris.load_local(path)


@pytest.mark.parametrize(
    "mes_ano",
    [
        "2024-01/../../secret-item",
        "2024-01/etc/passwd",
        "../../2024-01",
        "2024-1",
        "2024-13",
        "abcd-ef",
        "",
    ],
)
def test_load_text_rejects_malformed_mes_ano(mes_ano: str) -> None:
    """`mes_ano` is interpolated into a `read_parquet` URL by
    `causaganha.decisoes.published._juris_url` (issue #1610): `urllib.parse.quote`'s
    default `safe='/'` lets an embedded `/` (in particular `../`) survive into the
    resulting archive.org URL unescaped, redirecting the DuckDB fetch target outside
    the intended item. A manifest that cannot produce a well-formed `YYYY-MM` value
    must fail closed at parse time, before any URL is ever built from it.
    """
    text = f"{HEADER}\nACÓRDÃO,{mes_ano},uploaded,5,\n"

    with pytest.raises(ManifestFormatError, match="mes_ano"):
        ManifestJuris.load_text(text)


def test_load_text_accepts_well_formed_mes_ano() -> None:
    m = ManifestJuris.load_text(f"{HEADER}\nACÓRDÃO,2024-01,uploaded,5,\n")
    assert m.get("ACÓRDÃO", "2024-01") is not None


def test_save_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "tjro-juris-manifest.csv"
    m1 = ManifestJuris()
    m1.upsert(
        ManifestJurisEntry(tipo="ACÓRDÃO", mes_ano="2024-01", ia_status="uploaded", n_docs=10)
    )
    m1.upsert(ManifestJurisEntry(tipo="SENTENÇA", mes_ano="2024-01", n_docs=5))
    m1.save_local(path)

    m2 = ManifestJuris.load_local(path)
    e1 = m2.get("ACÓRDÃO", "2024-01")
    e2 = m2.get("SENTENÇA", "2024-01")
    assert e1 is not None
    assert e1.ia_status == "uploaded"
    assert e1.n_docs == 10
    assert e1.updated_at  # stamp survived the roundtrip
    assert e2 is not None
    assert e2.ia_status == ""
    assert e2.n_docs == 5


def test_roundtrip_preserves_a_comma_in_ia_status(tmp_path: Path) -> None:
    """save_local must escape commas, not just join fields with them.

    ia_status is normally a controlled value today, but the on-disk format
    contract must not silently corrupt any value it is asked to persist --
    the reader (csv.DictReader) already expects real CSV quoting, so the
    writer must produce it.
    """
    path = tmp_path / "tjro-juris-manifest.csv"
    m1 = ManifestJuris()
    m1.upsert(
        ManifestJurisEntry(
            tipo="ACÓRDÃO", mes_ano="2024-01", ia_status="erro, retry pending", n_docs=10
        )
    )
    m1.save_local(path)

    m2 = ManifestJuris.load_local(path)
    entry = m2.get("ACÓRDÃO", "2024-01")
    assert entry is not None
    assert entry.ia_status == "erro, retry pending"


def test_saved_csv_has_header_and_sorted_rows(tmp_path: Path) -> None:
    path = tmp_path / "m.csv"
    m = ManifestJuris()
    m.upsert(ManifestJurisEntry(tipo="VOTO", mes_ano="2024-02", n_docs=1))
    m.upsert(ManifestJurisEntry(tipo="ACÓRDÃO", mes_ano="2024-01", n_docs=2))
    m.save_local(path)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == HEADER
    assert lines[1].startswith("ACÓRDÃO,2024-01,")
    assert lines[2].startswith("VOTO,2024-02,")


def test_key_is_tipo_and_mes_ano_pair(tmp_path: Path) -> None:
    """Same month with different tipos must be two distinct entries."""
    m = ManifestJuris()
    m.upsert(ManifestJurisEntry(tipo="ACÓRDÃO", mes_ano="2024-01", n_docs=1))
    m.upsert(ManifestJurisEntry(tipo="VOTO", mes_ano="2024-01", n_docs=2))
    assert len(m.all_entries()) == 2
    assert m.get("ACÓRDÃO", "2024-01").n_docs == 1
    assert m.get("VOTO", "2024-01").n_docs == 2


def test_upsert_replaces_existing_and_stamps_updated_at() -> None:
    m = ManifestJuris()
    m.upsert(ManifestJurisEntry(tipo="ACÓRDÃO", mes_ano="2024-01", n_docs=1))
    m.upsert(ManifestJurisEntry(tipo="ACÓRDÃO", mes_ano="2024-01", ia_status="uploaded", n_docs=9))

    assert len(m.all_entries()) == 1
    entry = m.get("ACÓRDÃO", "2024-01")
    assert entry.n_docs == 9
    assert entry.ia_status == "uploaded"
    assert entry.updated_at


def test_pending_upload_excludes_uploaded() -> None:
    m = ManifestJuris()
    m.upsert(ManifestJurisEntry(tipo="ACÓRDÃO", mes_ano="2024-01", ia_status="uploaded"))
    m.upsert(ManifestJurisEntry(tipo="ACÓRDÃO", mes_ano="2024-02"))
    m.upsert(ManifestJurisEntry(tipo="VOTO", mes_ano="2024-01"))

    pending = m.pending_upload()
    assert sorted((e.tipo, e.mes_ano) for e in pending) == [
        ("ACÓRDÃO", "2024-02"),
        ("VOTO", "2024-01"),
    ]


def test_load_tolerates_missing_optional_columns(tmp_path: Path) -> None:
    """n_docs empty string must fall back to 0, not crash int()."""
    path = tmp_path / "m.csv"
    path.write_text(
        HEADER + "\nACÓRDÃO,2024-01,,,\n",
        encoding="utf-8",
    )
    m = ManifestJuris.load_local(path)
    entry = m.get("ACÓRDÃO", "2024-01")
    assert entry is not None
    assert entry.n_docs == 0
