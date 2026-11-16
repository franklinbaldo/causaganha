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
            json.dumps(
                {
                    "numeroProcesso": cnj,
                    "grau": "G1",
                    "dataHoraUltimaAtualizacao": "2026-11-13T12:30:00Z",
                }
            ),
        )
    with pytest.raises(ValueError, match="Incomplete DataJud source identity"):
        export_daily_locators(zip_path, "tjro")


def test_locator_offsets_point_at_the_member(tmp_path):
    import gzip
    import json
    import zipfile

    from datajud.daily_pack import export_daily_locators

    zip_path = tmp_path / "tjro_2026-11-15T153820Z.zip"
    docs = {
        f"000000{i}0220248220001": {
            "_id": f"TJRO_7_G1_1_000000{i}0220248220001",
            "numeroProcesso": f"000000{i}0220248220001",
            "grau": "G1",
            "dataHoraUltimaAtualizacao": "2026-11-15T10:00:00Z",
            "payload": "x" * (100 * i),
        }
        for i in range(1, 4)
    }
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for cnj, doc in docs.items():
            zf.writestr(f"{cnj}.json.gz", gzip.compress(json.dumps(doc).encode()))

    rows = [
        json.loads(line)
        for line in export_daily_locators(zip_path, "tjro").read_text().splitlines()
    ]
    raw = zip_path.read_bytes()
    for row in rows:
        offset = int(row["offset_cabecalho"])
        assert raw[offset : offset + 4] == b"PK\x03\x04"
        name_len = int.from_bytes(raw[offset + 26 : offset + 28], "little")
        extra_len = int.from_bytes(raw[offset + 28 : offset + 30], "little")
        assert raw[offset + 30 : offset + 30 + name_len].decode() == row["membro"]
        start = offset + 30 + name_len + extra_len
        data = raw[start : start + int(row["tamanho_comprimido"])]
        import zlib

        doc = json.loads(gzip.decompress(zlib.decompress(data, -15)))
        assert doc["numeroProcesso"] == row["numero_processo"]
