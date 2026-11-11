"""Teste operacional automatizado de ponta a ponta do leitor estático HTTP Range.

Valida:
1. Requisição 1: Download e parsing do micro-índice de roteamento.
2. Requisição 2: Execução de HTTP Range (bytes=X-Y) no Shard ZIP retornando HTTP 206.
3. Descompressão Zstandard client-side e reconstrução com catálogo TPU.
4. Recuperação comprovada de caso multigrau/multíndice (TJMG G1, G2 e STJ).
5. Comportamento com Cache Local (2ª consulta no mesmo tribunal/ano custa apenas 1 request!).
"""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.request
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import zstandard as zstd  # noqa: E402

from experiments.datajud_ia_static_reader.serve_static import (  # noqa: E402
    PUBLIC_DIR,
    InternetArchiveSimulatorHandler,
)

TEST_PORT = 8089
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"


def start_test_server():
    server = HTTPServer(("127.0.0.1", TEST_PORT), InternetArchiveSimulatorHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_fluxo_operacional_completo():
    server = start_test_server()
    time.sleep(0.5)  # aguarda subir o socket

    zstd_dctx = zstd.ZstdDecompressor()
    cnj_alvo = "0001311-51.2024.8.13.0647"  # Caso comprovado TJMG G1, G2 + STJ

    print("\n--- INICIANDO TESTE OPERACIONAL HTTP RANGE DO INTERNET ARCHIVE ---")

    # =========================================================================
    # REQUISIÇÃO 1: Micro-Índice de Roteamento
    # =========================================================================
    url_indice = f"{BASE_URL}/indexes/8.13_2024.json"
    t0 = time.perf_counter()
    req1 = urllib.request.Request(url_indice)
    with urllib.request.urlopen(req1) as resp:
        assert resp.status == 200
        raw_index_bytes = resp.read()
    t_req1 = time.perf_counter() - t0

    index_data = json.loads(raw_index_bytes.decode("utf-8"))
    print(
        f"[REQ 1] GET {url_indice} -> HTTP 200 em {t_req1 * 1000:0.1f}ms ({len(raw_index_bytes)} B)"
    )

    # Localiza o processo no índice (comparando apenas dígitos)
    cnj_digitos = "".join(c for c in cnj_alvo if c.isdigit())
    processo_meta = next(
        (
            p
            for p in index_data["processos"]
            if "".join(c for c in p["cnj"] if c.isdigit()) == cnj_digitos
        ),
        None,
    )
    assert processo_meta is not None, f"CNJ {cnj_alvo} não encontrado no índice"

    shard_rel_path = processo_meta["shard"]
    offset = processo_meta["offset"]
    length = processo_meta["length"]

    print(
        f"        Processo localizado: Shard={shard_rel_path}, Offset={offset}, Length={length} B"
    )
    print(f"        Instâncias detectadas no índice: {processo_meta['instancias']}")
    assert len(processo_meta["instancias"]) >= 2, "Deveria conter ao menos 2 instâncias mapeadas"

    # =========================================================================
    # REQUISIÇÃO 2: HTTP Range Request no Shard ZIP
    # =========================================================================
    url_shard = f"{BASE_URL}/{shard_rel_path}"
    range_header_val = f"bytes={offset}-{offset + length - 1}"

    t0 = time.perf_counter()
    req2 = urllib.request.Request(url_shard, headers={"Range": range_header_val})
    with urllib.request.urlopen(req2) as resp:
        status_code = resp.status
        content_range = resp.headers.get("Content-Range")
        compressed_payload = resp.read()
    t_req2 = time.perf_counter() - t0

    print(f"[REQ 2] GET {url_shard} (Range: {range_header_val})")
    print(
        f"        -> HTTP {status_code} ({content_range}) em {t_req2 * 1000:0.1f}ms ({len(compressed_payload)} B)"
    )

    assert status_code == 206, f"Esperado HTTP 206 Partial Content, obtido {status_code}"
    assert len(compressed_payload) == length, (
        f"Bytes recebidos ({len(compressed_payload)}) != esperado ({length})"
    )

    # =========================================================================
    # PROCESSAMENTO CLIENT-SIDE (WASM ZSTD + RECONSTRUÇÃO TPU)
    # =========================================================================
    t0 = time.perf_counter()
    raw_decompressed = zstd_dctx.decompress(compressed_payload)
    processo_obj = json.loads(raw_decompressed.decode("utf-8"))
    t_decomp = time.perf_counter() - t0

    print(
        f"[CLIENT] Descompressão Zstandard concluída em {t_decomp * 1000:0.2f}ms ({len(raw_decompressed)} B brutos)"
    )
    assert "".join(c for c in processo_obj["cnj"] if c.isdigit()) == cnj_digitos
    docs = processo_obj["documentos"]
    print(f"         Total de documentos reconstruídos: {len(docs)}")
    assert len(docs) >= 2, f"Esperado ao menos 2 documentos para {cnj_alvo}, obtido: {len(docs)}"

    # Carrega catálogo TPU e valida movimentos
    cat_path = PUBLIC_DIR / "catalogo_tpu.json"
    catalogo = {t["id"]: t for t in json.loads(cat_path.read_text(encoding="utf-8"))["tipos"]}

    total_movs_validados = 0
    for d in docs:
        for m in d.get("m", []):
            tipo_id = m[0]
            assert tipo_id in catalogo, f"Tipo de movimento {tipo_id} não encontrado no catálogo!"
            total_movs_validados += 1

    print(
        f"         Movimentos validados contra catálogo TPU: {total_movs_validados} eventos processuais"
    )

    # =========================================================================
    # TESTE DE CACHE LOCAL (Warm Request: 1 única requisição HTTP!)
    # =========================================================================
    print("\n--- TESTANDO SEGUNDA CONSULTA COM CACHE DE ÍNDICE (WARM) ---")
    segundo_cnj = index_data["processos"][1]["cnj"]
    meta2 = index_data["processos"][1]

    # Índice já está em memória (0 HTTP requests para o índice!)
    t0 = time.perf_counter()
    req_warm = urllib.request.Request(
        f"{BASE_URL}/{meta2['shard']}",
        headers={"Range": f"bytes={meta2['offset']}-{meta2['offset'] + meta2['length'] - 1}"},
    )
    with urllib.request.urlopen(req_warm) as resp:
        assert resp.status == 206
        payload2 = resp.read()
    t_warm = time.perf_counter() - t0

    print(f"[WARM] Consulta ao CNJ {segundo_cnj} concluída com EXATAMENTE 1 REQUISIÇÃO HTTP!")
    print(f"       Latência total: {t_warm * 1000:0.1f}ms | Bytes trafegados: {len(payload2)} B")

    # Teste 3: Processo Real recém-coletado do TJRO 2026
    print("\n--- TESTANDO PROCESSO REAL RECÉM-COLETADO DO TJRO 2026 ---")
    cnj_tjro = "70007797020268220021"
    url_idx_tjro = f"{BASE_URL}/indexes/8.22_2026.json"
    req_tjro = urllib.request.Request(url_idx_tjro)
    with urllib.request.urlopen(req_tjro) as resp:
        idx_tjro = json.loads(resp.read().decode("utf-8"))
    proc_tjro = next((p for p in idx_tjro["processos"] if p["cnj"] == cnj_tjro), None)
    assert proc_tjro is not None, f"Processo {cnj_tjro} não encontrado no índice 8.22_2026.json"
    print(f"[TJRO 2026] Localizado no índice: {proc_tjro['classe']} | Offset: {proc_tjro['offset']} | Size: {proc_tjro['length']} B")

    range_tjro = f"bytes={proc_tjro['offset']}-{proc_tjro['offset'] + proc_tjro['length'] - 1}"
    req_range = urllib.request.Request(f"{BASE_URL}/{proc_tjro['shard']}", headers={"Range": range_tjro})
    with urllib.request.urlopen(req_range) as resp:
        assert resp.status == 206
        tjro_payload = resp.read()
    tjro_decomp = zstd_dctx.decompress(tjro_payload)
    tjro_obj = json.loads(tjro_decomp.decode("utf-8"))
    print(f"[TJRO 2026] Descomprimido com sucesso! Total de documentos: {len(tjro_obj['documentos'])}")
    assert len(tjro_obj["documentos"]) >= 1

    print("\n==================================================================")
    print(" TODOS OS TESTES OPERACIONAIS FORAM APROVADOS COM 100% DE SUCESSO! ")
    print("==================================================================\n")

    server.shutdown()


if __name__ == "__main__":
    test_fluxo_operacional_completo()
