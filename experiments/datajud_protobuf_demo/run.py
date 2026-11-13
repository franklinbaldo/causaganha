# /// script
# requires-python = ">=3.12"
# dependencies = ["protobuf==7.36.2", "grpcio-tools==1.85.1", "zstandard==0.25.0"]
# ///
"""Compile, encode and independently recover real DataJud hits using Protobuf."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_collections(scope: str) -> tuple[dict, dict]:
    """Keep every capture by default, including repeated index/id and envelope differences."""
    fixtures = ROOT / "fixtures" / "datajud_sample"
    hashes = {}
    raw = fixtures / "inventario_datajud_bruto.json"
    pairs = fixtures / "pares_multindice_comprovados.json"
    for path in (raw, pairs):
        hashes[str(path.relative_to(ROOT))] = sha256(path.read_bytes())
    inventory = json.loads(raw.read_bytes())
    hits = [hit for docs in inventory["amostras_tribunais"].values() for hit in docs]
    hits += inventory.get("casos_multigrau", []) + inventory.get("casos_superiores", [])
    for pair in json.loads(pairs.read_bytes()):
        hits += pair["documentos_origem"] + pair["documentos_superior"]
    collections = {}
    for hit in hits:
        cnj = hit["_source"]["numeroProcesso"]
        docs = collections.setdefault(cnj, [])
        if scope == "legacy-68" and any(
            (d.get("_index"), d.get("_id")) == (hit.get("_index"), hit.get("_id")) for d in docs
        ):
            continue
        docs.append(hit)
    assert collections and sum(map(len, collections.values())) >= 68, (
        "Real corpus is missing or unexpectedly small"
    )
    return collections, hashes


def measure(function, repeats: int) -> dict:
    for _ in range(3):
        function()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        function()
        samples.append((time.perf_counter_ns() - start) / 1e6)
    ordered = sorted(samples)
    return {
        "median_ms": statistics.median(samples),
        "p95_ms": ordered[int(0.95 * (len(ordered) - 1))],
    }


def recover(name: str, payload: bytes, templates: list[dict]) -> tuple[str, list[dict]]:
    import codec

    if name.startswith("protobuf"):
        return codec.decode(payload, name.endswith("templates"), templates)
    obj = json.loads(payload)
    if name == "json":
        return obj["cnj"], obj["docs"]
    return obj["cnj"], [
        codec.restore(codec.unproject_dict(record["document"], True, templates), record["residual"])
        for record in obj["records"]
    ]


def build(output: Path, scope: str, repeats: int) -> None:
    import codec
    import demo_pb2
    import zstandard as zstd

    collections, hashes = load_collections(scope)
    templates, catalog = codec.make_catalog(collections)
    (output / "catalog.pb").write_bytes(catalog)
    (output / "catalog.pb.zst").write_bytes(zstd.ZstdCompressor(level=3).compress(catalog))
    compressor = zstd.ZstdCompressor(level=3)
    decompressor = zstd.ZstdDecompressor()
    # JSON and Protobuf carry the exact same canonical document model. The
    # compact JSON control includes exactly the same templates and dynamic values.
    variants = {"json": {}, "protobuf": {}, "protobuf-templates": {}, "json-templates": {}}
    manifest = {
        "scope": scope,
        "source_sha": os.environ.get("SOURCE_SHA")
        or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "fixture_sha256": hashes,
        "collections": len(collections),
        "captures": sum(map(len, collections.values())),
        "movements": sum(
            len(d["_source"].get("movimentos", [])) for ds in collections.values() for d in ds
        ),
        "templates": len(templates),
        "catalog_sha256": sha256(catalog),
        "entries": [],
    }
    residual_bytes = {"protobuf": 0, "protobuf-templates": 0}
    for cnj, docs in collections.items():
        variants["json"][cnj] = codec.json_bytes({"cnj": cnj, "docs": docs})
        for name, compact in (("protobuf", False), ("protobuf-templates", True)):
            payload = codec.encode(cnj, docs, compact, templates)
            assert codec.json_bytes(
                codec.decode(payload, compact, templates)[1]
            ) == codec.json_bytes(docs), f"Full roundtrip failed for {name}/{cnj}"
            variants[name][cnj] = payload
            cls = demo_pb2.CompactCollection if compact else demo_pb2.CanonicalCollection
            residual_bytes[name] += sum(
                len(record.residual_json) for record in cls.FromString(payload).records
            )
        # This is the SAME compact logical representation (native fields and
        # corrections) encoded as JSON, not an independently optimized JSON codec.
        proto = demo_pb2.CompactCollection.FromString(variants["protobuf-templates"][cnj])
        variants["json-templates"][cnj] = codec.json_bytes(
            {
                "cnj": cnj,
                "records": [
                    {
                        "document": codec.native_dict(r.document),
                        "residual": json.loads(r.residual_json) if r.residual_json else [],
                    }
                    for r in proto.records
                ],
            }
        )
        manifest["entries"].append(
            {"cnj": cnj, "count": len(docs), "expected_sha256": sha256(codec.json_bytes(docs))}
        )
    (output / "catalog.json").write_bytes(codec.json_bytes(templates))
    (output / "catalog.json.zst").write_bytes(compressor.compress(codec.json_bytes(templates)))
    results = []
    for name, store in variants.items():
        folder = output / name
        folder.mkdir(exist_ok=True)
        for cnj, payload in store.items():
            extension = "pb" if name.startswith("protobuf") else "json"
            (folder / f"{cnj}.{extension}").write_bytes(payload)
            (folder / f"{cnj}.{extension}.zst").write_bytes(compressor.compress(payload))
        dict_payload = (
            catalog
            if name == "protobuf-templates"
            else codec.json_bytes(templates)
            if name == "json-templates"
            else b""
        )
        compact = name == "protobuf-templates"

        def read_all(store=store, name=name):
            loaded_templates = (
                codec.read_catalog(catalog)
                if name == "protobuf-templates"
                else json.loads(codec.json_bytes(templates))
                if name == "json-templates"
                else []
            )
            return [recover(name, payload, loaded_templates)[1] for payload in store.values()]

        for cnj, recovered in zip(store, read_all(), strict=True):
            assert codec.json_bytes(recovered) == codec.json_bytes(collections[cnj])

        compressed = [compressor.compress(payload) for payload in store.values()]
        row = {
            "variant": name,
            "data_bytes": sum(map(len, store.values())),
            "dictionary_bytes": len(dict_payload),
            "total_bytes": sum(map(len, store.values())) + len(dict_payload),
            "zstd_total_bytes": sum(map(len, compressed))
            + (len(compressor.compress(dict_payload)) if dict_payload else 0),
            "residual_json_bytes": residual_bytes.get(name, 0),
            "read_uncompressed": measure(read_all, repeats),
            "decompress_only": measure(
                lambda compressed=compressed: [decompressor.decompress(p) for p in compressed],
                repeats,
            ),
        }
        if name.startswith("protobuf"):
            row["encode_end_to_end"] = measure(
                lambda compact=compact: [
                    codec.encode(cnj, docs, compact, templates) for cnj, docs in collections.items()
                ],
                repeats,
            )
        results.append(row)
    report = {
        "manifest": manifest,
        "results": results,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "versions": {
                p: importlib.metadata.version(p) for p in ("protobuf", "grpcio-tools", "zstandard")
            },
        },
        "limits": [
            "No IA network/publication test",
            "Templates and lossless residuals included",
            "No claim to reproduce historical 41272 bytes",
            "In-memory timings; no cold network, RAM or index overhead",
            "JSON template row is the same logical projection, not a separately optimized JSON codec",
        ],
    }
    (output / "manifest.json").write_bytes(codec.json_bytes(manifest))
    (output / "results.json").write_bytes(codec.json_bytes(report))
    summary = [
        "# DataJud: demonstração Protobuf",
        "",
        f"Corpus: **{scope}** — {manifest['captures']} capturas, {len(collections)} CNJs, {manifest['movements']} movimentos.",
        "",
        "| Representação | Dados B | Dicionário B | Total B | Total Zstd B | Residual JSON B |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        summary.append(
            f"| {row['variant']} | {row['data_bytes']} | {row['dictionary_bytes']} | {row['total_bytes']} | {row['zstd_total_bytes']} | {row['residual_json_bytes']} |"
        )
    summary += [
        "",
        "Protobuf usa processo.proto compilado neste run, com diferenças residuais explícitas para preservar campos ausentes/nulos/desconhecidos e tipos não representáveis. O decoder é executado em outro processo e lê somente os artefatos publicados e as fixtures de referência.",
        "",
        "Sem decisão definitiva de arquitetura; estes números não reproduzem automaticamente os 41.272 B históricos.",
    ]
    (output / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


def verify(output: Path) -> None:
    import codec
    import zstandard as zstd

    manifest = json.loads((output / "manifest.json").read_bytes())
    collections, hashes = load_collections(manifest["scope"])
    assert hashes == manifest["fixture_sha256"], "Fixture hashes changed"
    catalog = (output / "catalog.pb").read_bytes()
    assert sha256(catalog) == manifest["catalog_sha256"], "Catalog hash mismatch"
    templates = codec.read_catalog(catalog)
    json_templates = json.loads((output / "catalog.json").read_bytes())
    assert codec.json_bytes(json_templates) == codec.json_bytes(templates), "JSON catalog mismatch"
    zctx = zstd.ZstdDecompressor()
    assert zctx.decompress((output / "catalog.pb.zst").read_bytes()) == catalog, (
        "Compressed catalog mismatch"
    )
    assert zctx.decompress((output / "catalog.json.zst").read_bytes()) == codec.json_bytes(
        templates
    ), "Compressed JSON catalog mismatch"
    verified = 0
    for entry in manifest["entries"]:
        cnj = entry["cnj"]
        expected = collections[cnj]
        for name in ("json", "json-templates", "protobuf", "protobuf-templates"):
            extension = "pb" if name.startswith("protobuf") else "json"
            path = output / name / f"{cnj}.{extension}"
            for payload in (
                path.read_bytes(),
                zctx.decompress(path.with_suffix(f".{extension}.zst").read_bytes()),
            ):
                recovered_cnj, recovered = recover(name, payload, templates)
                assert recovered_cnj == cnj and len(recovered) == entry["count"], (
                    f"Cardinality/CNJ mismatch: {name}/{cnj}"
                )
                assert codec.json_bytes(recovered) == codec.json_bytes(expected), (
                    f"Full fidelity mismatch: {name}/{cnj}"
                )
                assert sha256(codec.json_bytes(recovered)) == entry["expected_sha256"], (
                    "Recovered hash mismatch"
                )
        verified += len(expected)
    assert verified == manifest["captures"], "Not all captures verified"
    text = f"\n**PASS: {verified}/{verified} capturas reconstruídas integralmente nas duas variantes, sem/com Zstd, em processo separado.**\n"
    print(text)
    with (output / "summary.md").open("a", encoding="utf-8") as stream:
        stream.write(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as stream:
            stream.write((output / "summary.md").read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "datajud-protobuf")
    parser.add_argument("--scope", choices=("all-hits", "legacy-68"), default="all-hits")
    parser.add_argument("--repeats", type=int, default=11)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    generated = output / "generated"
    generated.mkdir(exist_ok=True)
    if not args.verify_only:
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
    if args.verify_only:
        verify(output)
    else:
        build(output, args.scope, args.repeats)
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--output",
                str(output),
                "--verify-only",
            ],
            check=True,
        )
        print((output / "summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
