"""Tests for Phase 0.4 NDJSON input validator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from causaganha.consolidate.ndjson_validator import validate_ndjson_sample


def _write_ndjson(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")


class TestNDJSONValidator:
    def test_valid_records_pass(self, tmp_path: Path) -> None:
        records = [
            {
                "data_disponibilizacao": "2026-06-01",
                "numero_processo": "00012345678901234567",
                "tipoComunicacao": "Intimação",
                "siglaTribunal": "TJRO",
                "texto": "foo",
            }
        ] * 50
        _write_ndjson(tmp_path / "tjro.ndjson", records)
        result = validate_ndjson_sample(tmp_path)
        assert result.passed, result.errors

    def test_empty_dir_warns(self, tmp_path: Path) -> None:
        result = validate_ndjson_sample(tmp_path)
        assert result.passed
        assert any("No *.ndjson" in w for w in result.warnings)

    def test_missing_critical_field_blocks(self, tmp_path: Path) -> None:
        records = [
            {
                "numero_processo": "00012345678901234567",
                "tipoComunicacao": "Intimação",
            }
        ] * 50
        _write_ndjson(tmp_path / "tjro.ndjson", records)
        result = validate_ndjson_sample(tmp_path)
        assert not result.passed
        assert any("data_disponibilizacao" in e for e in result.errors)

    def test_accepts_camelcase_variant(self, tmp_path: Path) -> None:
        records = [
            {
                "dataDisponibilizacao": "2026-06-01",
                "numeroProcesso": "00012345678901234567",
                "tipoComunicacao": "Intimação",
            }
        ] * 50
        _write_ndjson(tmp_path / "tjro.ndjson", records)
        result = validate_ndjson_sample(tmp_path)
        assert result.passed, result.errors

    def test_partial_missing_within_threshold_passes(self, tmp_path: Path) -> None:
        good = {
            "data_disponibilizacao": "2026-06-01",
            "numero_processo": "00012345678901234567",
            "tipoComunicacao": "Intimação",
        }
        bad = {"other_field": "x"}
        records = [good] * 93 + [bad] * 7
        _write_ndjson(tmp_path / "tjro.ndjson", records)
        result = validate_ndjson_sample(tmp_path, sample_size=100)
        assert result.passed, result.errors

    def test_above_threshold_blocks(self, tmp_path: Path) -> None:
        good = {
            "data_disponibilizacao": "2026-06-01",
            "numero_processo": "00012345678901234567",
            "tipoComunicacao": "Intimação",
        }
        bad = {"numero_processo": "x", "tipoComunicacao": "y"}
        records = [good] * 85 + [bad] * 15
        _write_ndjson(tmp_path / "tjro.ndjson", records)
        result = validate_ndjson_sample(tmp_path, sample_size=100)
        assert not result.passed
        assert any("data_disponibilizacao" in e for e in result.errors)

    def test_skips_blank_lines(self, tmp_path: Path) -> None:
        content = "\n".join(
            [
                json.dumps(
                    {
                        "data_disponibilizacao": "2026-06-01",
                        "numero_processo": "x",
                        "tipoComunicacao": "y",
                    }
                ),
                "",
                "",
                json.dumps(
                    {
                        "data_disponibilizacao": "2026-06-01",
                        "numero_processo": "x",
                        "tipoComunicacao": "y",
                    }
                ),
            ]
        )
        (tmp_path / "tjro.ndjson").write_text(content, encoding="utf-8")
        result = validate_ndjson_sample(tmp_path)
        assert result.passed, result.errors
