"""Benchmark empírico de formatos de serialização para o DataJud (Issue #1710, #1711).

Compara:
1. JSON Canônico (bruto)
2. JSON.gz (gzip level 6)
3. FlatBuffers (Codec oficial estrito ao esquema processo.fbs)
4. Parquet (capa tabular com payload comprimido)

Mede de forma simétrica:
- Tamanho total em disco (bytes)
- Tempo de serialização (encoding) de toda a coleção
- Tempo de desserialização completa (decoding de TODOS os documentos)
- Tempo de projeção seletiva (leitura apenas da capa sem decodificar movimentos)
- Validação estrutural de zero-loss
"""

from __future__ import annotations

import gzip
import io
import json
import time
from pathlib import Path

import pandas as pd

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
        # Chave de proveniência completa: (index, id)
        doc_provs = {(d.get("_index"), d.get("_id")) for d in colecoes[cnj]}
        if (doc.get("_index"), doc.get("_id")) not in doc_provs:
            colecoes[cnj].append(doc)

    # 1. Carrega amostras brutas
    if BRUTO_PATH.exists():
        raw_data = json.loads(BRUTO_PATH.read_text(encoding="utf-8"))
        for t, hits in raw_data.get("amostras_tribunais", {}).items():
            for h in hits:
                adicionar_doc(h.get("_source", {}).get("numeroProcesso"), h)
        for h in raw_data.get("casos_multigrau", []):
            adicionar_doc(h.get("_source", {}).get("numeroProcesso"), h)
        for h in raw_data.get("casos_superiores", []):
            adicionar_doc(h.get("_source", {}).get("numeroProcesso"), h)

    # 2. Carrega pares multíndice comprovados (STJ + tribunais de origem)
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
    print(f"Total de coleções CNJ carregadas: {len(colecoes)}")
    total_docs = sum(len(docs) for docs in colecoes.values())
    multidoc_count = sum(1 for docs in colecoes.values() if len(docs) > 1)
    print(
        f"Total de documentos: {total_docs} (Casos com múltiplos documentos/graus/índices: {multidoc_count})"
    )

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
    json_docs_recovered = 0
    for cnj, payload in json_store.items():
        obj = json.loads(payload.decode("utf-8"))
        json_docs_recovered += len(obj.get("documentos", []))
    t_dec_json = time.perf_counter() - t0

    # 2. JSON.gz
    t0 = time.perf_counter()
    gz_bytes_total = 0
    gz_store = {}
    for cnj, payload in json_store.items():
        compressed = gzip.compress(payload, compresslevel=6)
        gz_bytes_total += len(compressed)
        gz_store[cnj] = compressed
    t_enc_gz = time.perf_counter() - t0

    t0 = time.perf_counter()
    gz_docs_recovered = 0
    for cnj, comp in gz_store.items():
        obj = json.loads(gzip.decompress(comp).decode("utf-8"))
        gz_docs_recovered += len(obj.get("documentos", []))
    t_dec_gz = time.perf_counter() - t0

    # 3. FlatBuffers (Esquema tipado oficial processo.fbs)
    t0 = time.perf_counter()
    fb_bytes_total = 0
    fb_store = {}
    for cnj, docs in colecoes.items():
        fb_buf = FlatBuffersCodec.encode_collection(cnj, docs)
        fb_bytes_total += len(fb_buf)
        fb_store[cnj] = fb_buf
    t_enc_fb = time.perf_counter() - t0

    # 3a. Decodificação Completa Tipada (TODOS os documentos da coleção)
    t0 = time.perf_counter()
    fb_docs_recovered_typed = 0
    for cnj, fb_buf in fb_store.items():
        docs_rec = FlatBuffersCodec.decode_collection(fb_buf, mode="typed")
        fb_docs_recovered_typed += len(docs_rec)
    t_dec_fb_typed = time.perf_counter() - t0

    # 3b. Projeção Seletiva (Capa Apenas)
    t0 = time.perf_counter()
    fb_docs_recovered_capa = 0
    for cnj, fb_buf in fb_store.items():
        docs_capa = FlatBuffersCodec.decode_collection(fb_buf, mode="capa")
        fb_docs_recovered_capa += len(docs_capa)
    t_dec_fb_capa = time.perf_counter() - t0

    # 3c. Decodificação Raw Zero-Loss
    t0 = time.perf_counter()
    fb_docs_recovered_raw = 0
    for cnj, fb_buf in fb_store.items():
        docs_raw = FlatBuffersCodec.decode_collection(fb_buf, mode="raw")
        fb_docs_recovered_raw += len(docs_raw)
    t_dec_fb_raw = time.perf_counter() - t0

    # 4. Parquet (Capa Tabular)
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
                    "classe_nome": src.get("classe", {}).get("nome") if src.get("classe") else None,
                    "orgao_nome": src.get("orgaoJulgador", {}).get("nome")
                    if src.get("orgaoJulgador")
                    else None,
                    "data_ajuizamento": src.get("dataAjuizamento"),
                    "data_atualizacao": src.get("dataHoraUltimaAtualizacao"),
                    "qtd_movimentos": len(src.get("movimentos", [])),
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
    pq_docs_recovered = len(df_read)
    t_dec_pq = time.perf_counter() - t0

    # Validação de simetria do benchmark
    assert json_docs_recovered == total_docs
    assert gz_docs_recovered == total_docs
    assert fb_docs_recovered_typed == total_docs
    assert fb_docs_recovered_raw == total_docs
    assert pq_docs_recovered == total_docs

    print(
        "\n======================= BENCHMARK SIMÉTRICO (TODOS OS DOCUMENTOS) ======================="
    )
    print(
        f"{'Formato':28} | {'Tamanho Total':14} | {'Enc Time (ms)':14} | {'Dec Time (ms)':14} | {'Ratio'}"
    )
    print("-" * 92)
    print(
        f"{'1. JSON Canônico Bruto':28} | {json_bytes_total:11,d} B | {t_enc_json * 1000:11.2f} ms | {t_dec_json * 1000:11.2f} ms | 1.000x"
    )
    print(
        f"{'2. JSON.gz (Nível 6)':28} | {gz_bytes_total:11,d} B | {t_enc_gz * 1000:11.2f} ms | {t_dec_gz * 1000:11.2f} ms | {gz_bytes_total / json_bytes_total:0.3f}x"
    )
    print(
        f"{'3. FlatBuffers (Tipado .fbs)':28} | {fb_bytes_total:11,d} B | {t_enc_fb * 1000:11.2f} ms | {t_dec_fb_typed * 1000:11.2f} ms | {fb_bytes_total / json_bytes_total:0.3f}x"
    )
    print(
        f"{'   -> Projeção Seletiva Capa':28} | {'(mesmo buffer)':14} | {'-':14} | {t_dec_fb_capa * 1000:11.2f} ms | -"
    )
    print(
        f"{'   -> Raw Zero-Loss Payload':28} | {'(mesmo buffer)':14} | {'-':14} | {t_dec_fb_raw * 1000:11.2f} ms | -"
    )
    print(
        f"{'4. Parquet (Zstd+Gz)':28} | {pq_bytes_total:11,d} B | {t_enc_pq * 1000:11.2f} ms | {t_dec_pq * 1000:11.2f} ms | {pq_bytes_total / json_bytes_total:0.3f}x"
    )
    print(
        "=========================================================================================="
    )


if __name__ == "__main__":
    executar_benchmark()
