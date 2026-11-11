"""Benchmark empírico aprofundado de formatos para o DataJud (Issue #1710, #1711).

Compara de forma rigorosa e simétrica:
1. JSON Canônico Bruto
2. JSON.gz (nível 6)
3. JSON.zst (Zstandard nível 3)
4. FlatBuffers v1 (Esquema processo.fbs com cópia bruta duplicada)
5. FlatBuffers Híbrido (Capa plana O(1) em FB + Bloco de Movimentos em Zstandard)
6. Parquet (Capa tabular com descompressão de payload)

Mede:
- Tamanho total em bytes
- Ratio de compressão vs JSON original
- Tempo de serialização (encoding)
- Tempo de recuperação integral (full decode de todos os documentos)
- Tempo de projeção seletiva (leitura da capa sem decodificar movimentos)
"""

from __future__ import annotations

import gzip
import io
import json
import time
from pathlib import Path

import pandas as pd
import zstandard as zstd

from datajud.schema.compact_codec import CompactFlatBuffersCodec
from datajud.schema.flatbuffers_codec import FlatBuffersCodec

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "datajud_sample"
BRUTO_PATH = FIXTURES_DIR / "inventario_datajud_bruto.json"
PARES_PATH = FIXTURES_DIR / "pares_multindice_comprovados.json"


def carregar_colecoes_cnj() -> dict[str, list[dict]]:
    """Carrega dados reais incluindo casos multigrau e pares multíndice comprovados."""
    colecoes: dict[str, list[dict]] = {}

    def adicionar_doc(cnj: str, doc: dict):
        if not cnj:
            return
        if cnj not in colecoes:
            colecoes[cnj] = []
        doc_provs = {(d.get("_index"), d.get("_id")) for d in colecoes[cnj]}
        if (doc.get("_index"), doc.get("_id")) not in doc_provs:
            colecoes[cnj].append(doc)

    if BRUTO_PATH.exists():
        raw_data = json.loads(BRUTO_PATH.read_text(encoding="utf-8"))
        for t, hits in raw_data.get("amostras_tribunais", {}).items():
            for h in hits:
                adicionar_doc(h.get("_source", {}).get("numeroProcesso"), h)
        for h in raw_data.get("casos_multigrau", []):
            adicionar_doc(h.get("_source", {}).get("numeroProcesso"), h)
        for h in raw_data.get("casos_superiores", []):
            adicionar_doc(h.get("_source", {}).get("numeroProcesso"), h)

    if PARES_PATH.exists():
        pares = json.loads(PARES_PATH.read_text(encoding="utf-8"))
        for par in pares:
            cnj = par.get("cnj")
            for h in par.get("documentos_origem", []):
                adicionar_doc(cnj, h)
            for h in par.get("documentos_superior", []):
                adicionar_doc(cnj, h)

    return colecoes


def executar_benchmark():
    colecoes = carregar_colecoes_cnj()
    total_docs = sum(len(docs) for docs in colecoes.values())
    multidoc_count = sum(1 for docs in colecoes.values() if len(docs) > 1)
    print(f"Total de coleções CNJ: {len(colecoes)}")
    print(f"Total de documentos: {total_docs} (Casos multíndice/multigrau: {multidoc_count})")

    # 1. JSON Canônico
    t0 = time.perf_counter()
    json_bytes_total = 0
    json_store = {}
    for cnj, docs in colecoes.items():
        payload = json.dumps({"cnj": cnj, "documentos": docs}, ensure_ascii=False).encode("utf-8")
        json_bytes_total += len(payload)
        json_store[cnj] = payload
    t_enc_json = time.perf_counter() - t0

    t0 = time.perf_counter()
    json_recovered = 0
    for payload in json_store.values():
        obj = json.loads(payload.decode("utf-8"))
        json_recovered += len(obj.get("documentos", []))
    t_dec_json = time.perf_counter() - t0

    # 2. JSON.gz (L6)
    t0 = time.perf_counter()
    gz_bytes_total = 0
    gz_store = {}
    for cnj, payload in json_store.items():
        comp = gzip.compress(payload, compresslevel=6)
        gz_bytes_total += len(comp)
        gz_store[cnj] = comp
    t_enc_gz = time.perf_counter() - t0

    t0 = time.perf_counter()
    gz_recovered = 0
    for comp in gz_store.values():
        obj = json.loads(gzip.decompress(comp).decode("utf-8"))
        gz_recovered += len(obj.get("documentos", []))
    t_dec_gz = time.perf_counter() - t0

    # 3. JSON.zst (Zstandard L3)
    zstd_cctx = zstd.ZstdCompressor(level=3)
    zstd_dctx = zstd.ZstdDecompressor()

    t0 = time.perf_counter()
    zst_bytes_total = 0
    zst_store = {}
    for cnj, payload in json_store.items():
        comp = zstd_cctx.compress(payload)
        zst_bytes_total += len(comp)
        zst_store[cnj] = comp
    t_enc_zst = time.perf_counter() - t0

    t0 = time.perf_counter()
    zst_recovered = 0
    for comp in zst_store.values():
        obj = json.loads(zstd_dctx.decompress(comp).decode("utf-8"))
        zst_recovered += len(obj.get("documentos", []))
    t_dec_zst = time.perf_counter() - t0

    # 4. FlatBuffers v1 (Esquema processo.fbs com cópia bruta duplicada)
    t0 = time.perf_counter()
    fb1_bytes_total = 0
    fb1_store = {}
    for cnj, docs in colecoes.items():
        buf = FlatBuffersCodec.encode_collection(cnj, docs)
        fb1_bytes_total += len(buf)
        fb1_store[cnj] = buf
    t_enc_fb1 = time.perf_counter() - t0

    t0 = time.perf_counter()
    fb1_recovered_full = 0
    for buf in fb1_store.values():
        rec = FlatBuffersCodec.decode_collection(buf, mode="raw")
        fb1_recovered_full += len(rec)
    t_dec_fb1_full = time.perf_counter() - t0

    # 5. FlatBuffers Híbrido (Capa Plana O(1) + Movimentos em Zstandard)
    t0 = time.perf_counter()
    fb_hyb_bytes_total = 0
    fb_hyb_store = {}
    for cnj, docs in colecoes.items():
        buf = CompactFlatBuffersCodec.encode_hybrid(cnj, docs)
        fb_hyb_bytes_total += len(buf)
        fb_hyb_store[cnj] = buf
    t_enc_fb_hyb = time.perf_counter() - t0

    t0 = time.perf_counter()
    fb_hyb_recovered_capa = 0
    for buf in fb_hyb_store.values():
        capas = CompactFlatBuffersCodec.decode_capa_only(buf)
        fb_hyb_recovered_capa += len(capas)
    t_dec_fb_hyb_capa = time.perf_counter() - t0

    t0 = time.perf_counter()
    fb_hyb_recovered_full = 0
    for buf in fb_hyb_store.values():
        docs_full = CompactFlatBuffersCodec.decode_full(buf)
        fb_hyb_recovered_full += len(docs_full)
    t_dec_fb_hyb_full = time.perf_counter() - t0

    # 6. Parquet (Capa + Payload Comprimido)
    t0 = time.perf_counter()
    rows = []
    for cnj, docs in colecoes.items():
        for d in docs:
            src = d.get("_source", {})
            rows.append(
                {
                    "cnj": cnj,
                    "_id": d.get("_id"),
                    "_index": d.get("_index"),
                    "tribunal": src.get("tribunal"),
                    "grau": src.get("grau"),
                    "classe_codigo": src.get("classe", {}).get("codigo")
                    if src.get("classe")
                    else None,
                    "data_ajuizamento": src.get("dataAjuizamento"),
                    "payload_json_gz": gzip.compress(json.dumps(d).encode("utf-8")),
                }
            )
    df = pd.DataFrame(rows)
    buf_pq = io.BytesIO()
    df.to_parquet(buf_pq, engine="pyarrow", compression="zstd")
    pq_bytes_total = len(buf_pq.getvalue())
    t_enc_pq = time.perf_counter() - t0

    t0 = time.perf_counter()
    buf_pq.seek(0)
    df_read = pd.read_parquet(buf_pq, engine="pyarrow")
    pq_recovered = 0
    for payload in df_read["payload_json_gz"]:
        _ = json.loads(gzip.decompress(payload).decode("utf-8"))
        pq_recovered += 1
    t_dec_pq_full = time.perf_counter() - t0

    # Validação de simetria do benchmark
    assert json_recovered == total_docs
    assert gz_recovered == total_docs
    assert zst_recovered == total_docs
    assert fb1_recovered_full == total_docs
    assert fb_hyb_recovered_capa == total_docs
    assert fb_hyb_recovered_full == total_docs
    assert pq_recovered == total_docs

    print(
        "\n========================= BENCHMARK MULTI-VARIANTE (DATAJUD) ========================="
    )
    print(f"{'Formato':32} | {'Tamanho Total':14} | {'Enc Time':12} | {'Dec Time':12} | {'Ratio'}")
    print("-" * 92)
    print(
        f"{'1. JSON Canônico Bruto':32} | {json_bytes_total:11,d} B | {t_enc_json * 1000:9.2f} ms | {t_dec_json * 1000:9.2f} ms | 1.000x"
    )
    print(
        f"{'2. JSON.gz (Nível 6)':32} | {gz_bytes_total:11,d} B | {t_enc_gz * 1000:9.2f} ms | {t_dec_gz * 1000:9.2f} ms | {gz_bytes_total / json_bytes_total:0.3f}x"
    )
    print(
        f"{'3. JSON.zst (Zstandard L3)':32} | {zst_bytes_total:11,d} B | {t_enc_zst * 1000:9.2f} ms | {t_dec_zst * 1000:9.2f} ms | {zst_bytes_total / json_bytes_total:0.3f}x"
    )
    print(
        f"{'4. FlatBuffers v1 (c/ cópia Gz)':32} | {fb1_bytes_total:11,d} B | {t_enc_fb1 * 1000:9.2f} ms | {t_dec_fb1_full * 1000:9.2f} ms | {fb1_bytes_total / json_bytes_total:0.3f}x"
    )
    print(
        f"{'5. FlatBuffers Híbrido':32} | {fb_hyb_bytes_total:11,d} B | {t_enc_fb_hyb * 1000:9.2f} ms | {t_dec_fb_hyb_full * 1000:9.2f} ms | {fb_hyb_bytes_total / json_bytes_total:0.3f}x"
    )
    print(
        f"{'   -> Projeção Capa O(1) direta':32} | {'(mesmo buffer)':14} | {'-':12} | {t_dec_fb_hyb_capa * 1000:9.2f} ms | -"
    )
    print(
        f"{'6. Parquet (Capa + Payload Gz)':32} | {pq_bytes_total:11,d} B | {t_enc_pq * 1000:9.2f} ms | {t_dec_pq_full * 1000:9.2f} ms | {pq_bytes_total / json_bytes_total:0.3f}x"
    )
    print(
        "========================================================================================"
    )


if __name__ == "__main__":
    executar_benchmark()
