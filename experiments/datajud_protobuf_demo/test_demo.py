"""Lossless checks for schema gaps that were not covered by the original spike."""

from __future__ import annotations

import copy
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


@pytest.fixture(scope="module")
def codec(tmp_path_factory):
    generated = tmp_path_factory.mktemp("protobuf-generated")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"-I{ROOT / 'src/datajud/schema'}",
            f"-I{HERE}",
            f"--python_out={generated}",
            str(ROOT / "src/datajud/schema/processo.proto"),
            str(HERE / "demo.proto"),
        ],
        check=True,
    )
    sys.path.insert(0, str(generated))
    sys.path.insert(0, str(HERE))
    module = importlib.import_module("codec")
    yield module
    sys.path.remove(str(HERE))
    sys.path.remove(str(generated))


@pytest.mark.parametrize("compact", [False, True])
@pytest.mark.parametrize(
    "source",
    [
        {},
        {"classe": None, "assuntos": None, "movimentos": None},
        {"classe": {"codigo": 0, "nome": None, "future": {"x": True}}},
        {"sistema": {"codigo": -1}, "dataAjuizamento": "20260918080636"},
        {"movimentos": [{"codigo": 0, "dataHora": None, "complementosTabelados": None}]},
        {
            "movimentos": [
                {
                    "codigo": 1,
                    "dataHora": "x",
                    "orgaoJulgador": {"codigo": "7", "extra": 3},
                    "complementosTabelados": [{"valor": None, "unknown": 1}, {"valor": 2**80}],
                }
            ]
        },
        {"movimentos": [None, 3, "unknown shape"]},
        {
            "movimentos": [
                {"codigo": 1, "extra": [1, False, None]},
                {"codigo": 1, "extra": [1, False, None]},
            ]
        },
    ],
)
def test_schema_gaps_preserve_exact_json(codec, compact, source):
    doc = {
        "_index": "i",
        "_id": "same",
        "_score": None,
        "sort": [0, "tie"],
        "future": {"n": 2**90},
        "_source": source,
    }
    second = copy.deepcopy(doc)
    second["sort"] = [1, "another capture"]
    docs = [doc, second]
    templates, catalog = codec.make_catalog({"cnj": docs})
    payload = codec.encode("cnj", docs, compact, templates)
    recovered_cnj, recovered = codec.decode(payload, compact, codec.read_catalog(catalog))
    assert recovered_cnj == "cnj"
    assert len(recovered) == 2
    assert codec.json_bytes(recovered) == codec.json_bytes(docs)


def test_verifier_rejects_catalog_tampering(tmp_path):
    output = tmp_path / "demo"
    subprocess.run(
        [sys.executable, str(HERE / "run.py"), "--output", str(output), "--repeats", "1"],
        check=True,
    )
    report = json.loads((output / "results.json").read_bytes())
    assert report["manifest"]["captures"] == 94
    (output / "catalog.pb").write_bytes(b"tampered")
    result = subprocess.run(
        [sys.executable, str(HERE / "run.py"), "--output", str(output), "--verify-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Catalog hash mismatch" in result.stderr
