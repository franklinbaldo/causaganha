"""Modelos de dados estruturados para Entidades e Menções Judiciais (Judicial NER)."""

from __future__ import annotations

import enum
from dataclasses import asdict, dataclass
from typing import Any


class EntityType(str, enum.Enum):
    """Categorias canônicas de entidades em documentos jurídicos."""

    CNJ = "CNJ"
    NORMA = "NORMA"
    VALOR = "VALOR"
    DATA = "DATA"
    ORGANIZACAO = "ORGANIZACAO"
    PESSOA = "PESSOA"
    OAB = "OAB"
    ENDERECO = "ENDERECO"


class EntityRole(str, enum.Enum):
    """Papéis semânticos e contextuais atribuídos a cada entidade no processo."""

    # Processos
    PROCESSO_PRINCIPAL = "PROCESSO_PRINCIPAL"
    PROCESSO_CITADO = "PROCESSO_CITADO"
    PROCESSO_PARADIGMA = "PROCESSO_PARADIGMA"

    # Normas
    DISPOSITIVO_LEGAL_APLICADO = "DISPOSITIVO_LEGAL_APLICADO"
    RATIO_DECIDENDI = "RATIO_DECIDENDI"
    TESE_ALEGADA = "TESE_ALEGADA"
    REFERENCIA_NORMATIVA = "REFERENCIA_NORMATIVA"

    # Valores
    VALOR_CONDENACAO_PRINCIPAL = "VALOR_CONDENACAO_PRINCIPAL"
    VALOR_DA_CAUSA = "VALOR_DA_CAUSA"
    VALOR_HONORARIOS = "VALOR_HONORARIOS"
    VALOR_ASTREINTES_MULTA = "VALOR_ASTREINTES_MULTA"
    PERCENTUAL_SUCUMBENCIA = "PERCENTUAL_SUCUMBENCIA"
    VALOR_MENCIONADO = "VALOR_MENCIONADO"

    # Datas
    DATA_PUBLICACAO = "DATA_PUBLICACAO"
    DATA_JULGAMENTO = "DATA_JULGAMENTO"
    DATA_FATO = "DATA_FATO"
    PRAZO_MANIFESTACAO = "PRAZO_MANIFESTACAO"
    DATA_GENERICA = "DATA_GENERICA"

    # Pessoas e Sujeitos
    POLO_ATIVO = "POLO_ATIVO"
    POLO_PASSIVO = "POLO_PASSIVO"
    MAGISTRADO = "MAGISTRADO"
    ADVOGADO = "ADVOGADO"
    TESTEMUNHA = "TESTEMUNHA"
    TERCEIRO_CITADO = "TERCEIRO_CITADO"

    # Organizações
    ORGAO_JULGADOR = "ORGAO_JULGADOR"
    PARTE_PJ = "PARTE_PJ"
    INSTITUICAO_FINANCEIRA = "INSTITUICAO_FINANCEIRA"
    EMPRESA_SERVICO_PUBLICO = "EMPRESA_SERVICO_PUBLICO"
    ORGAO_PUBLICO = "ORGAO_PUBLICO"

    PAPEL_GENERICO = "PAPEL_GENERICO"


@dataclass
class NormaRef:
    diploma: str  # ex: "CPC", "CC", "CF", "CDC", "CLT", "LEI_ESPECIFICA", "PENDENTE_CONTEXTO"
    artigo: str  # ex: "485", "5º", "186"
    paragrafo: str | None = None  # ex: "1º", "único"
    inciso: str | None = None  # ex: "VI", "I", "II"
    alinea: str | None = None  # ex: "a", "b"
    lei_ano: str | None = None  # ex: "Lei 13.105/2015"
    raw_reference: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def canonical_string(self) -> str:
        parts = [f"art. {self.artigo}"]
        if self.paragrafo:
            parts.append(f"§ {self.paragrafo}")
        if self.inciso:
            parts.append(f"inc. {self.inciso}")
        if self.alinea:
            parts.append(f"alínea '{self.alinea}'")
        if self.diploma and self.diploma != "PENDENTE_CONTEXTO":
            parts.append(f"do {self.diploma}")
        return " ".join(parts)


@dataclass
class MoneyValue:
    amount: float
    currency: str = "BRL"
    is_percentage: bool = False
    raw_text: str = ""
    qualifier: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CnjValue:
    numero_formatado: str  # NNNNNNN-DD.AAAA.J.TR.OOOO
    sequencial: str
    digito_verificador: str
    ano: int
    ramo_justica: int
    tribunal: int
    origem: str
    is_valid_mod97: bool

    @property
    def numero_limpo(self) -> str:
        import re

        return re.sub(r"\D", "", self.numero_formatado)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DateValue:
    iso_date: str | None  # YYYY-MM-DD
    year: int | None
    month: int | None
    day: int | None
    is_deadline: bool = False
    deadline_days: int | None = None
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PersonValue:
    nome: str
    cpf_cnpj: str | None = None
    polo: str | None = None  # "ATIVO", "PASSIVO", "TERCEIRO", "MAGISTRADO", "ADVOGADO"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OabValue:
    uf: str  # ex: "RO", "SP"
    numero: str  # ex: "1234", "12345"
    tipo_inscricao: str | None = None  # ex: "A", "E", "B"
    nome_advogado: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def formatado(self) -> str:
        return f"OAB/{self.uf.upper()} {self.numero}"


@dataclass
class JudicialMention:
    literal: str
    start: int
    end: int
    section: str  # SectionType string (ex: "DISPOSITIVO", "CABECALHO")
    entity_type: EntityType
    normalized_value: Any
    role: EntityRole
    confidence: float
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        norm = self.normalized_value
        if hasattr(norm, "to_dict"):
            norm_dict = norm.to_dict()
        elif isinstance(norm, (dict, list, str, int, float, bool, type(None))):
            norm_dict = norm
        else:
            norm_dict = str(norm)

        return {
            "literal": self.literal,
            "start": self.start,
            "end": self.end,
            "char_count": len(self.literal),
            "section": self.section,
            "entity_type": self.entity_type.value,
            "normalized_value": norm_dict,
            "role": self.role.value,
            "confidence": round(self.confidence, 4),
            "evidence": self.evidence,
        }
