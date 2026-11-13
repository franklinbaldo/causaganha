"""The DataJud locator sidecar must derive from existing ZIP members."""

import gzip
import json
import zipfile

import pytest

from datajud.daily_pack import export_daily_locators


def test_locators_reference_actual_archive_members(tmp_path):
    cnj = "70726450920238220001"
    zip_path = tmp_path / "tjro_2026-11-13.zip"
    doc = {
        "numeroProcesso": cnj,
        "id": f"TJRO_G1_{cnj}",
        "grau": "G1",
        "dataHoraUltimaAtualizacao": "2026-11-13T12:30:00Z",
    }
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(f"{cnj}.json.gz", gzip.compress(json.dumps(doc).encode()))
    output = export_daily_locators(zip_path, "tjro")
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["numero_processo"] == cnj
    assert row["item_ia"] == "datajud-tjro"
    assert row["arquivo_zip"] == zip_path.name
    assert row["membro"] == f"{cnj}.json.gz"
    assert row["documento_id"] == f"TJRO_G1_{cnj}"


def test_no_implicit_identity_when_source_lacks_id(tmp_path):
    cnj = "70726450920238220001"
    zip_path = tmp_path / "tjro_2026-11-13.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            f"{cnj}.json",
            json.dumps({
                "numeroProcesso": cnj,
                "grau": "G1",
                "dataHoraUltimaAtualizacao": "2026-11-13T12:30:00Z",
            }),
        )
    with pytest.raises(ValueError, match="Incomplete DataJud source identity"):
        export_daily_locators(zip_path, "tjro")
