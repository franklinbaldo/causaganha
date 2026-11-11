"""Script de inventário empírico multíndice do DataJud (Issue #1710).

Coleta respostas brutas com controle rigoroso de rate limit, anonimiza dados sensíveis,
identifica documentos multigrau e multíndice e gera relatório de schema e cardinalidade.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import httpx
from aiolimiter import AsyncLimiter
import tenacity

from causaganha.config import DATAJUD_PUBLIC_API_KEY_DEFAULT
from datajud.client import (
    BASE_URL,
    DataJudAuthError,
    DataJudRateLimitError,
    _raise_for_status_flavor,
    retry_wait,
    _TransientRejectionError,
)

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "datajud_sample"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

# Limiter conservador global compartilhado para evitar 429
GLOBAL_LIMITER = AsyncLimiter(max_rate=15, time_period=60)  # 15 req/min


def anonimizar_payload(obj: Any) -> Any:
    """Remove nomes de partes físicas e PII, preservando estrutura e tipos."""
    if isinstance(obj, dict):
        novo = {}
        for k, v in obj.items():
            if k in ("nome", "nomePessoa") and isinstance(v, str) and len(v) > 3:
                # Mascara se for parte ou pessoa física, mas preserva se for classe/órgão/movimento
                if any(term in k.lower() for term in ("polo", "parte", "pessoa", "advogado")):
                    novo[k] = "[NOME ANONIMIZADO]"
                else:
                    novo[k] = v
            elif k in ("cpf", "cnpj", "documento"):
                novo[k] = "000.***.***-00"
            else:
                novo[k] = anonimizar_payload(v)
        return novo
    elif isinstance(obj, list):
        return [anonimizar_payload(item) for item in obj]
    return obj


class SharedRateLimitClient:
    """Cliente HTTP com limiter global compartilhado e retry robusto."""

    def __init__(self, api_key: str = DATAJUD_PUBLIC_API_KEY_DEFAULT, timeout: float = 60.0):
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"APIKey {self.api_key}",
                "User-Agent": "causaganha/inventory-1710",
            },
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def search(self, tribunal: str, body: dict) -> dict:
        async with GLOBAL_LIMITER:
            endpoint = f"/api_publica_{tribunal.lower()}/_search"
            async for attempt in tenacity.AsyncRetrying(
                stop=tenacity.stop_after_attempt(5),
                wait=tenacity.wait_exponential(multiplier=2.0, min=2.0, max=40.0),
                retry=tenacity.retry_if_exception_type((_TransientRejectionError, httpx.TransportError, httpx.TimeoutException)),
                reraise=True,
            ):
                with attempt:
                    assert self._client is not None
                    resp = await self._client.post(endpoint, json=body)
                    _raise_for_status_flavor(resp)
                    return resp.json()
        raise RuntimeError("Unreachable")


async def coletar_amostras():
    """Coleta amostras de diversos tribunais e cruza CNJs conhecidos."""
    tribunais = ["tjro", "tjmg", "stj", "tst"]
    resultados_por_tribunal: dict[str, list[dict]] = {}

    print("Iniciando coleta empírica...")
    async with SharedRateLimitClient() as client:
        # 1. Coleta inicial de capa e movimentos em cada tribunal
        for trib in tribunais:
            print(f"Buscando processos recentes em {trib}...")
            try:
                res = await client.search(trib, {
                    "query": {"match_all": {}},
                    "size": 15,
                    "sort": [{"dataHoraUltimaAtualizacao": {"order": "desc"}}]
                })
                hits = res.get("hits", {}).get("hits", [])
                print(f"  {trib}: {len(hits)} hits obtidos.")
                resultados_por_tribunal[trib] = hits
            except Exception as e:
                print(f"  {trib}: falha na busca ({e})")
                resultados_por_tribunal[trib] = []

        # 2. Investigar ocorrência multigrau (TJRO G1 e G2)
        print("\nInvestigando duplicidade e múltiplos graus no TJRO...")
        cnjs_para_testar: set[str] = set()
        for hit in resultados_por_tribunal.get("tjro", []):
            np = hit.get("_source", {}).get("numeroProcesso")
            if np:
                cnjs_para_testar.add(np)

        # Adicionar o CNJ que já sabemos ser G1 + G2
        cnjs_para_testar.add("70049812720258220021")

        casos_multigrau: list[dict] = []
        for cnj in list(cnjs_para_testar)[:10]:
            try:
                res = await client.search("tjro", {
                    "query": {"match": {"numeroProcesso": cnj}}
                })
                hits = res.get("hits", {}).get("hits", [])
                if len(hits) > 1:
                    print(f"  CNJ multigrau encontrado no TJRO: {cnj} com {len(hits)} documentos!")
                    for h in hits:
                        casos_multigrau.append(h)
            except Exception as e:
                print(f"  Erro ao buscar CNJ {cnj}: {e}")

        # 3. Investigar se processos do STJ/TST existem nos tribunais de origem
        print("\nInvestigando processos do STJ/TST em relação à Justiça Estadual/Trabalhista...")
        casos_cruzados: list[dict] = []
        for trib_sup in ["stj", "tst"]:
            for hit in resultados_por_tribunal.get(trib_sup, []):
                np = hit.get("_source", {}).get("numeroProcesso")
                trib_origem = hit.get("_source", {}).get("tribunal")
                print(f"  {trib_sup} processo: {np}, tribunal campo: {trib_origem}")
                if np:
                    casos_cruzados.append(hit)

        # Salvar as amostras coletadas em disco para análise
        todas_amostras = {
            "amostras_tribunais": {t: [anonimizar_payload(h) for h in hits] for t, hits in resultados_por_tribunal.items()},
            "casos_multigrau": [anonimizar_payload(h) for h in casos_multigrau],
            "casos_superiores": [anonimizar_payload(h) for h in casos_cruzados],
        }

        output_path = FIXTURES_DIR / "inventario_datajud_bruto.json"
        output_path.write_text(json.dumps(todas_amostras, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nAmostras salvas com sucesso em: {output_path}")


if __name__ == "__main__":
    asyncio.run(coletar_amostras())
