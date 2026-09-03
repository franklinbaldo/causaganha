from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from tse_processual.inspection import (
    InvalidProcessualArchiveError,
    common_process_keys,
    inspect_zip,
    inspection_report,
    write_inspection_report,
)


def _zip_csv(path: Path, name: str, content: str, *, encoding: str = "utf-8") -> Path:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(name, content.encode(encoding))
    return path


def test_inspect_zip_observes_header_generation_metadata_and_delimiter(tmp_path: Path) -> None:
    path = _zip_csv(
        tmp_path / "processos.zip",
        "processo_eleitoral_2026.csv",
        "DT_GERACAO;HH_GERACAO;SQ_PROCESSO;NR_PROCESSO;DS_CLASSE\n"
        "28/08/2026;10:00:00;1;00000000000000000001;Classe A\n"
        "28/08/2026;10:00:00;2;00000000000000000002;Classe B\n",
    )

    result = inspect_zip(path)

    assert result.member == "processo_eleitoral_2026.csv"
    assert result.encoding == "utf-8-sig"
    assert result.delimiter == ";"
    assert result.columns == ("DT_GERACAO", "HH_GERACAO", "SQ_PROCESSO", "NR_PROCESSO", "DS_CLASSE")
    assert result.sampled_rows == 2
    assert result.generation_date_column == "DT_GERACAO"
    assert result.generation_date_values == ("28/08/2026",)
    assert result.generation_time_values == ("10:00:00",)


def test_inspect_zip_accepts_latin1_tse_text(tmp_path: Path) -> None:
    path = _zip_csv(
        tmp_path / "decisoes.zip",
        "decisoes.csv",
        "DT_GERACAO;SQ_PROCESSO;DS_DECISAO\n28/08/2026;1;PROCEDÊNCIA\n",
        encoding="latin-1",
    )

    result = inspect_zip(path)

    assert result.encoding == "latin-1"
    assert result.columns[-1] == "DS_DECISAO"


def test_common_process_keys_reports_candidates_without_claiming_identity(tmp_path: Path) -> None:
    processos = inspect_zip(
        _zip_csv(tmp_path / "p.zip", "p.csv", "SQ_PROCESSO;NR_PROCESSO;CLASSE\n1;123;A\n")
    )
    assuntos = inspect_zip(
        _zip_csv(
            tmp_path / "a.zip",
            "a.csv",
            "SQ_PROCESSO;NR_PROCESSO;ASSUNTO\n1;123;X\n",
        )
    )
    decisoes = inspect_zip(
        _zip_csv(
            tmp_path / "d.zip",
            "d.csv",
            "SQ_PROCESSO;NR_PROCESSO;DECISAO\n1;123;Y\n",
        )
    )

    assert common_process_keys((processos, assuntos, decisoes)) == ("SQ_PROCESSO", "NR_PROCESSO")
    report = inspection_report((tmp_path / "p.zip", tmp_path / "a.zip", tmp_path / "d.zip"))
    assert report["identity_proven"] is False
    assert report["common_process_key_candidates"] == ["SQ_PROCESSO", "NR_PROCESSO"]


def test_write_inspection_report_is_machine_readable(tmp_path: Path) -> None:
    source = _zip_csv(tmp_path / "p.zip", "p.csv", "SQ_PROCESSO;DT_GERACAO\n1;28/08/2026\n")
    destination = tmp_path / "evidence" / "report.json"

    write_inspection_report((source,), destination)

    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["resources"][0]["archive"] == "p.zip"
    assert payload["identity_proven"] is False


def test_inspect_zip_rejects_ambiguous_archive(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("one.csv", "A\n1\n")
        archive.writestr("two.csv", "A\n2\n")

    with pytest.raises(InvalidProcessualArchiveError, match="exactly one CSV"):
        inspect_zip(path)


def test_inspect_zip_requires_positive_sample_size(tmp_path: Path) -> None:
    path = _zip_csv(tmp_path / "p.zip", "p.csv", "A\n1\n")

    with pytest.raises(ValueError, match="sample_rows"):
        inspect_zip(path, sample_rows=0)
