"""Gerador de Shards e Índices Estáticos para o Protótipo DataJud IA Reader.

Gera:
1. Shard ZIP em modo ZIP_STORED contendo payloads .json.zst compactos.
2. Catálogo global estático de templates TPU (Estratégia B).
3. Micro-índices particionados por Tribunal e Ano com offsets de HTTP Range.
4. Mapa mestre de roteamento para o cliente estático.
"""

from __future__ import annotations

import glob
import gzip
import json
import os
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import zstandard as zstd  # noqa: E402

from datajud.schema.lossless_codec import LosslessCodec, LosslessVocabulary  # noqa: E402
from scripts.datajud.benchmark_formats import carregar_colecoes_cnj  # noqa: E402

PUBLIC_DIR = Path(__file__).resolve().parent / "public"
SHARDS_DIR = PUBLIC_DIR / "shards"
INDEXES_DIR = PUBLIC_DIR / "indexes"

SHARDS_DIR.mkdir(parents=True, exist_ok=True)
INDEXES_DIR.mkdir(parents=True, exist_ok=True)


def parse_cnj_parts(cnj: str) -> tuple[str, str, str]:
    """Extrai tribunal (J.TR), ano (AAAA) e sequencial de um CNJ limpo ou formatado."""
    digits = "".join(c for c in cnj if c.isdigit())
    if len(digits) == 20:
        # NNNNNNN-DD.AAAA.J.TR.OOOO
        ano = digits[9:13]
        j_tr = f"{digits[13]}.{digits[14:16]}"
        seq = digits[0:7]
        return j_tr, ano, seq
    return "outros", "geral", digits


def carregar_todas_as_colecoes() -> dict[str, list[dict[str, Any]]]:
    """Carrega fixtures do benchmark + todos os processos reais de data/datajud/daily/*.zip."""
    colecoes = carregar_colecoes_cnj()
    print(f"Coleções base do benchmark carregadas: {len(colecoes)}")

    daily_files = sorted(glob.glob(str(ROOT / "data" / "datajud" / "daily" / "*.zip")))
    print(f"Verificando arquivos em data/datajud/daily/: encontrados {len(daily_files)} zips")
    daily_count = 0

    for zpath in daily_files:
        try:
            with zipfile.ZipFile(zpath, "r") as z:
                for name in z.namelist():
                    if not name.endswith(".json.gz"):
                        continue
                    try:
                        raw_bytes = z.read(name)
                        doc_data = json.loads(gzip.decompress(raw_bytes).decode("utf-8"))
                        if "_source" in doc_data:
                            src = doc_data["_source"]
                        else:
                            src = doc_data
                        cnj = src.get("numeroProcesso") or name.split(".")[0]
                        clean_cnj = "".join(c for c in cnj if c.isdigit())
                        if not clean_cnj:
                            continue

                        envelope = {
                            "_source": src,
                            "_id": doc_data.get(
                                "_id",
                                f"{src.get('tribunal', 'tjro')}_{src.get('grau', 'G1')}_{clean_cnj}",
                            ),
                            "_index": f"api_publica_{src.get('tribunal', 'tjro').lower()}",
                        }

                        if clean_cnj not in colecoes:
                            colecoes[clean_cnj] = []

                        # Evita duplicatas da mesma instância
                        if not any(d.get("_id") == envelope["_id"] for d in colecoes[clean_cnj]):
                            colecoes[clean_cnj].append(envelope)
                            daily_count += 1
                    except Exception:
                        continue
        except Exception as e:
            print(f"Aviso ao ler {zpath}: {e}")

    print(f"Processos reais incorporados dos pacotes daily: {daily_count}")
    print(f"Total de processos unificados para o protótipo: {len(colecoes)}")
    return colecoes


def construir_catalogo_e_shards():
    print("Iniciando build do catálogo e shards estáticos...")
    colecoes = carregar_todas_as_colecoes()
    print(f"Total de coleções carregadas: {len(colecoes)}")

    # 1. Constrói o Catálogo de Templates TPU (Estratégia B)
    vocab_str = LosslessVocabulary()
    catalogo_tipos = {}  # tuple -> int
    catalogo_export = []

    # Primeiro passe: descobre templates
    for cnj, docs in colecoes.items():
        for d in docs:
            src = d.get("_source", {})
            for m in src.get("movimentos") or []:
                c_cod = m.get("codigo")
                c_nome = m.get("nome")
                comp_template = []
                for c in m.get("complementosTabelados") or []:
                    comp_template.append(
                        (
                            c.get("codigo"),
                            vocab_str.get_or_add(c.get("nome")),
                            vocab_str.get_or_add(c.get("descricao")),
                        )
                    )
                has_comps = "complementosTabelados" in m
                tipo_key = (c_cod, vocab_str.get_or_add(c_nome), tuple(comp_template), has_comps)
                if tipo_key not in catalogo_tipos:
                    t_id = len(catalogo_tipos) + 1  # IDs 1-based
                    catalogo_tipos[tipo_key] = t_id
                    catalogo_export.append(
                        {
                            "id": t_id,
                            "codigo": c_cod,
                            "nome": c_nome,
                            "complementos": [
                                {
                                    "codigo": ct[0],
                                    "nome": vocab_str.get(ct[1]),
                                    "descricao": vocab_str.get(ct[2]),
                                }
                                for ct in comp_template
                            ],
                            "tem_complementos": has_comps,
                        }
                    )

    # Salva o catálogo de templates TPU
    catalogo_path = PUBLIC_DIR / "catalogo_tpu.json"
    catalogo_path.write_text(
        json.dumps(
            {"total_tipos": len(catalogo_export), "tipos": catalogo_export},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Catálogo TPU salvo em {catalogo_path} ({len(catalogo_export)} templates únicos)")

    # 2. Compacta e gera os arquivos .json.zst individuais
    zstd_cctx = zstd.ZstdCompressor(level=3)
    shards_zip_path = SHARDS_DIR / "shard_001.zip"

    # Preparação das coleções em formato compacto
    payloads_zstd: dict[str, bytes] = {}
    metadados_processo: dict[str, dict[str, Any]] = {}

    for cnj, docs in colecoes.items():
        doc_entries = []
        instancias_encontradas = set()
        tribunal_origem = ""
        classe_nome = ""

        for d in docs:
            src = d.get("_source", {})
            grau = src.get("grau", "")
            trib = src.get("tribunal", "")
            if not tribunal_origem or grau == "G1":
                tribunal_origem = trib
            if not classe_nome:
                classe_nome = src.get("classe", {}).get("nome", "")
            instancias_encontradas.add(f"{trib} {grau}".strip())

            # Movimentos enxutos usando template IDs
            m_list = []
            for m in src.get("movimentos") or []:
                c_cod = m.get("codigo")
                c_nome = m.get("nome")
                comp_template = tuple(
                    (
                        c.get("codigo"),
                        vocab_str.str_to_id.get(c.get("nome"), -1),
                        vocab_str.str_to_id.get(c.get("descricao"), -1),
                    )
                    for c in (m.get("complementosTabelados") or [])
                )
                has_comps = "complementosTabelados" in m
                tipo_key = (
                    c_cod,
                    vocab_str.str_to_id.get(c_nome, -1),
                    comp_template,
                    has_comps,
                )
                t_id = catalogo_tipos[tipo_key]
                valores = [c.get("valor") for c in (m.get("complementosTabelados") or [])]
                m_oj = None
                if "orgaoJulgador" in m:
                    oj = m["orgaoJulgador"]
                    m_oj = [oj.get("codigo"), oj.get("nome")]
                m_entry = [t_id, m.get("dataHora"), m_oj]
                if valores:
                    m_entry.append(valores)
                m_list.append(m_entry)

            compact_doc = LosslessCodec.encode_document(d, vocab_str)
            compact_doc["m"] = m_list  # substitui movimentos por template IDs enxutos
            doc_entries.append(compact_doc)

        processo_payload = {
            "cnj": cnj,
            "total_documentos": len(docs),
            "documentos": doc_entries,
        }

        raw_json_bytes = json.dumps(processo_payload, ensure_ascii=False).encode("utf-8")
        compressed_zst = zstd_cctx.compress(raw_json_bytes)
        payloads_zstd[cnj] = compressed_zst

        j_tr, ano, _ = parse_cnj_parts(cnj)
        metadados_processo[cnj] = {
            "cnj": cnj,
            "tribunal": tribunal_origem,
            "ano": ano,
            "j_tr": j_tr,
            "classe": classe_nome,
            "instancias": sorted(list(instancias_encontradas)),
            "total_docs": len(docs),
            "uncompressed_bytes": len(raw_json_bytes),
            "compressed_bytes": len(compressed_zst),
        }

    # 3. Cria o container ZIP com compressão STORED (para permitir HTTP Range exato!)
    print(f"Escrevendo {len(payloads_zstd)} arquivos em {shards_zip_path} com ZIP_STORED...")
    with zipfile.ZipFile(shards_zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for cnj, data in payloads_zstd.items():
            member_name = f"{cnj}.json.zst"
            zf.writestr(member_name, data)

    # 4. Inspeciona os offsets de bytes exatos de cada membro dentro do ZIP
    offsets_por_cnj = {}
    with zipfile.ZipFile(shards_zip_path, "r") as zf:
        with open(shards_zip_path, "rb") as f_raw:
            for zinfo in zf.infolist():
                cnj = zinfo.filename.replace(".json.zst", "")
                header_offset = zinfo.header_offset
                filename_bytes_len = len(zinfo.filename.encode("utf-8"))
                extra_len = len(zinfo.extra)
                data_offset = header_offset + 30 + filename_bytes_len + extra_len
                length = zinfo.file_size

                # Auto-verificação de sanidade: lê o slice exato do arquivo bruto e compara!
                f_raw.seek(data_offset)
                slice_bytes = f_raw.read(length)
                expected_bytes = zf.read(zinfo.filename)
                assert slice_bytes == expected_bytes, f"Erro de alinhamento de offset no CNJ {cnj}!"

                offsets_por_cnj[cnj] = {
                    "shard": "shards/shard_001.zip",
                    "offset": data_offset,
                    "length": length,
                }

    print("Verificação de Range de bytes validada com 100% de precisão!")

    # 5. Gera os micro-índices particionados por Tribunal e Ano
    particoes = defaultdict(list)
    for cnj, meta in metadados_processo.items():
        part_key = f"{meta['j_tr']}_{meta['ano']}"
        entry = {
            "cnj": cnj,
            "shard": offsets_por_cnj[cnj]["shard"],
            "offset": offsets_por_cnj[cnj]["offset"],
            "length": offsets_por_cnj[cnj]["length"],
            "tribunal": meta["tribunal"],
            "classe": meta["classe"],
            "instancias": meta["instancias"],
            "compressed_size": meta["compressed_bytes"],
        }
        particoes[part_key].append(entry)

    router_map = {}
    for part_key, entries in particoes.items():
        part_file = INDEXES_DIR / f"{part_key}.json"
        part_file.write_text(
            json.dumps({"total": len(entries), "processos": entries}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        router_map[part_key] = {
            "url": f"indexes/{part_key}.json",
            "total_processos": len(entries),
            "tamanho_bytes": os.path.getsize(part_file),
        }
        print(f"Micro-índice criado: {part_file.name} ({len(entries)} processos)")

    # Salva o mapa mestre de roteamento
    router_path = INDEXES_DIR / "router_map.json"
    router_path.write_text(
        json.dumps(
            {
                "descricao": "Mapa estático de roteamento por Tribunal (J.TR) e Ano (AAAA)",
                "particoes": router_map,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Mapa mestre de roteamento salvo em {router_path}")
    print("\nPROTOTIPO BUILD FINALIZADO COM SUCESSO!")


if __name__ == "__main__":
    construir_catalogo_e_shards()
