"""Published decision-dataset discovery is manifest-driven and deterministic."""

from __future__ import annotations

import json

import pytest

from causaganha.decisoes.published import (
    IndiceProcessualUnavailableError,
    PublishedDecisionDataset,
    STJ_PARQUET_URL,
    TCU_PARQUET_URL,
    discover_published_decision_datasets,
    discover_published_juris_datasets,
    discover_published_tcu_dataset,
    resolve_juris_urls_for_cnj,
    unpublished_fontes,
)
from causaganha.processos.query_plan_fixtures import (
    CNJ_ALL,
    CNJ_DJEN_ONLY,
    CNJ_UNKNOWN,
    build_fixtures,
)


MANIFEST = """tipo,mes_ano,ia_status,n_docs,updated_at
ACÓRDÃO,2026-06,uploaded,5,2026-07-01T00:00:00+00:00
DECISÃO / MONOCRÁTICA,2026-07,uploaded,2,2026-08-01T00:00:00+00:00
EMENTA,2026-08,,10,2026-09-01T00:00:00+00:00
VOTO,2026-09,uploaded,0,2026-09-02T00:00:00+00:00
"""


def test_juris_discovery_only_exposes_uploaded_nonempty_windows() -> None:
    datasets = discover_published_juris_datasets(MANIFEST)

    assert [(item.periodo, item.tipo, item.registros) for item in datasets] == [
        ("2026-06", "ACÓRDÃO", 5),
        ("2026-07", "DECISÃO / MONOCRÁTICA", 2),
    ]
    assert datasets[0].url == (
        "https://archive.org/download/tjro-juris-2026/2026-06-AC%C3%93RD%C3%83O.parquet"
    )
    assert datasets[1].url.endswith("/2026-07-DECIS%C3%83O___MONOCR%C3%81TICA.parquet")


def test_combined_discovery_keeps_stj_as_distinct_source() -> None:
    datasets = discover_published_decision_datasets(MANIFEST)

    assert [item.fonte for item in datasets] == ["juris", "juris", "stj"]
    assert datasets[-1].url == STJ_PARQUET_URL
    assert datasets[-1].periodo is None


def test_unpublished_fontes_names_tcu_until_publication_is_proven() -> None:
    """TCU is recognized by decisoes_buscar's schema but has no published
    dataset yet (#1022); the authority must say so without a live fetch (#1036)."""
    assert unpublished_fontes() == frozenset({"tcu"})


def _write_evidence(path, **overrides: object) -> None:
    payload: dict[str, object] = {
        "item_id": "tcu-acordaos-2017-2026",
        "remote_name": "tcu-acordaos.parquet",
        "local_parquet": "/tmp/tcu-acordaos.parquet",
        "upload_succeeded": True,
        "read_back": {
            "url": TCU_PARQUET_URL,
            "size_bytes": 123,
            "sha256": "deadbeef",
            "record_count": 10,
            "checksum_matches_local": True,
            "schema_ok": True,
            "count_matches_local": True,
        },
        "published": True,
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_discover_published_tcu_dataset_reads_proven_evidence(tmp_path) -> None:
    """Once scripts/tcu_acordaos_publish_teor.py records published=true for the
    real TCU_PARQUET_URL (#1022), discovery must expose it as a real dataset."""
    evidence_path = tmp_path / "tcu-acordaos-publish-proof.json"
    _write_evidence(evidence_path)

    dataset = discover_published_tcu_dataset(evidence_path)

    assert dataset == PublishedDecisionDataset(fonte="tcu", url=TCU_PARQUET_URL, tipo="acordao")


def test_discover_published_tcu_dataset_missing_evidence_file_returns_none(tmp_path) -> None:
    assert discover_published_tcu_dataset(tmp_path / "missing.json") is None


def test_discover_published_tcu_dataset_unpublished_evidence_returns_none(tmp_path) -> None:
    """A failed upload or a failed read-back proof must never be treated as published."""
    evidence_path = tmp_path / "tcu-acordaos-publish-proof.json"
    _write_evidence(evidence_path, published=False)

    assert discover_published_tcu_dataset(evidence_path) is None


def test_discover_published_tcu_dataset_url_mismatch_returns_none(tmp_path) -> None:
    """Evidence proving a different/stale URL must not be mistaken for TCU_PARQUET_URL."""
    evidence_path = tmp_path / "tcu-acordaos-publish-proof.json"
    _write_evidence(
        evidence_path,
        read_back={"url": "https://archive.org/download/tcu-acordaos-stale/old.parquet"},
    )

    assert discover_published_tcu_dataset(evidence_path) is None


def test_discover_published_tcu_dataset_malformed_json_returns_none(tmp_path) -> None:
    evidence_path = tmp_path / "tcu-acordaos-publish-proof.json"
    evidence_path.write_text("not json", encoding="utf-8")

    assert discover_published_tcu_dataset(evidence_path) is None


def test_resolve_juris_urls_for_cnj_returns_the_exact_indexed_file(tmp_path) -> None:
    """decisoes_buscar's CNJ lookup must reuse the same thin index
    processo_consultar already relies on instead of scanning every published
    JURIS partition (the production manifest already has 1000+ of them)."""
    fixtures = build_fixtures(tmp_path)

    urls = resolve_juris_urls_for_cnj(CNJ_ALL, indice_url=str(fixtures["indice"]))

    assert urls == [str(fixtures["juris"])]


def test_resolve_juris_urls_for_cnj_absent_cnj_is_a_real_empty_result(tmp_path) -> None:
    """A CNJ with no juris row in the index is a provable absence — the same
    authority processo_consultar already answers "no juris document" from —
    not a signal to fall back to scanning everything."""
    fixtures = build_fixtures(tmp_path)

    assert resolve_juris_urls_for_cnj(CNJ_DJEN_ONLY, indice_url=str(fixtures["indice"])) == []
    assert resolve_juris_urls_for_cnj(CNJ_UNKNOWN, indice_url=str(fixtures["indice"])) == []


def test_resolve_juris_urls_for_cnj_unreadable_index_raises_distinct_error(tmp_path) -> None:
    """An infra failure reading the index itself must never be mistaken for a
    proven absence — callers need to tell the two apart to decide whether to
    fall back to an unbounded scan."""
    missing_index = tmp_path / "missing-indice_processual.parquet"

    with pytest.raises(IndiceProcessualUnavailableError):
        resolve_juris_urls_for_cnj(CNJ_ALL, indice_url=str(missing_index))
