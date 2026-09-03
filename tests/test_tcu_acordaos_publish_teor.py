"""Tests for the pure report-assembly logic of the #1022 TCU publish script.

Only ``build_evidence`` is unit-tested here: it is the one part of
``scripts/tcu_acordaos_publish_teor.py`` with no network I/O. The rest of the script performs
a real upload/read-back against Internet Archive and is run manually, once per publication,
to produce ``docs/data/tcu-acordaos-publish-proof.json``.
"""

from __future__ import annotations

from pathlib import Path

from scripts.tcu_acordaos_publish_teor import build_evidence
from tcu_acordaos.publish import PublicationProof


def _proof(**overrides: object) -> PublicationProof:
    fields = {
        "url": "https://archive.org/download/tcu-acordaos-2017-2026/tcu-acordaos.parquet",
        "size_bytes": 1234,
        "sha256": "a" * 64,
        "record_count": 10,
        "checksum_matches_local": True,
        "schema_ok": True,
        "count_matches_local": True,
    }
    fields.update(overrides)
    return PublicationProof(**fields)


def test_build_evidence_reports_published_when_upload_and_proof_succeed() -> None:
    evidence = build_evidence(
        parquet_path=Path("data/tcu/tcu-acordaos-2026.parquet"),
        uploaded=True,
        proof=_proof(),
    )

    assert evidence["item_id"] == "tcu-acordaos-2017-2026"
    assert evidence["upload_succeeded"] is True
    assert evidence["published"] is True
    assert evidence["read_back"]["checksum_matches_local"] is True


def test_build_evidence_never_published_when_upload_failed_even_if_proof_looks_ok() -> None:
    evidence = build_evidence(
        parquet_path=Path("data/tcu/tcu-acordaos-2026.parquet"),
        uploaded=False,
        proof=_proof(),
    )

    assert evidence["upload_succeeded"] is False
    assert evidence["published"] is False


def test_build_evidence_never_published_when_readback_proof_fails() -> None:
    evidence = build_evidence(
        parquet_path=Path("data/tcu/tcu-acordaos-2026.parquet"),
        uploaded=True,
        proof=_proof(checksum_matches_local=False),
    )

    assert evidence["published"] is False
    assert evidence["read_back"]["checksum_matches_local"] is False
