"""Cruzamento empírico pareado de CNJs entre tribunais de origem e instâncias superiores.

Executa consultas pareadas para o MESMO CNJ em múltiplos índices do DataJud
e salva os pares comprovados em fixtures com rastreabilidade total.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx

from datajud.client import DataJudClient, DataJudError

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "datajud_sample"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


def sanitizar_contextual(obj: Any, path: tuple = ()) -> Any:
    """Anonimiza PII com base estrita no contexto hierárquico da chave."""
    if isinstance(obj, dict):
        novo = {}
        for k, v in obj.items():
            current_path = path + (k,)

            # Se for nome de parte, pessoa ou advogado no contexto
            is_pii_context = any(
                p.lower() in ("partes", "poloativo", "polopassivo", "advogados", "pessoas")
                for p in path
            )
            if is_pii_context and k == "nome" and isinstance(v, str):
                novo[k] = "[NOME ANONIMIZADO]"
            elif k in ("cpf", "cnpj", "documento"):
                novo[k] = "000.***.***-00"
            else:
                novo[k] = sanitizar_contextual(v, current_path)
        return novo
    elif isinstance(obj, list):
        return [sanitizar_contextual(item, path) for item in obj]
    return obj


async def buscar_cnj(client: DataJudClient, cnj: str) -> list[dict]:
    # Tentativa com match e term no numeroProcesso
    try:
        res = await client.search(body={"query": {"match": {"numeroProcesso": cnj}}})
        return res.get("hits", {}).get("hits", [])
    except (DataJudError, httpx.HTTPError) as exc:
        print(f"  Erro ao buscar CNJ {cnj} em {client.tribunal}: {exc}")
        return []


async def executar_cruzamento():
    print("Iniciando cruzamento pareado de índices para o mesmo CNJ...")

    # 1. Obter CNJs recentes do STJ e do TST
    cnjs_stj = []
    async with DataJudClient(tribunal="stj") as stj_client:
        res = await stj_client.search(
            body={
                "query": {"match_all": {}},
                "size": 10,
                "sort": [{"dataHoraUltimaAtualizacao": {"order": "desc"}}],
            }
        )
        for hit in res.get("hits", {}).get("hits", []):
            np = hit.get("_source", {}).get("numeroProcesso")
            if np:
                cnjs_stj.append((np, hit))
    print(f"Obtidos {len(cnjs_stj)} processos no STJ.")

    pares_confirmados = []

    # Mapeamento J.TR -> sigla do tribunal
    # J=8: 13 -> tjmg, 26 -> tjsp, 22 -> tjro, 09 -> tjgo, etc.
    mapeamento_j8 = {
        "13": "tjmg",
        "26": "tjsp",
        "22": "tjro",
        "09": "tjgo",
        "24": "tjsc",
        "18": "tjpi",
        "16": "tjpr",
    }
    mapeamento_j4 = {
        "01": "trf1",
        "02": "trf2",
        "03": "trf3",
        "04": "trf4",
        "05": "trf5",
        "06": "trf6",
    }

    for cnj, stj_hit in cnjs_stj:
        # CNJ tem 20 dígitos: NNNNNNN-DD.AAAA.J.TR.OOOO
        # Índices de string: J está na posição 13, TR na 14:16
        if len(cnj) != 20:
            continue
        j = cnj[13]
        tr = cnj[14:16]

        trib_origem = None
        if j == "8" and tr in mapeamento_j8:
            trib_origem = mapeamento_j8[tr]
        elif j == "4" and tr in mapeamento_j4:
            trib_origem = mapeamento_j4[tr]

        if not trib_origem:
            continue

        print(f"\nConsultando CNJ {cnj}: STJ (encontrado) vs {trib_origem} (origem)...")
        await asyncio.sleep(2.0)  # Evitar rate limit
        async with DataJudClient(tribunal=trib_origem) as orig_client:
            orig_hits = await buscar_cnj(orig_client, cnj)
            print(f"  Resultado em {trib_origem}: {len(orig_hits)} hits encontrados!")

            if orig_hits:
                par_info = {
                    "cnj": cnj,
                    "ramo_justica": j,
                    "tribunal_regiao": tr,
                    "tribunal_origem": trib_origem,
                    "tribunal_superior": "stj",
                    "documentos_origem": [sanitizar_contextual(h) for h in orig_hits],
                    "documentos_superior": [sanitizar_contextual(stj_hit)],
                }
                pares_confirmados.append(par_info)
                print(f"  >>> SUCESSO: Par multíndice confirmado para CNJ {cnj}!")

    out_file = FIXTURES_DIR / "pares_multindice_comprovados.json"
    out_file.write_text(
        json.dumps(pares_confirmados, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nTotal de pares multíndice comprovados: {len(pares_confirmados)}")
    print(f"Salvo em: {out_file}")


if __name__ == "__main__":
    asyncio.run(executar_cruzamento())
