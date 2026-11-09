"""Segmentador Híbrido de Dispositivo Judicial (Random Forest + Metadados DJEN + Anomaly Detection).

Substitui modelos neurais pesados de token classification (OPF 1.5B) por um classificador
tabular de altíssima eficiência (< 0.1 ms em CPU) enriquecido com metadados do DJEN
(juiz, partes, classe processual, data e tribunal) e detecção de anomalias com Isolation Forest.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np

from causaganha.decisoes.taxonomy import DocumentTaxonomyRegistry, MacroCategory

# Padrões canônicos de abertura de dispositivo
CANONICAL_ANCHORS = [
    r"\bante\s+(?:ao|o)\s+exposto\b",
    r"\bdiante\s+do\s+exposto\b",
    r"\bisto\s+posto\b",
    r"\bpelo\s+exposto\b",
    r"\b(?:d\s*e\s*c\s*i\s*d\s*o|decido)\b",
    r"\b(?:d\s*i\s*s\s*p\s*o\s*s\s*i\s*t\s*i\s*v\s*o|dispositivo)\b",
    r"\b(?:a\s*c\s*o\s*r\s*d\s*a\s*m|acordam)\b",
    r"\bvistos,\s*relatados\s*e\s*discutidos\b",
    r"\bjulgo\s+(?:procedente|improcedente|parcialmente|extinto)\b",
    r"\bhomologo\s+o\s+acordo\b",
    r"\bextingo\s+o\s+processo\b",
    r"\bconcedo\s+a\s+ordem\b",
    r"\bdenego\s+a\s+ordem\b",
    r"\bnão\s+conheço\b",
    r"\bdou\s+provimento\b",
    r"\bnego\s+provimento\b",
]

REGEX_ANCHORS = re.compile("|".join(CANONICAL_ANCHORS), re.IGNORECASE)

# Padrões de alerta de citação jurisprudencial (anti-falso positivo)
CITATION_WARNINGS = [
    r"\b(?:resp|recuso\s+especial)\b",
    r"\b(?:re\s+\d+|agr-re)\b",
    r"\bstj\b",
    r"\bstf\b",
    r"\bdje\b",
    r"\bprecedente(?:s)?\b",
    r"\bjurisprudência\b",
    r"\brelator(?:\(a\))?\b",
    r"\bementa\b",
    r"\bsúmula\b",
]

REGEX_CITATIONS = re.compile("|".join(CITATION_WARNINGS), re.IGNORECASE)


def normalize_str(s: Any) -> str:
    if s is None or not isinstance(s, str):
        return ""
    normalized = unicodedata.normalize("NFKD", s)
    return "".join(c for c in normalized if not unicodedata.combining(c)).lower().strip()


def clean_header_name(s: str) -> str:
    s = re.split(r"(?i)\b(?:defensor|advogad|data|origem|comarca|vara|foro|cnpj|cpf)\b", s)[0]
    s = s.strip(" .-:\t\r\n")
    if any(w in s.lower() for w in ["alega", "requer", "sustenta", "ajuiz", "afirma"]):
        return ""
    return s[:60]


@dataclass
class DispositifResult:
    start: int
    end: int
    snippet: str
    confidence: float
    is_anomaly: bool
    fallback_used: bool
    metadata_used: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "snippet": self.snippet,
            "char_count": len(self.snippet),
            "confidence": round(self.confidence, 4),
            "is_anomaly": self.is_anomaly,
            "fallback_used": self.fallback_used,
            "metadata_used": self.metadata_used,
        }


class HybridDispositifSegmenter:
    """Classificador leve de parágrafos/sentenças para recorte cirúrgico do Dispositivo."""

    FEATURE_NAMES = [
        "pos_relativa",
        "char_len",
        "dist_to_end_ratio",
        "has_canonical_anchor",
        "has_citation_warning",
        "has_judge_signature",
        "has_plaintiff_mention",
        "has_defendant_mention",
        "is_upper_heading",
        "classe_is_execucao",
        "classe_is_recurso",
        "classe_is_hc",
        "ano_pos_2020",
        "is_macro_acordao",
        "is_macro_sentenca",
        "is_macro_interlocutoria",
        "is_macro_edital",
        "is_macro_comunicacao",
        "is_macro_cartorio",
        "is_spec_homologatoria",
        "is_spec_liminar_urgencia",
        "has_urgencia_tag",
    ]

    def __init__(
        self,
        model_path: str | Path | None = None,
        taxonomy_registry: DocumentTaxonomyRegistry | None = None,
    ):
        self.rf_model = None
        self.isolation_forest = None
        self.is_fitted = False
        self.taxonomy_registry = taxonomy_registry or DocumentTaxonomyRegistry()

        if model_path and Path(model_path).exists():
            self.load(model_path)

    @staticmethod
    def extract_header_metadata(text: str) -> dict[str, str]:
        """Extrai metadados do cabeçalho caso não tenham sido fornecidos pelo DJEN."""
        header = text[:1200]
        # Normaliza pontuação de quebra para suportar texto contínuo do DJEN
        header_lines = header.replace(". ", "\n")
        meta: dict[str, str] = {}

        # Juiz / Relator
        m_rel = re.search(
            r"\b(?:relator(?:a)?|juiz(?:a)?(?:\s+de\s+direito)?)\s*[:]\s*([^\n\r]+)",
            header_lines,
            re.IGNORECASE,
        )
        if m_rel:
            name = clean_header_name(m_rel.group(1))
            if name:
                meta["judge_name"] = name

        # Autor / Apelante / Requerente
        m_aut = re.search(
            r"\b(?:apelante|autor(?:a)?|requerente|exequente|embargante|agravante)\s*[:]\s*([^\n\r]+)",
            header_lines,
            re.IGNORECASE,
        )
        if m_aut:
            name = clean_header_name(m_aut.group(1))
            if name:
                meta["polo_ativo"] = name

        # Réu / Apelado / Requerido
        m_reu = re.search(
            r"\b(?:apelad[oa]|r[eé]u|requerid[oa]|executad[oa]|embargad[oa]|agravad[oa])\s*[:]\s*([^\n\r]+)",
            header_lines,
            re.IGNORECASE,
        )
        if m_reu:
            name = clean_header_name(m_reu.group(1))
            if name:
                meta["polo_passivo"] = name

        # Classe processual
        m_classe = re.search(
            r"\b(apelação(?:\s+cível|\s+criminal)?|habeas\s+corpus|cumprimento\s+de\s+sentença|execução\s+fiscal|procedimento\s+comum|agravo\s+de\s+instrumento)\b",
            header,
            re.IGNORECASE,
        )
        if m_classe:
            meta["classe_processual"] = m_classe.group(1).strip()

        # Ano
        m_ano = re.search(r"\b20(1[5-9]|2[0-9])\b", header)
        if m_ano:
            meta["ano"] = m_ano.group(0)

        return meta

    def extract_features(
        self,
        paragraph: str,
        para_idx: int,
        total_paras: int,
        char_offset: int,
        total_chars: int,
        metadata: dict[str, Any] | None = None,
    ) -> list[float]:
        meta = metadata or {}
        p_norm = normalize_str(paragraph)

        # 1. Posição relativa e tamanho
        pos_rel = para_idx / max(total_paras - 1, 1)
        char_len = len(paragraph)
        dist_to_end_ratio = (total_chars - (char_offset + char_len)) / max(total_chars, 1)

        # 2. Âncoras e Citações
        has_anchor = 1.0 if REGEX_ANCHORS.search(paragraph) else 0.0
        has_cit = 1.0 if REGEX_CITATIONS.search(paragraph) else 0.0

        # 3. Metadados DJEN
        judge_norm = normalize_str(meta.get("judge_name"))
        has_judge = 1.0 if judge_norm and len(judge_norm) > 3 and judge_norm in p_norm else 0.0

        autor_norm = normalize_str(meta.get("polo_ativo") or meta.get("requerente"))
        has_autor = 1.0 if autor_norm and len(autor_norm) > 3 and autor_norm in p_norm else 0.0

        reu_norm = normalize_str(meta.get("polo_passivo") or meta.get("requerido"))
        has_reu = 1.0 if reu_norm and len(reu_norm) > 3 and reu_norm in p_norm else 0.0

        # 4. Formatação de título/caixa alta
        is_upper = 1.0 if paragraph[:40].isupper() and len(paragraph) > 5 else 0.0

        # 5. Metadados de Classe e Temporal
        classe_norm = normalize_str(meta.get("classe_processual"))
        is_exec = 1.0 if "execu" in classe_norm or "cumprimento" in classe_norm else 0.0
        is_rec = 1.0 if "apelac" in classe_norm or "agravo" in classe_norm or "recurso" in classe_norm else 0.0
        is_hc = 1.0 if "habeas corpus" in classe_norm else 0.0

        ano = 2026
        date_str = str(
            meta.get("ano")
            or meta.get("validated_at")
            or meta.get("data_decisao")
            or meta.get("data_disponibilizacao")
            or ""
        )
        m_ano = re.search(r"\b20(1[5-9]|2[0-9])\b", date_str)
        if m_ano:
            ano = int(m_ano.group(0))
        ano_pos_2020 = 1.0 if ano >= 2020 else 0.0

        # 6. Metadados de Taxonomia Especializada (DJEN / Topologia Especializada)
        tax_res = meta.get("taxonomy_classification")
        if tax_res is None:
            full_context = meta.get("full_text") or paragraph
            tax_res = self.taxonomy_registry.classify(full_context, meta)

        macro = getattr(tax_res, "macro_category", None)
        macro_val = macro.value if hasattr(macro, "value") else str(macro)
        spec = str(getattr(tax_res, "specific_category", ""))
        tags = getattr(tax_res, "tags", []) or []

        is_macro_acordao = 1.0 if macro_val == "ACORDAO" else 0.0
        is_macro_sentenca = 1.0 if macro_val == "SENTENCA" else 0.0
        is_macro_interlocutoria = 1.0 if macro_val == "DECISAO_INTERLOCUTORIA" else 0.0
        is_macro_edital = 1.0 if macro_val == "EDITAL" else 0.0
        is_macro_comunicacao = 1.0 if macro_val == "PUBLICACAO_COMUNICACAO" else 0.0
        is_macro_cartorio = 1.0 if macro_val == "ATO_CARTORARIO" else 0.0

        is_spec_homologatoria = 1.0 if "HOMOLOGATORIA" in spec else 0.0
        is_spec_liminar_urgencia = 1.0 if ("TUTELA_URGENCIA" in spec or "LIMINAR" in spec) else 0.0
        has_urgencia_tag = 1.0 if "urgencia" in tags else 0.0

        return [
            pos_rel,
            float(char_len),
            dist_to_end_ratio,
            has_anchor,
            has_cit,
            has_judge,
            has_autor,
            has_reu,
            is_upper,
            is_exec,
            is_rec,
            is_hc,
            ano_pos_2020,
            is_macro_acordao,
            is_macro_sentenca,
            is_macro_interlocutoria,
            is_macro_edital,
            is_macro_comunicacao,
            is_macro_cartorio,
            is_spec_homologatoria,
            is_spec_liminar_urgencia,
            has_urgencia_tag,
        ]

    def _rule_based_score(self, feats: list[float]) -> float:
        """Árvore de decisão em código para garantir fallback imediato com 100% de disponibilidade."""
        pos_rel = feats[0]
        has_anchor = feats[3]
        has_cit = feats[4]
        has_judge = feats[5]

        if pos_rel < 0.40:
            return 0.05

        score = 0.3 + (pos_rel * 0.4)
        if has_anchor:
            score += 0.35
        if has_cit:
            score -= 0.40
        if has_judge:
            score -= 0.10

        return max(min(score, 1.0), 0.0)

    @staticmethod
    def split_document_units(text: str) -> list[dict[str, Any]]:
        """Divide o documento em unidades estruturais (parágrafos se houver, ou sentenças/períodos no texto plano do DJEN)."""
        if text.count("\n") >= 3:
            matches = list(re.finditer(r"[^\n]+(?:\n|$)", text))
        else:
            matches = list(re.finditer(r"[^.!?\n]+(?:[.!?\n]+|\s*$)", text))

        units = []
        for m in matches:
            content = m.group(0).strip()
            if content:
                units.append({"text": content, "start": m.start(), "end": m.end()})
        if not units:
            units = [{"text": text.strip(), "start": 0, "end": len(text)}]
        return units

    def predict(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        max_snippet_chars: int = 2500,
    ) -> DispositifResult:
        """Recorta o dispositivo e valida integridade estrutural."""
        meta = dict(metadata or {})

        # Autocompleta metadados se faltantes
        if not meta.get("judge_name") or not meta.get("polo_ativo") or not meta.get("classe_processual"):
            extracted = self.extract_header_metadata(text)
            for k, v in extracted.items():
                if k not in meta or not meta[k]:
                    meta[k] = v

        # Classifica a taxonomia especializada uma única vez para o documento
        if "taxonomy_classification" not in meta:
            tax_res = self.taxonomy_registry.classify(text, meta)
            meta["taxonomy_classification"] = tax_res
            meta["taxonomy"] = tax_res.to_dict()

        n_total = len(text)
        if n_total <= 350:
            snippet = text.strip()
            if len(snippet) > max_snippet_chars:
                snippet = snippet[-max_snippet_chars:]
            return DispositifResult(
                start=max(0, n_total - len(snippet)),
                end=n_total,
                snippet=snippet,
                confidence=1.0,
                is_anomaly=False,
                fallback_used=False,
                metadata_used=meta,
            )

        # 1. Quebra em unidades estruturais preservando offsets exatos
        paras_info = self.split_document_units(text)
        total_paras = len(paras_info)
        features_list = []

        for idx, u in enumerate(paras_info):
            feats = self.extract_features(
                paragraph=u["text"],
                para_idx=idx,
                total_paras=total_paras,
                char_offset=u["start"],
                total_chars=n_total,
                metadata=meta,
            )
            features_list.append(feats)

        X = np.array(features_list)

        # 2. Avaliação de Anomalia via Isolation Forest
        is_anomaly = False
        if self.isolation_forest is not None:
            doc_profile = np.mean(X, axis=0, keepdims=True)
            iso_pred = self.isolation_forest.predict(doc_profile)
            is_anomaly = bool(iso_pred[0] == -1)

        # 3. Predição de probabilidade de Dispositivo
        if self.is_fitted and self.rf_model is not None:
            raw_probs = self.rf_model.predict_proba(X)[:, 1]
        else:
            raw_probs = np.array([self._rule_based_score(f) for f in features_list])

        # Enriquecimento híbrido com âncoras canônicas e penalidades de jurisprudência
        probs_list = []
        for idx_f, f in enumerate(features_list):
            p = float(raw_probs[idx_f])
            if f[3] > 0.5:  # has_canonical_anchor
                p = min(1.0, p + 0.40)
            if f[4] > 0.5:  # has_citation_warning
                p = max(0.0, p - 0.40)
            probs_list.append(p)
        probs = np.array(probs_list)

        # 4. Seleção do parágrafo de abertura do dispositivo
        min_para_idx = int(total_paras * 0.40) if total_paras > 4 else 0
        candidate_probs = probs[min_para_idx:]
        if len(candidate_probs) == 0:
            candidate_probs = probs
            min_para_idx = 0

        best_sub_idx = int(np.argmax(candidate_probs))
        start_para_idx = min_para_idx + best_sub_idx
        best_prob = float(probs[start_para_idx])

        # 5. Encontra o fim do dispositivo
        start_char = paras_info[start_para_idx]["start"]
        end_char = n_total
        fallback = False

        if best_prob < 0.35:
            # Fallback seguro para janela final de 2.000 caracteres
            fallback = True
            start_char = max(0, n_total - 2000)
            end_char = n_total
        else:
            # Varre parágrafos subsequentes procurando assinatura do juiz para recortar encerramento
            judge_norm = normalize_str(meta.get("judge_name"))
            for p_idx in range(start_para_idx + 1, total_paras):
                p_text_norm = normalize_str(paras_info[p_idx]["text"])
                if judge_norm and len(judge_norm) > 3 and judge_norm in p_text_norm:
                    end_char = paras_info[p_idx]["end"]
                    break

        # Limite máximo de segurança
        if (end_char - start_char) > max_snippet_chars:
            end_char = start_char + max_snippet_chars

        snippet = text[start_char:end_char].strip()

        return DispositifResult(
            start=start_char,
            end=end_char,
            snippet=snippet,
            confidence=best_prob,
            is_anomaly=is_anomaly,
            fallback_used=fallback,
            metadata_used=meta,
        )

    def fit(self, X: np.ndarray, y: np.ndarray, doc_profiles: np.ndarray | None = None) -> None:
        """Treina a Random Forest e a Isolation Forest."""
        from sklearn.ensemble import IsolationForest, RandomForestClassifier

        self.rf_model = RandomForestClassifier(
            n_estimators=120,
            max_depth=6,
            min_samples_split=4,
            class_weight="balanced",
            random_state=42,
        )
        self.rf_model.fit(X, y)

        self.isolation_forest = IsolationForest(
            contamination=0.08,
            random_state=42,
        )
        fit_iso_data = doc_profiles if doc_profiles is not None and len(doc_profiles) > 0 else X
        self.isolation_forest.fit(fit_iso_data)
        self.is_fitted = True

    def save(self, filepath: str | Path) -> None:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "rf_model": self.rf_model,
                "isolation_forest": self.isolation_forest,
                "is_fitted": self.is_fitted,
            },
            filepath,
        )

    def load(self, filepath: str | Path) -> None:
        data = joblib.load(filepath)
        self.rf_model = data["rf_model"]
        self.isolation_forest = data["isolation_forest"]
        self.is_fitted = data["is_fitted"]
