"""Roteador Topológico de Decisões Judiciais baseado em Metadados do DJEN.

Determina com custo computacional nulo (< 0.01 ms) a topologia estrutural
da decisão (Sentença de 1º Grau, Acórdão Colegiado de 2º Grau, Execução/Cumprimento
ou Decisão Interlocutória) a partir dos metadados nativos do DJEN ou análise rápida
de cabeçalho institucional.
"""

from __future__ import annotations

import enum
import re
import unicodedata
from typing import Any


class DecisionTopology(str, enum.Enum):
    SENTENCA = "SENTENCA"
    ACORDAO = "ACORDAO"
    EXECUCAO = "EXECUCAO"
    INTERLOCUTORIA = "INTERLOCUTORIA"


def _norm(s: Any) -> str:
    if s is None or not isinstance(s, str):
        return ""
    normalized = unicodedata.normalize("NFKD", s)
    return "".join(c for c in normalized if not unicodedata.combining(c)).lower().strip()


class TopologyRouter:
    """Roteador determinístico baseado nos metadados do DJEN."""

    # Padrões de classes processuais
    ACORDAO_CLASSES = [
        "apelacao",
        "agravo de instrumento",
        "agravo interno",
        "recurso inominado",
        "embargos de declaracao",
        "remessa necessaria",
        "habeas corpus",
        "mandado de seguranca",
        "conflito de competencia",
        "revisao criminal",
        "acao rescisoria",
    ]

    EXECUCAO_CLASSES = [
        "cumprimento de sentenca",
        "execucao fiscal",
        "execucao de titulo",
        "execucao de alimentos",
        "monitoria",
    ]

    SENTENCA_CLASSES = [
        "procedimento comum",
        "juizado especial civel",
        "procedimento do juizado",
        "acao civil publica",
        "acao popular",
        "usucapiao",
        "divorcio",
        "despejo",
        "cobranca",
        "indenizatoria",
        "declaratoria",
    ]

    @classmethod
    def route(
        cls,
        metadata: dict[str, Any] | None = None,
        text: str = "",
    ) -> DecisionTopology:
        """Determina a topologia da decisão a partir dos metadados e cabeçalho."""
        meta = metadata or {}

        doc_type = _norm(meta.get("doc_type") or meta.get("tipoComunicacao") or meta.get("tipo_comunicacao"))
        classe = _norm(
            meta.get("classe_processual")
            or meta.get("classe")
            or meta.get("nomeClasse")
            or meta.get("nome_classe")
        )
        orgao = _norm(
            meta.get("orgao_julgador")
            or meta.get("nomeOrgao")
            or meta.get("nome_orgao")
            or meta.get("vara")
            or meta.get("comarca")
        )
        relator = _norm(meta.get("relator"))
        juiz = _norm(meta.get("judge_name") or meta.get("juiz"))

        # 1. Metadado explícito de doc_type
        if "acordao" in doc_type:
            return DecisionTopology.ACORDAO
        if "sentenca" in doc_type:
            return DecisionTopology.SENTENCA
        if "despacho" in doc_type or "interlocutoria" in doc_type:
            return DecisionTopology.INTERLOCUTORIA

        # 2. Metadado de Relator (presença de Relator indica colegiado/acórdão)
        if relator and len(relator) > 3:
            return DecisionTopology.ACORDAO

        # 3. Metadado de Órgão Julgador
        if any(term in orgao for term in ["camara", "turma", "pleno", "secao", "tribunal pleno", "colegiado", "turma recursal"]):
            return DecisionTopology.ACORDAO

        if any(term in orgao for term in ["vara", "juizado", "nucleo de justica", "gabinete da"]):
            if any(term in classe for term in cls.EXECUCAO_CLASSES):
                return DecisionTopology.EXECUCAO
            return DecisionTopology.SENTENCA

        # 4. Metadado de Classe Processual
        if any(term in classe for term in cls.EXECUCAO_CLASSES):
            return DecisionTopology.EXECUCAO

        if any(term in classe for term in cls.ACORDAO_CLASSES):
            return DecisionTopology.ACORDAO

        if any(term in classe for term in cls.SENTENCA_CLASSES):
            return DecisionTopology.SENTENCA

        # 5. Fallback por inspeção rápida do cabeçalho (primeiros 800 caracteres)
        header = _norm(text[:800])
        if "acordam" in header or "acordao" in header or "sessao de julgamento" in header:
            return DecisionTopology.ACORDAO

        if "sentenca" in header or "vistos etc" in header or "juiz de direito" in header:
            if "cumprimento de sentenca" in header or "execucao" in header:
                return DecisionTopology.EXECUCAO
            return DecisionTopology.SENTENCA

        if "despacho" in header or "vistos." in header:
            return DecisionTopology.INTERLOCUTORIA

        # Default mais comum no DJEN cível de primeiro grau
        return DecisionTopology.SENTENCA
