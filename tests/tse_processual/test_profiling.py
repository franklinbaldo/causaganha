from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from tse_processual.profiling import relational_profile


def _zip_csv(path: Path, name: str, content: str) -> Path:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(name, content.encode())
    return path


def _resources(tmp_path: Path, *, orphan_decision: bool = False) -> dict[str, Path]:
    decision_key = "3" if orphan_decision else "2"
    return {
        "processos": _zip_csv(
            tmp_path / "processos.zip",
            "processos.csv",
            "SQ_PROCESSO;NR_PROCESSO;CLASSE\n"
            "1;0000000-00.0000.0.00.0000;A\n"
            "2;1111111-11.1111.1.11.1111;B\n",
        ),
        "assuntos": _zip_csv(
            tmp_path / "assuntos.zip",
            "assuntos.csv",
            "SQ_PROCESSO;NR_PROCESSO;ASSUNTO\n"
            "1;0000000-00.0000.0.00.0000;X\n"
            "1;0000000-00.0000.0.00.0000;Y\n"
            "2;1111111-11.1111.1.11.1111;Z\n",
        ),
        "decisoes": _zip_csv(
            tmp_path / "decisoes.zip",
            "decisoes.csv",
            "SQ_PROCESSO;NR_PROCESSO;DECISAO\n"
            f"1;0000000-00.0000.0.00.0000;A\n{decision_key};"
            f"{'2222222-22.2222.2.22.2222' if orphan_decision else '1111111-11.1111.1.11.1111'};B\n",
        ),
    }


def test_relational_profile_measures_exact_cardinality_and_child_joins(tmp_path: Path) -> None:
    report = relational_profile(_resources(tmp_path))

    assert report["identity_proven"] is False
    profiles = {profile["candidate"]: profile for profile in report["candidate_profiles"]}
    sq = profiles["SQ_PROCESSO"]

    assert sq["resources"]["processos"] == {
        "rows": 2,
        "null_rows": 0,
        "non_null_rows": 2,
        "distinct_values": 2,
        "duplicate_rows": 0,
        "cnj_shaped_rows": 0,
        "unique_when_present": True,
    }
    assert sq["resources"]["assuntos"]["duplicate_rows"] == 1
    assert sq["child_joins_to_processos"]["assuntos"]["orphan_distinct"] == 0
    assert sq["child_joins_to_processos"]["decisoes"]["distinct_coverage"] == 1.0
    assert sq["relational_shape_supported"] is True

    nr = profiles["NR_PROCESSO"]
    assert nr["resources"]["processos"]["cnj_shaped_rows"] == 2
    assert nr["relational_shape_supported"] is True


def test_relational_profile_reports_orphans_without_promoting_identity(tmp_path: Path) -> None:
    report = relational_profile(_resources(tmp_path, orphan_decision=True))
    profiles = {profile["candidate"]: profile for profile in report["candidate_profiles"]}

    sq = profiles["SQ_PROCESSO"]
    assert sq["child_joins_to_processos"]["decisoes"]["matched_processos_distinct"] == 1
    assert sq["child_joins_to_processos"]["decisoes"]["orphan_distinct"] == 1
    assert sq["child_joins_to_processos"]["decisoes"]["distinct_coverage"] == 0.5
    assert sq["relational_shape_supported"] is False
    assert sq["identity_proven"] is False


def test_relational_profile_requires_named_processual_resources(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing required resources"):
        relational_profile({"processos": tmp_path / "processos.zip"})
