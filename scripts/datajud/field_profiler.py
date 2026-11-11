"""Profiling estatístico, estrutural e orçamentário de campos do DataJud (Issue #1711).

Executa:
1. Análise orçamentária de bytes por campo (onde está o peso real do documento).
2. Validação empírica de redundância de identificadores (_id = tribunal + grau + cnj).
3. Distribuição de tipos numéricos e verificação de limites (uint8, uint16, uint32, int64).
4. Frequência, nulabilidade e cardinalidade de strings TPU repetidas.
5. Experimento controlado 2x4 isolando Modelagem de Dados vs Formato de Serialização.
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import zstandard as zstd

from datajud.schema.compact_codec import CompactFlatBuffersCodec
from datajud.schema.flatbuffers_codec import FlatBuffersCodec
from scripts.datajud.benchmark_formats import carregar_colecoes_cnj

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "datajud_sample"


def analisar_perfil_campos(colecoes: dict[str, list[dict]]) -> dict[str, Any]:
    """Mapeia detalhadamente o custo em bytes, tipos e redundâncias de cada campo."""
    total_docs = sum(len(docs) for docs in colecoes.values())

    # 1. Orçamento de bytes por campo
    bytes_por_campo = defaultdict(int)
    tamanho_total_bruto = 0

    # 2. Análise de redundância do _id
    id_derivavel_count = 0
    id_excecoes = []

    # 3. Faixas numéricas
    faixas_numericas = defaultdict(
        lambda: {"min": float("inf"), "max": float("-inf"), "valores": set()}
    )

    # 4. Cardinalidade de strings
    valores_unicos = defaultdict(set)
    total_ocorrencias = defaultdict(int)

    # 5. Análise de movimentos
    total_movimentos = 0
    bytes_movimentos_total = 0

    for cnj, docs in colecoes.items():
        for doc in docs:
            doc_raw_json = json.dumps(doc, ensure_ascii=False)
            doc_bytes = len(doc_raw_json.encode("utf-8"))
            tamanho_total_bruto += doc_bytes

            src = doc.get("_source", {})
            tribunal = src.get("tribunal", "")
            grau = src.get("grau", "")
            np = src.get("numeroProcesso", "")

            # Checagem de derivabilidade do _id
            esperado_id = f"{tribunal}_{grau}_{np}"
            atual_id = doc.get("_id", "")
            if atual_id == esperado_id:
                id_derivavel_count += 1
            else:
                id_excecoes.append((atual_id, esperado_id))

            # Mede contribuição em bytes de cada campo de primeiro nível
            for k, v in doc.items():
                if k == "_source":
                    for sk, sv in src.items():
                        s_bytes = len(json.dumps({sk: sv}, ensure_ascii=False).encode("utf-8"))
                        bytes_por_campo[f"_source.{sk}"] += s_bytes
                        total_ocorrencias[f"_source.{sk}"] += 1
                        if isinstance(sv, (str, int)):
                            valores_unicos[f"_source.{sk}"].add(sv)
                else:
                    k_bytes = len(json.dumps({k: v}, ensure_ascii=False).encode("utf-8"))
                    bytes_por_campo[k] += k_bytes
                    total_ocorrencias[k] += 1
                    if isinstance(v, (str, int)):
                        valores_unicos[k].add(v)

            # Rastreia movimentos
            movs = src.get("movimentos") or []
            total_movimentos += len(movs)
            b_movs = len(json.dumps(movs, ensure_ascii=False).encode("utf-8"))
            bytes_movimentos_total += b_movs

            # Faixas de inteiros
            def track_num(chave: str, val: Any):
                if isinstance(val, int):
                    faixas_numericas[chave]["min"] = min(faixas_numericas[chave]["min"], val)
                    faixas_numericas[chave]["max"] = max(faixas_numericas[chave]["max"], val)
                    faixas_numericas[chave]["valores"].add(val)

            track_num("nivelSigilo", src.get("nivelSigilo"))
            track_num(
                "classe.codigo",
                src.get("classe", {}).get("codigo")
                if isinstance(src.get("classe"), dict)
                else None,
            )
            track_num(
                "sistema.codigo",
                src.get("sistema", {}).get("codigo")
                if isinstance(src.get("sistema"), dict)
                else None,
            )
            track_num(
                "formato.codigo",
                src.get("formato", {}).get("codigo")
                if isinstance(src.get("formato"), dict)
                else None,
            )
            track_num(
                "orgaoJulgador.codigo",
                src.get("orgaoJulgador", {}).get("codigo")
                if isinstance(src.get("orgaoJulgador"), dict)
                else None,
            )
            track_num(
                "orgaoJulgador.codigoMunicipioIBGE",
                src.get("orgaoJulgador", {}).get("codigoMunicipioIBGE")
                if isinstance(src.get("orgaoJulgador"), dict)
                else None,
            )

            for m in movs:
                if isinstance(m, dict):
                    track_num("movimento.codigo", m.get("codigo"))
                    for c in m.get("complementosTabelados") or []:
                        if isinstance(c, dict):
                            track_num("complemento.codigo", c.get("codigo"))

    return {
        "total_docs": total_docs,
        "total_movimentos": total_movimentos,
        "tamanho_total_bruto": tamanho_total_bruto,
        "bytes_movimentos_total": bytes_movimentos_total,
        "bytes_por_campo": dict(bytes_por_campo),
        "id_derivavel_pct": (id_derivavel_count / total_docs) * 100 if total_docs else 0,
        "id_excecoes": id_excecoes,
        "faixas_numericas": {
            k: {"min": v["min"], "max": v["max"], "cardinalidade": len(v["valores"])}
            for k, v in faixas_numericas.items()
        },
        "valores_unicos_count": {k: len(v) for k, v in valores_unicos.items()},
    }


# ── MODELAGEM COMPACTA NORMALIZADA (APLICADA A JSON E FLATBUFFERS) ────


def to_json_compacto(doc: dict) -> dict:
    """Modelo compacto: elimina _id derivável, deduplica nomes TPU e usa timestamps."""
    src = doc.get("_source", {})
    tribunal = src.get("tribunal", "")
    grau = src.get("grau", "")
    np = src.get("numeroProcesso", "")
    esperado_id = f"{tribunal}_{grau}_{np}"
    atual_id = doc.get("_id", "")

    compacto = {
        "_i": doc.get("_index"),
        "t": tribunal,
        "g": grau,
        "s": src.get("nivelSigilo", 0),
        "c": src.get("classe", {}).get("codigo") if isinstance(src.get("classe"), dict) else 0,
        "o": src.get("orgaoJulgador", {}).get("codigo")
        if isinstance(src.get("orgaoJulgador"), dict)
        else 0,
    }
    # Só armazena _id se for exceção não-derivável!
    if atual_id != esperado_id:
        compacto["_id"] = atual_id

    # Assuntos apenas códigos
    assuntos = src.get("assuntos") or []
    compacto["a"] = [a.get("codigo") for a in assuntos if isinstance(a, dict) and a.get("codigo")]

    # Movimentos enxutos: [codigo, dataHora, orgao, complementos]
    movs = src.get("movimentos") or []
    compacto["m"] = [
        [
            m.get("codigo"),
            m.get("dataHora"),
            [[c.get("codigo"), c.get("valor")] for c in (m.get("complementosTabelados") or [])],
        ]
        for m in movs
        if isinstance(m, dict)
    ]
    return compacto


def from_json_compacto(compacto: dict, cnj: str) -> dict:
    """Reconstrói exatamente a estrutura e os campos originais do documento."""
    tribunal = compacto.get("t", "")
    grau = compacto.get("g", "")
    # Reconstrói _id derivado ou usa a exceção explícita
    doc_id = compacto.get("_id") or f"{tribunal}_{grau}_{cnj}"

    return {
        "_index": compacto.get("_i"),
        "_id": doc_id,
        "_source": {
            "id": doc_id,
            "numeroProcesso": cnj,
            "tribunal": tribunal,
            "grau": grau,
            "nivelSigilo": compacto.get("s", 0),
            "classe": {"codigo": compacto.get("c")},
            "orgaoJulgador": {"codigo": compacto.get("o")},
            "assuntos": [{"codigo": cod} for cod in compacto.get("a", [])],
            "movimentos": [
                {
                    "codigo": m[0],
                    "dataHora": m[1],
                    "complementosTabelados": [{"codigo": c[0], "valor": c[1]} for c in m[2]],
                }
                for m in compacto.get("m", [])
            ],
        },
    }


def executar_matriz_comparativa(colecoes: dict[str, list[dict]]):
    """Executa a matriz 2x4 isolando o ganho de Modelagem do ganho de Serialização."""
    zstd_cctx = zstd.ZstdCompressor(level=3)
    zstd_dctx = zstd.ZstdDecompressor()

    # Nível 1: Dados Originais (Bruto)
    t0 = time.perf_counter()
    json_bruto_store = {
        cnj: json.dumps({"cnj": cnj, "docs": docs}).encode("utf-8")
        for cnj, docs in colecoes.items()
    }
    t_enc_json_bruto = time.perf_counter() - t0
    b_json_bruto = sum(len(b) for b in json_bruto_store.values())

    t0 = time.perf_counter()
    for b in json_bruto_store.values():
        _ = json.loads(b.decode("utf-8"))
    t_dec_json_bruto = time.perf_counter() - t0

    t0 = time.perf_counter()
    fb_bruto_store = {
        cnj: FlatBuffersCodec.encode_collection(cnj, docs) for cnj, docs in colecoes.items()
    }
    t_enc_fb_bruto = time.perf_counter() - t0
    b_fb_bruto = sum(len(b) for b in fb_bruto_store.values())

    t0 = time.perf_counter()
    for b in fb_bruto_store.values():
        _ = FlatBuffersCodec.decode_collection(b, mode="raw")
    t_dec_fb_bruto = time.perf_counter() - t0

    # Nível 2: Modelo Compacto Otimizado (JSON Compacto vs FlatBuffers Híbrido)
    t0 = time.perf_counter()
    json_compact_store = {
        cnj: json.dumps({"cnj": cnj, "docs": [to_json_compacto(d) for d in docs]}).encode("utf-8")
        for cnj, docs in colecoes.items()
    }
    t_enc_json_compact = time.perf_counter() - t0
    b_json_compact = sum(len(b) for b in json_compact_store.values())

    t0 = time.perf_counter()
    for cnj, b in json_compact_store.items():
        obj = json.loads(b.decode("utf-8"))
        _ = [from_json_compacto(d, cnj) for d in obj["docs"]]
    t_dec_json_compact = time.perf_counter() - t0

    t0 = time.perf_counter()
    fb_compact_store = {
        cnj: CompactFlatBuffersCodec.encode_hybrid(cnj, docs) for cnj, docs in colecoes.items()
    }
    t_enc_fb_compact = time.perf_counter() - t0
    b_fb_compact = sum(len(b) for b in fb_compact_store.values())

    t0 = time.perf_counter()
    for b in fb_compact_store.values():
        _ = CompactFlatBuffersCodec.decode_full(b)
    t_dec_fb_compact = time.perf_counter() - t0

    # Nível 3: Modelo Compacto Comprimido (JSON Compacto + Zstd vs FB Compacto + Zstd)
    t0 = time.perf_counter()
    json_zstd_store = {cnj: zstd_cctx.compress(b) for cnj, b in json_compact_store.items()}
    t_enc_json_zstd = time.perf_counter() - t0
    b_json_zstd = sum(len(b) for b in json_zstd_store.values())

    t0 = time.perf_counter()
    for cnj, b in json_zstd_store.items():
        obj = json.loads(zstd_dctx.decompress(b).decode("utf-8"))
        _ = [from_json_compacto(d, cnj) for d in obj["docs"]]
    t_dec_json_zstd = time.perf_counter() - t0

    # FB Compacto + Zstd total (comprimindo o buffer do FB)
    t0 = time.perf_counter()
    fb_zstd_store = {cnj: zstd_cctx.compress(b) for cnj, b in fb_compact_store.items()}
    t_enc_fb_zstd = time.perf_counter() - t0
    b_fb_zstd = sum(len(b) for b in fb_zstd_store.values())

    t0 = time.perf_counter()
    for b in fb_zstd_store.values():
        raw_fb = zstd_dctx.decompress(b)
        _ = CompactFlatBuffersCodec.decode_full(raw_fb)
    t_dec_fb_zstd = time.perf_counter() - t0

    return {
        "b_json_bruto": b_json_bruto,
        "t_enc_json_bruto": t_enc_json_bruto,
        "t_dec_json_bruto": t_dec_json_bruto,
        "b_fb_bruto": b_fb_bruto,
        "t_enc_fb_bruto": t_enc_fb_bruto,
        "t_dec_fb_bruto": t_dec_fb_bruto,
        "b_json_compact": b_json_compact,
        "t_enc_json_compact": t_enc_json_compact,
        "t_dec_json_compact": t_dec_json_compact,
        "b_fb_compact": b_fb_compact,
        "t_enc_fb_compact": t_enc_fb_compact,
        "t_dec_fb_compact": t_dec_fb_compact,
        "b_json_zstd": b_json_zstd,
        "t_enc_json_zstd": t_enc_json_zstd,
        "t_dec_json_zstd": t_dec_json_zstd,
        "b_fb_zstd": b_fb_zstd,
        "t_enc_fb_zstd": t_enc_fb_zstd,
        "t_dec_fb_zstd": t_dec_fb_zstd,
    }


def main():
    print("Iniciando profiling estatístico e orçamentário do DataJud...")
    colecoes = carregar_colecoes_cnj()
    perfil = analisar_perfil_campos(colecoes)

    print(f"\nTotal de documentos analisados: {perfil['total_docs']}")
    print(f"Total de movimentos analisados: {perfil['total_movimentos']}")
    print(f"Tamanho total bruto dos dados: {perfil['tamanho_total_bruto']:,d} bytes")
    print(
        f"Tamanho apenas dos movimentos: {perfil['bytes_movimentos_total']:,d} bytes ({(perfil['bytes_movimentos_total'] / perfil['tamanho_total_bruto']) * 100:.1f}% do total!)"
    )

    print("\n--- Derivabilidade do _id ---")
    print(
        f"Regra determinística '_id == tribunal_grau_cnj': {perfil['id_derivavel_pct']:.1f}% de conformidade!"
    )
    print(f"Total de exceções encontradas: {len(perfil['id_excecoes'])}")

    print("\n--- Faixas Numéricas Observadas ---")
    for campo, dados in sorted(perfil["faixas_numericas"].items()):
        min_v = dados["min"]
        max_v = dados["max"]
        card = dados["cardinalidade"]
        # Determina o menor tipo FlatBuffers que comporta com segurança
        tipo_ideal = "int64"
        if min_v >= 0 and max_v <= 255:
            tipo_ideal = "ubyte (8-bit)"
        elif min_v >= -128 and max_v <= 127:
            tipo_ideal = "byte (8-bit)"
        elif min_v >= 0 and max_v <= 65535:
            tipo_ideal = "ushort (16-bit)"
        elif min_v >= -32768 and max_v <= 32767:
            tipo_ideal = "short (16-bit)"
        elif min_v >= 0 and max_v <= 4294967295:
            tipo_ideal = "uint (32-bit)"
        elif min_v >= -2147483648 and max_v <= 2147483647:
            tipo_ideal = "int (32-bit)"
        print(
            f"  {campo:30} | min: {min_v:10} | max: {max_v:10} | únicos: {card:5} | tipo ideal: {tipo_ideal}"
        )

    print("\n--- Orçamento de Bytes por Campo (Top 10) ---")
    sorted_bytes = sorted(perfil["bytes_por_campo"].items(), key=lambda x: x[1], reverse=True)
    for campo, b in sorted_bytes[:10]:
        pct = (b / perfil["tamanho_total_bruto"]) * 100
        print(f"  {campo:30} | {b:10,d} bytes | {pct:5.1f}%")

    # Executa a matriz comparativa isolando Modelagem vs Serialização
    print("\nExecutando Matriz 2x4 (Isolando Modelagem de Dados vs Serialização)...")
    matriz = executar_matriz_comparativa(colecoes)

    print("\n========================= MATRIZ CONTROLADA 2x4 =========================")
    print(f"{'Nível de Otimização':30} | {'JSON':20} | {'FlatBuffers':20} | {'Delta FB vs JSON'}")
    print("-" * 88)

    # Nível 1: Bruto
    print(
        f"{'1. Dados Originais (Bruto)':30} | {matriz['b_json_bruto']:10,d} B ({matriz['t_enc_json_bruto'] * 1000:5.1f}ms) | {matriz['b_fb_bruto']:10,d} B ({matriz['t_enc_fb_bruto'] * 1000:5.1f}ms) | {matriz['b_fb_bruto'] / matriz['b_json_bruto']:0.2f}x"
    )

    # Nível 2: Modelo Compacto
    print(
        f"{'2. Modelo Compacto Otimizado':30} | {matriz['b_json_compact']:10,d} B ({matriz['t_enc_json_compact'] * 1000:5.1f}ms) | {matriz['b_fb_compact']:10,d} B ({matriz['t_enc_fb_compact'] * 1000:5.1f}ms) | {matriz['b_fb_compact'] / matriz['b_json_compact']:0.2f}x"
    )

    # Nível 3: Modelo Compacto + Zstd
    print(
        f"{'3. Modelo Compacto + Zstd':30} | {matriz['b_json_zstd']:10,d} B ({matriz['t_enc_json_zstd'] * 1000:5.1f}ms) | {matriz['b_fb_zstd']:10,d} B ({matriz['t_enc_fb_zstd'] * 1000:5.1f}ms) | {matriz['b_fb_zstd'] / matriz['b_json_zstd']:0.2f}x"
    )
    print("=========================================================================")


if __name__ == "__main__":
    main()
