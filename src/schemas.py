from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class ResultadoDecisao(str, Enum):
    PROCEDENTE = "procedente"
    IMPROCEDENTE = "improcedente"
    PARCIALMENTE_PROCEDENTE = "parcialmente_procedente"
    EXTINTO = "extinto"
    PROVIDO = "provido"
    NEGADO_PROVIMENTO = "negado_provimento"
    CONFIRMADA = "confirmada"
    REFORMADA = "reformada"
    ANULADA = "anulada"
    NAO_CONHECIDO = "nao_conhecido"
    PREJUDICADO = "prejudicado"
    # Fallback
    OUTRO = "outro"

class Decisao(BaseModel):
    """Representa uma decisão judicial extraída."""
    numero_processo: str = Field(..., description="O número CNJ do processo (formato NNNNNNN-NN.NNNN.N.NN.NNNN). Se não disponível, usar o número encontrado.")
    tipo_decisao: str = Field(..., description="Tipo da decisão, ex: 'acórdão', 'sentença', 'decisão monocrática'.")
    polo_ativo: List[str] = Field(default_factory=list, description="Lista de nomes das partes no polo ativo (autores, agravantes, recorrentes).")
    advogados_polo_ativo: List[str] = Field(default_factory=list, description="Lista de advogados do polo ativo com OAB se disponível.")
    polo_passivo: List[str] = Field(default_factory=list, description="Lista de nomes das partes no polo passivo (réus, agravados, recorridos).")
    advogados_polo_passivo: List[str] = Field(default_factory=list, description="Lista de advogados do polo passivo com OAB se disponível.")
    resultado: ResultadoDecisao = Field(..., description="O resultado da decisão/julgamento classificado.")
    data: Optional[str] = Field(None, description="Data da decisão no formato YYYY-MM-DD.")
    resumo: str = Field(..., description="Breve resumo da decisão (max 250 chars).")

class ExtractionResult(BaseModel):
    """Resultado da extração de decisões de um texto."""
    decisoes: List[Decisao] = Field(default_factory=list, description="Lista de decisões encontradas no texto.")
