"""Extração e Enriquecimento de Classe Processual (TPU CNJ) via DataJud + NER Léxico.

Implementa uma estratégia em 4 camadas para identificar a Classe Processual oficial (TPU CNJ):
1. `datajud_acervo`: Consulta em 0ms ao banco relacional append-only local (`acervo.sqlite` v3
   da skill `datajud`), retornando `classe_codigo`, `classe_nome`, `grau`, `orgao_julgador`,
   `assunto_principal` e movimentos oficiais de julgamento (Oráculo de Supervisão Distante).
2. `metadado_djen`: Normalização de metadados explícitos da publicação (`classe_codigo`, `classe_hint`).
3. `cabecalho_ner`: Extração léxica no cabeçalho da decisão (`Classe: ...`, `APELAÇÃO CÍVEL (198)`, etc.)
   mapeada para a Tabela Processual Unificada (TPU) do CNJ.
4. `inferencia_taxonomia`: Inferência estrutural a partir da `especie_ato` e do órgão julgador.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import sqlite3
import unicodedata
from typing import Any


# Tabela Processual Unificada (TPU CNJ) — Classes mais frequentes na Justiça Estadual/Federal/JE
TPU_CLASSES_CNJ: dict[int, str] = {
    7: "Procedimento Comum Cível",
    37: "Alvará Judicial - Lei 6858/80",
    40: "Monitória",
    49: "Usucapião",
    65: "Ação Civil Pública",
    69: "Alimentos - Lei Especial Nº 5.478/68",
    81: "Busca e Apreensão em Alienação Fiduciária",
    90: "Despejo",
    98: "Inventário",
    120: "Mandado de Segurança Cível",
    156: "Cumprimento de sentença",
    159: "Execução de Título Extrajudicial",
    172: "Embargos à Execução",
    198: "Apelação Cível",
    202: "Agravo de Instrumento",
    206: "Agravo Interno Cível",
    282: "Ação Penal de Competência do Júri",
    283: "Ação Penal - Procedimento Ordinário",
    305: "Liberdade Provisória com ou sem fiança",
    307: "Habeas Corpus Criminal",
    417: "Apelação Criminal",
    420: "Embargos de Declaração Criminal",
    436: "Procedimento do Juizado Especial Cível",
    460: "Recurso Inominado Cível",
    1032: "Recurso Especial",
    1033: "Recurso Extraordinário",
    1116: "Execução Fiscal",
    1269: "Medidas Protetivas de urgência (Lei Maria da Penha)",
    1689: "Embargos de Declaração Cível",
    1727: "Apelação / Remessa Necessária",
    10943: "Ação Penal Militar - Procedimento Ordinário",
    12078: "Cumprimento de Sentença contra a Fazenda Pública",
    12541: "Divórcio Litigioso",
    14672: "Pedido de Uniformização de Interpretação de Lei Cível",
    14695: "Procedimento do Juizado Especial da Fazenda Pública",
}

# Mapeamento dos códigos TPU CNJ de movimentos decisórios para o desfecho operativo do CausaGanha
TPU_MOVIMENTO_PARA_DESFECHO: dict[int, str] = {
    219: "procedente",
    220: "improcedente",
    221: "parcialmente procedente",
    237: "provido",
    238: "parcialmente provido",
    239: "não provido",
    240: "não conhecido",
    242: "não conhecido",
    196: "extinção da execução",
    466: "acordo",
    14099: "acordo",
    218: "extinto sem mérito",
    222: "extinto sem mérito",
    454: "extinto sem mérito",
    472: "homologação de decisão leiga",
}

# Regras léxicas ordenadas por especificidade para extração no cabeçalho / metadados
_LEXICAL_CLASS_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (
        re.compile(r"\bjuizado\s+especial\s+da\s+fazenda\s+p[uú]blica\b", re.I),
        14695,
        TPU_CLASSES_CNJ[14695],
    ),
    (
        re.compile(r"\bcumprimento\s+de\s+senten[cç]a\s+contra\s+a\s+fazenda\s+p[uú]blica\b", re.I),
        12078,
        TPU_CLASSES_CNJ[12078],
    ),
    (
        re.compile(r"\bbusca\s+e\s+apreens[aã]o\s+em\s+aliena[cç][aã]o\s+fiduci[aá]ria\b", re.I),
        81,
        TPU_CLASSES_CNJ[81],
    ),
    (
        re.compile(r"\ba[cç][aã]o\s+penal\s+militar\b", re.I),
        10943,
        TPU_CLASSES_CNJ[10943],
    ),
    (
        re.compile(r"\ba[cç][aã]o\s+penal\s+de\s+compet[eê]ncia\s+do\s+j[uú]ri\b", re.I),
        282,
        TPU_CLASSES_CNJ[282],
    ),
    (
        re.compile(r"\bmedidas?\s+protetivas?\s+de\s+urg[eê]ncia\b", re.I),
        1269,
        TPU_CLASSES_CNJ[1269],
    ),
    (
        re.compile(r"\bliberdade\s+provis[oó]ria\b", re.I),
        305,
        TPU_CLASSES_CNJ[305],
    ),
    (
        re.compile(r"\bpedido\s+de\s+uniformiza[cç][aã]o\b", re.I),
        14672,
        TPU_CLASSES_CNJ[14672],
    ),
    (
        re.compile(r"\brecurso\s+inominado\b", re.I),
        460,
        TPU_CLASSES_CNJ[460],
    ),
    (
        re.compile(r"\bapela[cç][aã]o\s+criminal\b", re.I),
        417,
        TPU_CLASSES_CNJ[417],
    ),
    (
        re.compile(r"\bapela[cç][aã]o\s*/?\s*remessa\s+necess[aá]ria\b", re.I),
        1727,
        TPU_CLASSES_CNJ[1727],
    ),
    (
        re.compile(r"\bapela[cç][aã]o\s+c[ií]vel\b", re.I),
        198,
        TPU_CLASSES_CNJ[198],
    ),
    (
        re.compile(r"\bagravo\s+de\s+instrumento\b", re.I),
        202,
        TPU_CLASSES_CNJ[202],
    ),
    (
        re.compile(r"\bagravo\s+interno\b", re.I),
        206,
        TPU_CLASSES_CNJ[206],
    ),
    (
        re.compile(r"\bembargos\s+de\s+declara[cç][aã]o\s+criminal\b", re.I),
        420,
        TPU_CLASSES_CNJ[420],
    ),
    (
        re.compile(r"\bembargos\s+de\s+declara[cç][aã]o\b", re.I),
        1689,
        TPU_CLASSES_CNJ[1689],
    ),
    (
        re.compile(r"\bexecu[cç][aã]o\s+fiscal\b", re.I),
        1116,
        TPU_CLASSES_CNJ[1116],
    ),
    (
        re.compile(r"\bexecu[cç][aã]o\s+de\s+t[ií]tulo\s+extrajudicial\b", re.I),
        159,
        TPU_CLASSES_CNJ[159],
    ),
    (
        re.compile(r"\bembargos\s+[aà]\s+execu[cç][aã]o\b", re.I),
        172,
        TPU_CLASSES_CNJ[172],
    ),
    (
        re.compile(r"\bcumprimento\s+de\s+senten[cç]a\b", re.I),
        156,
        TPU_CLASSES_CNJ[156],
    ),
    (
        re.compile(r"\bmandado\s+de\s+seguran[cç]a\b", re.I),
        120,
        TPU_CLASSES_CNJ[120],
    ),
    (
        re.compile(r"\bhabeas\s+corpus\b", re.I),
        307,
        TPU_CLASSES_CNJ[307],
    ),
    (
        re.compile(r"\ba[cç][aã]o\s+penal\b", re.I),
        283,
        TPU_CLASSES_CNJ[283],
    ),
    (
        re.compile(r"\bprocedimento\s+do\s+juizado\s+especial\s+c[ií]vel\b", re.I),
        436,
        TPU_CLASSES_CNJ[436],
    ),
    (
        re.compile(r"\bprocedimento\s+comum\s+c[ií]vel\b", re.I),
        7,
        TPU_CLASSES_CNJ[7],
    ),
    (
        re.compile(r"\balimentos\s*-\s*lei\s+especial\b|\ba[cç][aã]o\s+de\s+alimentos\b", re.I),
        69,
        TPU_CLASSES_CNJ[69],
    ),
    (
        re.compile(r"\balvar[aá]\s+judicial\b", re.I),
        37,
        TPU_CLASSES_CNJ[37],
    ),
    (
        re.compile(r"\binvent[aá]rio\b", re.I),
        98,
        TPU_CLASSES_CNJ[98],
    ),
    (
        re.compile(r"\bdiv[oó]rcio\b", re.I),
        12541,
        TPU_CLASSES_CNJ[12541],
    ),
    (
        re.compile(r"\busucapi[aã]o\b", re.I),
        49,
        TPU_CLASSES_CNJ[49],
    ),
    (
        re.compile(r"\ba[cç][aã]o\s+monit[oó]ria\b|\bclasse:\s*monit[oó]ria\b", re.I),
        40,
        TPU_CLASSES_CNJ[40],
    ),
    (
        re.compile(r"\ba[cç][aã]o\s+civil\s+p[uú]blica\b", re.I),
        65,
        TPU_CLASSES_CNJ[65],
    ),
]

_CNJ_DIGITS_RE = re.compile(r"\b(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}|\d{20})\b")
_EXPLICIT_HEADER_CLASSE_RE = re.compile(
    r"(?:classe(?:\s+processual)?|processo)\s*:\s*([A-ZÀ-Úa-zà-ú0-9\s/\-()ºª.,]{3,80})",
    re.IGNORECASE,
)
_EXPLICIT_CODE_IN_PARENS_RE = re.compile(r"\((\d{1,6})\)")


def _default_acervo_path() -> Path:
    """Localiza o arquivo `acervo.sqlite` seguindo a convenção da skill `datajud`."""
    env_path = os.environ.get("DATAJUD_BANCO")
    if env_path:
        return Path(env_path).expanduser()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "datajud" / "acervo.sqlite"
    xdg_data = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg_data) if xdg_data else Path.home() / ".local" / "share"
    return base / "datajud" / "acervo.sqlite"


@dataclass(frozen=True)
class DataJudProcessSnapshot:
    """Instantâneo enriquecido de um processo extraído do `acervo.sqlite` (DataJud)."""

    numero_processo: str
    classe_codigo: int | None
    classe_nome: str | None
    grau: str | None = None
    orgao_nome: str | None = None
    assunto_principal: str | None = None
    desfecho_tpu: str | None = None
    movimento_tpu_codigo: int | None = None
    movimento_tpu_nome: str | None = None


@dataclass
class ClasseProcessualResult:
    """Resultado consolidado da identificação de classe processual e enriquecimento DataJud."""

    classe_codigo: int | None
    classe_nome: str
    origem_classe: (
        str  # "datajud_acervo" | "metadado_djen" | "cabecalho_ner" | "inferencia_taxonomia"
    )
    confianca_classe: float
    grau: str | None = None
    orgao_julgador: str | None = None
    assunto_principal: str | None = None
    datajud_desfecho_tpu: str | None = None
    datajud_movimento_codigo: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "classe_codigo": self.classe_codigo,
            "classe_nome": self.classe_nome,
            "origem_classe": self.origem_classe,
            "confianca_classe": round(self.confianca_classe, 4),
            "grau": self.grau,
            "orgao_julgador": self.orgao_julgador,
            "assunto_principal": self.assunto_principal,
            "datajud_desfecho_tpu": self.datajud_desfecho_tpu,
            "datajud_movimento_codigo": self.datajud_movimento_codigo,
        }


class DataJudAcervoReader:
    """Leitor somente-leitura de alta velocidade para o `acervo.sqlite` (v3) da skill DataJud."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else _default_acervo_path()
        self._cache: dict[str, DataJudProcessSnapshot | None] = {}
        self._bulk_loaded = False

    def is_available(self) -> bool:
        return self.db_path.exists() and self.db_path.is_file()

    def preload_all(self) -> int:
        """Carrega todas as capas, assuntos e movimentos decisórios do `acervo.sqlite` em memória."""
        if self._bulk_loaded or not self.is_available():
            return len(self._cache)

        try:
            con = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=5.0)
        except sqlite3.Error:
            return 0

        try:
            # 1. Carrega a capa mais recente de cada registro
            rows = con.execute(
                """
                SELECT r.id, r.numero_processo, r.grau,
                       c.classe_codigo, c.classe_nome,
                       org.nome AS orgao_nome
                FROM registros AS r
                LEFT JOIN observacoes AS o ON o.id = (
                    SELECT o2.id FROM observacoes AS o2
                    WHERE o2.registro_id = r.id AND o2.capa_id IS NOT NULL
                    ORDER BY o2.id DESC LIMIT 1
                )
                LEFT JOIN capas AS c ON c.id = o.capa_id
                LEFT JOIN orgaos AS org ON org.id = c.orgao_id
                ORDER BY r.id ASC
                """
            ).fetchall()

            reg_to_num: dict[int, str] = {}
            temp_caps: dict[str, dict[str, Any]] = {}
            for reg_id, num, grau, c_cod, c_nome, org_nome in rows:
                if not num:
                    continue
                reg_to_num[reg_id] = num
                # Prioriza G1/JE na capa base ou atualiza caso ainda não tenha classe_codigo
                existing = temp_caps.get(num)
                if existing is None or (
                    existing.get("classe_codigo") is None and c_cod is not None
                ):
                    temp_caps[num] = {
                        "numero_processo": num,
                        "classe_codigo": c_cod,
                        "classe_nome": c_nome,
                        "grau": grau,
                        "orgao_nome": org_nome,
                        "assunto_principal": None,
                        "desfecho_tpu": None,
                        "movimento_tpu_codigo": None,
                        "movimento_tpu_nome": None,
                    }

            # 2. Carrega assunto principal por registro
            for reg_id, a_nome in con.execute(
                "SELECT registro_id, nome FROM assuntos WHERE nome IS NOT NULL ORDER BY id ASC"
            ):
                num = reg_to_num.get(reg_id)
                if num and num in temp_caps and not temp_caps[num]["assunto_principal"]:
                    temp_caps[num]["assunto_principal"] = a_nome

            # 3. Carrega movimentos decisórios da TPU CNJ (Oráculo de Supervisão Distante)
            tpu_codes = tuple(TPU_MOVIMENTO_PARA_DESFECHO.keys())
            placeholders = ",".join("?" for _ in tpu_codes)
            for reg_id, m_cod, m_nome in con.execute(
                f"""
                SELECT m.registro_id, t.codigo, t.nome
                FROM movimentos AS m
                JOIN tipos_movimento AS t ON t.id = m.tipo_id
                WHERE t.codigo IN ({placeholders})
                ORDER BY m.instante ASC, m.id ASC
                """,
                tpu_codes,
            ):
                num = reg_to_num.get(reg_id)
                if num and num in temp_caps and m_cod in TPU_MOVIMENTO_PARA_DESFECHO:
                    temp_caps[num]["desfecho_tpu"] = TPU_MOVIMENTO_PARA_DESFECHO[m_cod]
                    temp_caps[num]["movimento_tpu_codigo"] = m_cod
                    temp_caps[num]["movimento_tpu_nome"] = m_nome

            for num, data in temp_caps.items():
                self._cache[num] = DataJudProcessSnapshot(**data)

            self._bulk_loaded = True
        except sqlite3.Error:
            pass
        finally:
            con.close()

        return len(self._cache)

    def lookup(self, cnj: str | None) -> DataJudProcessSnapshot | None:
        """Busca o processo de 20 dígitos no acervo local em memória (0ms após preload)."""
        if not cnj:
            return None
        digits = "".join(c for c in str(cnj) if c.isdigit())
        if len(digits) != 20:
            return None
        if not self._bulk_loaded:
            self.preload_all()
        return self._cache.get(digits)


class ClasseProcessualExtractor:
    """Extrator híbrido de Classe Processual (DataJud `acervo.sqlite` + NER Cabeçalho + Taxonomia)."""

    def __init__(self, acervo_reader: DataJudAcervoReader | None = None):
        self.acervo = acervo_reader or DataJudAcervoReader()

    def extract(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        especie_ato: str | None = None,
        macro_categoria: str | None = None,
    ) -> ClasseProcessualResult:
        meta = metadata or {}

        # 1. Identifica CNJ nos metadados ou no texto
        cnj_candidate = (
            meta.get("cnj") or meta.get("numero_processo") or meta.get("process_number") or ""
        )
        if not cnj_candidate and text:
            m_cnj = _CNJ_DIGITS_RE.search(text[:1500])
            if m_cnj:
                cnj_candidate = m_cnj.group(1)

        # Camada 1: Lookup no `acervo.sqlite` do DataJud
        snapshot = self.acervo.lookup(str(cnj_candidate)) if cnj_candidate else None
        if snapshot and snapshot.classe_nome:
            return ClasseProcessualResult(
                classe_codigo=snapshot.classe_codigo,
                classe_nome=snapshot.classe_nome,
                origem_classe="datajud_acervo",
                confianca_classe=0.99,
                grau=snapshot.grau,
                orgao_julgador=snapshot.orgao_nome,
                assunto_principal=snapshot.assunto_principal,
                datajud_desfecho_tpu=snapshot.desfecho_tpu,
                datajud_movimento_codigo=snapshot.movimento_tpu_codigo,
            )

        # Camada 2: Metadado explícito da publicação DJEN
        meta_classe = str(
            meta.get("classe_hint")
            or meta.get("classe_processual")
            or meta.get("procedural_class")
            or ""
        ).strip()
        meta_codigo = meta.get("classe_codigo")
        if isinstance(meta_codigo, int) and meta_codigo in TPU_CLASSES_CNJ:
            return ClasseProcessualResult(
                classe_codigo=meta_codigo,
                classe_nome=TPU_CLASSES_CNJ[meta_codigo],
                origem_classe="metadado_djen",
                confianca_classe=0.97,
                grau=snapshot.grau if snapshot else None,
                orgao_julgador=snapshot.orgao_nome if snapshot else None,
                assunto_principal=snapshot.assunto_principal if snapshot else None,
                datajud_desfecho_tpu=snapshot.desfecho_tpu if snapshot else None,
                datajud_movimento_codigo=snapshot.movimento_tpu_codigo if snapshot else None,
            )
        if meta_classe and meta_classe.lower() not in {"none", "null", "nan", "outro"}:
            matched_meta = self._match_lexical(meta_classe)
            if matched_meta:
                cod, nome = matched_meta
                return ClasseProcessualResult(
                    classe_codigo=cod,
                    classe_nome=nome,
                    origem_classe="metadado_djen",
                    confianca_classe=0.96,
                    grau=snapshot.grau if snapshot else None,
                    orgao_julgador=snapshot.orgao_nome if snapshot else None,
                    assunto_principal=snapshot.assunto_principal if snapshot else None,
                    datajud_desfecho_tpu=snapshot.desfecho_tpu if snapshot else None,
                    datajud_movimento_codigo=snapshot.movimento_tpu_codigo if snapshot else None,
                )

        # Camada 3: Extração Léxica / NER no cabeçalho da decisão (primeiros 900 caracteres)
        header = (text or "")[:900]
        # Verifica se há código explícito entre parênteses como "APELAÇÃO CÍVEL (198)" ou "PROCEDIMENTO COMUM CÍVEL (7)"
        m_header_decl = _EXPLICIT_HEADER_CLASSE_RE.search(header)
        if m_header_decl:
            decl_snippet = m_header_decl.group(1)
            m_code = _EXPLICIT_CODE_IN_PARENS_RE.search(decl_snippet)
            if m_code:
                code_val = int(m_code.group(1))
                if code_val in TPU_CLASSES_CNJ:
                    return ClasseProcessualResult(
                        classe_codigo=code_val,
                        classe_nome=TPU_CLASSES_CNJ[code_val],
                        origem_classe="cabecalho_ner",
                        confianca_classe=0.96,
                        grau=snapshot.grau if snapshot else None,
                        orgao_julgador=snapshot.orgao_nome if snapshot else None,
                        assunto_principal=snapshot.assunto_principal if snapshot else None,
                        datajud_desfecho_tpu=snapshot.desfecho_tpu if snapshot else None,
                        datajud_movimento_codigo=snapshot.movimento_tpu_codigo
                        if snapshot
                        else None,
                    )
            matched_decl = self._match_lexical(decl_snippet)
            if matched_decl:
                cod, nome = matched_decl
                return ClasseProcessualResult(
                    classe_codigo=cod,
                    classe_nome=nome,
                    origem_classe="cabecalho_ner",
                    confianca_classe=0.94,
                    grau=snapshot.grau if snapshot else None,
                    orgao_julgador=snapshot.orgao_nome if snapshot else None,
                    assunto_principal=snapshot.assunto_principal if snapshot else None,
                    datajud_desfecho_tpu=snapshot.desfecho_tpu if snapshot else None,
                    datajud_movimento_codigo=snapshot.movimento_tpu_codigo if snapshot else None,
                )

        matched_header = self._match_lexical(header)
        if matched_header:
            cod, nome = matched_header
            return ClasseProcessualResult(
                classe_codigo=cod,
                classe_nome=nome,
                origem_classe="cabecalho_ner",
                confianca_classe=0.91,
                grau=snapshot.grau if snapshot else None,
                orgao_julgador=snapshot.orgao_nome if snapshot else None,
                assunto_principal=snapshot.assunto_principal if snapshot else None,
                datajud_desfecho_tpu=snapshot.desfecho_tpu if snapshot else None,
                datajud_movimento_codigo=snapshot.movimento_tpu_codigo if snapshot else None,
            )

        # Camada 4: Inferência a partir da espécie especializada / órgão julgador
        inferred_cod, inferred_nome = self._infer_from_taxonomy(
            header=header,
            especie_ato=especie_ato or "",
            macro_categoria=macro_categoria or "",
        )
        return ClasseProcessualResult(
            classe_codigo=inferred_cod,
            classe_nome=inferred_nome,
            origem_classe="inferencia_taxonomia",
            confianca_classe=0.78 if inferred_cod is not None else 0.50,
            grau=snapshot.grau if snapshot else None,
            orgao_julgador=snapshot.orgao_nome if snapshot else None,
            assunto_principal=snapshot.assunto_principal if snapshot else None,
            datajud_desfecho_tpu=snapshot.desfecho_tpu if snapshot else None,
            datajud_movimento_codigo=snapshot.movimento_tpu_codigo if snapshot else None,
        )

    @staticmethod
    def _match_lexical(snippet: str) -> tuple[int, str] | None:
        if not snippet:
            return None
        for pattern, code, name in _LEXICAL_CLASS_PATTERNS:
            if pattern.search(snippet):
                return code, name
        return None

    @staticmethod
    def _infer_from_taxonomy(
        header: str, especie_ato: str, macro_categoria: str
    ) -> tuple[int | None, str]:
        norm_header = (
            unicodedata.normalize("NFKD", header).encode("ascii", "ignore").decode("ascii").lower()
        )
        esp = especie_ato.upper()
        macro = macro_categoria.upper()

        if esp == "ACORDAO_APELACAO":
            if "criminal" in norm_header or "penal" in norm_header:
                return 417, TPU_CLASSES_CNJ[417]
            return 198, TPU_CLASSES_CNJ[198]
        if esp == "ACORDAO_AGRAVO_INSTRUMENTO":
            return 202, TPU_CLASSES_CNJ[202]
        if esp == "ACORDAO_RECURSO_INOMINADO":
            return 460, TPU_CLASSES_CNJ[460]
        if esp == "ACORDAO_EMBARGOS_DECLARACAO":
            if "criminal" in norm_header or "penal" in norm_header:
                return 420, TPU_CLASSES_CNJ[420]
            return 1689, TPU_CLASSES_CNJ[1689]
        if esp == "SENTENCA_CUMPRIMENTO_SENTENCA":
            if "fazenda publica" in norm_header:
                return 12078, TPU_CLASSES_CNJ[12078]
            return 156, TPU_CLASSES_CNJ[156]
        if esp == "SENTENCA_HOMOLOGATORIA_LEIGA":
            if "fazenda publica" in norm_header:
                return 14695, TPU_CLASSES_CNJ[14695]
            return 436, TPU_CLASSES_CNJ[436]

        if "juizado especial da fazenda publica" in norm_header:
            return 14695, TPU_CLASSES_CNJ[14695]
        if "turma recursal" in norm_header:
            return 460, TPU_CLASSES_CNJ[460]
        if "juizado especial" in norm_header:
            return 436, TPU_CLASSES_CNJ[436]
        if "vara criminal" in norm_header or "juizo criminal" in norm_header:
            return 283, TPU_CLASSES_CNJ[283]
        if "execucao fiscal" in norm_header or "vara de execucoes fiscais" in norm_header:
            return 1116, TPU_CLASSES_CNJ[1116]

        if macro == "ACORDAO":
            return 198, TPU_CLASSES_CNJ[198]
        return 7, TPU_CLASSES_CNJ[7]
