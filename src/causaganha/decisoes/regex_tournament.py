"""Torneio Competitivo de Regexes (Regex Tournament & Leaderboard).

Implementa a dinâmica de seleção natural e ranqueamento de expressões regulares:
- Cada regex candidata é testada contra o acervo real.
- Acertos (True Positives) somam pontos.
- Falsos Positivos (False Positives) recebem penalidade severa (FP Penalty).
- Para cada categoria processual, apenas o Top-K de regexes promovidas é utilizado em produção.
- Regexes que acumulam falsos positivos são automaticamente rebaixadas (DEMOTED).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

# Pesos canônicos por seção estrutural do documento judicial
DEFAULT_SECTION_WEIGHTS: dict[str, float] = {
    "dispositivo": 3.0,
    "ementa": 1.5,
    "voto": 1.2,
    "fundamentacao": 0.6,
    "relatorio": 0.2,
    "cabecalho": 0.1,
    "encerramento": 0.5,
    "full": 1.0,
}

# Prioridade de especificidade jurídica para desempate entre categorias
SPECIFICITY_PRIORITY: dict[str, int] = {
    "acordo": 10,
    "parcialmente procedente": 8,
    "extinto sem mérito": 7,
    "procedente": 5,
    "improcedente": 5,
}


@dataclass
class MatchCandidate:
    """Evidência de correspondência encontrada por uma regra do torneio."""

    category: str
    rule: CompetitiveRegex
    section: str
    weight: float
    effective_score: float
    confidence: float
    matched_snippet: str = ""


@dataclass
class ClassificationExplanation:
    """Explicação detalhada do resultado competitivo da classificação."""

    category: str
    confidence: float
    winning_rule: CompetitiveRegex | None
    winning_section: str | None
    effective_score: float
    all_candidates: list[dict[str, Any]] = field(default_factory=list)


class CompetitiveRegex:
    """Expressão regular individual que compete no torneio de sua categoria."""

    def __init__(
        self,
        pattern_id: str,
        pattern: str,
        category: str,
        source: str = "seed",
        description: str = "",
        fp_penalty: float = 3.0,
        negative_pattern: str | None = None,
        scope: str = "all",
    ):
        self.pattern_id = pattern_id
        self.pattern = pattern
        self.category = category.lower().strip()
        self.source = source
        self.description = description
        self.fp_penalty = fp_penalty
        self.negative_pattern = negative_pattern
        self.scope = scope.lower().strip()

        self.tp: int = 0
        self.fp: int = 0
        self.fn: int = 0
        self.total_tested: int = 0
        self.precision: float = 0.0
        self.recall: float = 0.0
        self.score: float = 0.0
        self.status: str = "CANDIDATE"  # CANDIDATE, PROMOTED, DEMOTED

        self._compiled: re.Pattern[str] | None = None
        self._negative_compiled: re.Pattern[str] | None = None

    @property
    def compiled(self) -> re.Pattern[str]:
        if self._compiled is None:
            self._compiled = re.compile(self.pattern, re.IGNORECASE)
        return self._compiled

    @property
    def negative_compiled(self) -> re.Pattern[str] | None:
        if self.negative_pattern and self._negative_compiled is None:
            self._negative_compiled = re.compile(self.negative_pattern, re.IGNORECASE)
        return self._negative_compiled

    def matches(self, text: str, section: str | None = None) -> bool:
        """Verifica se o padrão tem match no texto, respeitando escopo e guardas negativas."""
        if not text:
            return False
        if self.scope != "all" and section is not None and section.lower() != self.scope:
            return False

        if not self.negative_compiled:
            return bool(self.compiled.search(text))

        # Com negative guard: valida se ao menos um match não está contaminado
        for m in self.compiled.finditer(text):
            # Janela de contexto local ao redor do match (100 caracteres antes e depois)
            start_window = max(0, m.start() - 100)
            end_window = min(len(text), m.end() + 100)
            context = text[start_window:end_window]

            if not self.negative_compiled.search(context):
                return True

        return False

    def update_metrics(self, tp: int, fp: int, total_positives_in_dataset: int) -> None:
        """Atualiza estatísticas, penalização e pontuação competitiva."""
        self.tp = tp
        self.fp = fp
        self.fn = max(0, total_positives_in_dataset - tp)
        self.total_tested = tp + fp

        # 1. Precisão: penaliza severamente falso positivo
        if (tp + fp) > 0:
            self.precision = round(tp / (tp + fp), 4)
        else:
            self.precision = 0.0

        # 2. Recall: proporção de casos da categoria capturados
        if total_positives_in_dataset > 0:
            self.recall = round(tp / total_positives_in_dataset, 4)
        else:
            self.recall = 0.0

        # 3. Score Competitivo com penalidade estrita de FP:
        # Recompensa True Positives líquidos ponderados pela Precisão:
        # Score = (TP - fp_penalty * FP) * Precision * 10.0
        # Se os falsos positivos superarem a margem de segurança, o score despenca para negativo.
        net_tp = float(tp) - (self.fp_penalty * float(fp))
        if net_tp > 0 and self.precision >= 0.70:
            self.score = round(net_tp * self.precision * 10.0, 2)
            self.status = "PROMOTED"
        elif net_tp <= 0 or self.precision < 0.60:
            self.score = round(min(net_tp * 5.0, -1.0) if fp > 0 else 0.0, 2)
            self.status = "DEMOTED"
        else:
            self.score = round(net_tp * self.precision * 5.0, 2)
            self.status = "CANDIDATE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "pattern": self.pattern,
            "category": self.category,
            "source": self.source,
            "description": self.description,
            "negative_pattern": self.negative_pattern,
            "scope": self.scope,
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "precision": self.precision,
            "recall": self.recall,
            "score": self.score,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompetitiveRegex:
        r = cls(
            pattern_id=data["pattern_id"],
            pattern=data["pattern"],
            category=data["category"],
            source=data.get("source", "seed"),
            description=data.get("description", ""),
            fp_penalty=data.get("fp_penalty", 3.0),
            negative_pattern=data.get("negative_pattern"),
            scope=data.get("scope", "all"),
        )
        r.tp = data.get("tp", 0)
        r.fp = data.get("fp", 0)
        r.fn = data.get("fn", 0)
        r.precision = data.get("precision", 0.0)
        r.recall = data.get("recall", 0.0)
        r.score = data.get("score", 0.0)
        r.status = data.get("status", "CANDIDATE")
        return r


class RegexTournament:
    """Orquestrador do torneio: gerencia pools por categoria e seleciona o Top-K."""

    def __init__(
        self,
        top_k: int = 3,
        fp_penalty: float = 2.0,
        min_precision: float = 0.75,
    ):
        self.top_k = top_k
        self.fp_penalty = fp_penalty
        self.min_precision = min_precision
        self.categories: dict[str, list[CompetitiveRegex]] = {}

    def register(
        self,
        pattern: str,
        category: str,
        pattern_id: str | None = None,
        source: str = "seed",
        description: str = "",
        negative_pattern: str | None = None,
        scope: str = "all",
    ) -> CompetitiveRegex:
        """Registra uma nova regex candidata no pool de sua categoria."""
        cat = category.lower().strip()
        if cat not in self.categories:
            self.categories[cat] = []

        # Evita duplicidade de padrão
        for existing in self.categories[cat]:
            if existing.pattern == pattern and existing.negative_pattern == negative_pattern:
                return existing

        pid = (
            pattern_id
            or f"{cat}_{len(self.categories[cat]) + 1}_{re.sub(r'[^a-zA-Z0-9]', '', pattern)[:16]}"
        )
        reg = CompetitiveRegex(
            pattern_id=pid,
            pattern=pattern,
            category=cat,
            source=source,
            description=description,
            fp_penalty=self.fp_penalty,
            negative_pattern=negative_pattern,
            scope=scope,
        )
        self.categories[cat].append(reg)
        return reg

    def evaluate_tournament(
        self,
        dataset: list[dict[str, Any]],
        text_key: str = "texto",
        label_key: str = "desfecho_cpc",
    ) -> dict[str, Any]:
        """Executa a rodada completa do torneio avaliando todas as regexes contra os documentos."""
        # 1. Contagem de casos reais por categoria no dataset
        cat_totals: dict[str, int] = {}
        for doc in dataset:
            lbl = str(doc.get(label_key, "")).lower().strip()
            cat_totals[lbl] = cat_totals.get(lbl, 0) + 1

        leaderboard_summary: dict[str, list[dict[str, Any]]] = {}

        # 2. Avalia cada regex em cada categoria
        for cat, regex_list in self.categories.items():
            total_real_positives = cat_totals.get(cat, 0)

            for reg in regex_list:
                tp = 0
                fp = 0

                for doc in dataset:
                    doc_text = doc.get(text_key, "")
                    doc_label = str(doc.get(label_key, "")).lower().strip()
                    if not doc_text:
                        continue

                    # Se deu match
                    if reg.matches(doc_text):
                        if doc_label == cat:
                            tp += 1
                        else:
                            # Deu match mas a decisão tinha outro resultado (falso positivo!)
                            fp += 1

                reg.update_metrics(tp, fp, total_real_positives)

            # 3. Ranqueia por score decrescente
            regex_list.sort(key=lambda r: (r.score, r.precision, r.tp), reverse=True)

            # Atualiza status dos Top-K
            promoted_count = 0
            for r in regex_list:
                if r.status == "PROMOTED" and promoted_count < self.top_k:
                    promoted_count += 1
                elif r.status == "PROMOTED":
                    r.status = "CANDIDATE"  # Bom score mas fora do Top-K ativo

            leaderboard_summary[cat] = [r.to_dict() for r in regex_list]

        return {
            "total_documents_tested": len(dataset),
            "category_distribution": cat_totals,
            "leaderboard": leaderboard_summary,
        }

    def get_top_k(self, category: str) -> list[CompetitiveRegex]:
        """Retorna apenas as melhores regexes promovidas para a categoria."""
        cat = category.lower().strip()
        pool = self.categories.get(cat, [])
        promoted = [r for r in pool if r.status == "PROMOTED" and r.precision >= self.min_precision]
        if not promoted:
            # Fallback para as melhores candidatas se ainda nenhuma atingiu o critério estrito
            promoted = [r for r in pool if r.score > 0]
        return promoted[: self.top_k]

    def classify_with_explanation(
        self,
        text: str,
        sections: dict[str, str] | None = None,
        section_weights: dict[str, float] | None = None,
    ) -> ClassificationExplanation:
        """Classifica ponderando as evidências de cada seção e desempata por especificidade."""
        weights = dict(DEFAULT_SECTION_WEIGHTS)
        if section_weights:
            weights.update(section_weights)

        # Se sections não foi fornecido diretamente, avalia o texto integral como "full"
        eval_sections: dict[str, str] = dict(sections) if sections else {"full": text}

        candidates: list[MatchCandidate] = []

        for cat, _ in self.categories.items():
            top_rules = self.get_top_k(cat)
            for r in top_rules:
                # Testa contra cada seção avaliável
                for sec_name, sec_text in eval_sections.items():
                    if not sec_text:
                        continue
                    if r.matches(sec_text, section=sec_name):
                        weight = weights.get(sec_name.lower(), 1.0)
                        # Score base histórico ponderado pelo peso da seção
                        base_score = max(
                            r.score, (r.precision * 100.0) if r.precision > 0 else 10.0
                        )
                        effective_score = round(base_score * weight, 2)

                        # Confiança proporcional à precisão histórica e peso da seção
                        section_conf_factor = 1.0 if weight >= 1.0 else 0.75
                        conf = round(min(0.99, max(0.50, r.precision * section_conf_factor)), 4)

                        candidates.append(
                            MatchCandidate(
                                category=cat,
                                rule=r,
                                section=sec_name,
                                weight=weight,
                                effective_score=effective_score,
                                confidence=conf,
                                matched_snippet=sec_text[:120],
                            )
                        )
                        # Encontrou o melhor match da categoria nesta seção, avança
                        break

        if not candidates:
            return ClassificationExplanation(
                category="unknown",
                confidence=0.0,
                winning_rule=None,
                winning_section=None,
                effective_score=0.0,
                all_candidates=[],
            )

        # Ordena candidatos por pontuação efetiva decrescente
        candidates.sort(
            key=lambda c: (
                c.effective_score,
                SPECIFICITY_PRIORITY.get(c.category, 5),
                c.confidence,
            ),
            reverse=True,
        )

        # Desempate por especificidade jurídica: se as duas melhores categorias têm scores muito próximos (<= 15%),
        # a categoria juridicamente mais específica (ex: PARCIALMENTE PROCEDENTE sobre PROCEDENTE) prevalece
        if len(candidates) >= 2:
            top1 = candidates[0]
            top2 = candidates[1]
            if top1.category != top2.category and top1.effective_score > 0:
                diff_ratio = abs(top1.effective_score - top2.effective_score) / top1.effective_score
                if diff_ratio <= 0.15:
                    p1 = SPECIFICITY_PRIORITY.get(top1.category, 5)
                    p2 = SPECIFICITY_PRIORITY.get(top2.category, 5)
                    if p2 > p1:
                        candidates[0], candidates[1] = top2, top1

        winner = candidates[0]
        return ClassificationExplanation(
            category=winner.category,
            confidence=winner.confidence,
            winning_rule=winner.rule,
            winning_section=winner.section,
            effective_score=winner.effective_score,
            all_candidates=[
                {
                    "category": c.category,
                    "pattern_id": c.rule.pattern_id,
                    "section": c.section,
                    "weight": c.weight,
                    "effective_score": c.effective_score,
                    "confidence": c.confidence,
                }
                for c in candidates
            ],
        )

    def classify_best(
        self,
        text: str,
        sections: dict[str, str] | None = None,
        section_weights: dict[str, float] | None = None,
    ) -> tuple[str, float, CompetitiveRegex | None]:
        """Aplica apenas as melhores regexes de cada categoria em ordem de pontuação."""
        res = self.classify_with_explanation(
            text, sections=sections, section_weights=section_weights
        )
        return res.category, res.confidence, res.winning_rule

    def save_leaderboard(self, filepath: str | Path) -> None:
        """Persiste o ranking do torneio em arquivo JSON."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "top_k": self.top_k,
            "fp_penalty": self.fp_penalty,
            "min_precision": self.min_precision,
            "categories": {
                cat: [r.to_dict() for r in r_list] for cat, r_list in self.categories.items()
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_leaderboard(self, filepath: str | Path) -> None:
        """Carrega o ranking do torneio a partir de arquivo JSON."""
        path = Path(filepath)
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.top_k = data.get("top_k", self.top_k)
        self.fp_penalty = data.get("fp_penalty", self.fp_penalty)
        self.min_precision = data.get("min_precision", self.min_precision)
        self.categories = {}
        for cat, r_list in data.get("categories", {}).items():
            self.categories[cat] = [CompetitiveRegex.from_dict(d) for d in r_list]


def build_default_tournament() -> RegexTournament:
    """Inicializa o torneio com o catálogo de regexes sementes e variantes conhecidas."""
    t = RegexTournament(top_k=3, fp_penalty=2.0, min_precision=0.75)

    # 1. PROCEDENTE
    t.register(
        r"\bjulgo\s+procedentes?\b",
        "procedente",
        "proc_julgo_procedente",
        negative_pattern=r"(?:parcialmente|em\s+parte|não\s+acolho|deixo\s+de|improcedente)",
    )
    t.register(r"\bacolho\s+integralmente\b", "procedente", "proc_acolho_integral")
    t.register(
        r"\bprocedente\s+(?:a\s+)?(?:ação|pedido|pretensão)\b",
        "procedente",
        "proc_procedente_pedido",
        negative_pattern=r"(?:parcialmente|em\s+parte)",
    )
    t.register(r"\bcondeno\s+o\s+r[eé]u\b", "procedente", "proc_condeno_reu")
    t.register(
        r"\bjulgo\s+procedente\s+o\s+pedido\b",
        "procedente",
        "proc_julgo_proc_pedido",
        negative_pattern=r"(?:parcialmente|em\s+parte)",
    )
    t.register(r"\bacolher\s+o\s+pedido\s+inicial\b", "procedente", "proc_acolher_pedido_inicial")

    # 2. IMPROCEDENTE
    t.register(
        r"\bjulgo\s+improcedentes?\b",
        "improcedente",
        "improc_julgo_improcedente",
        negative_pattern=r"(?:não\s+julgo|deixo\s+de|parcialmente)",
    )
    t.register(
        r"\brejeito\s+(?:integralmente\s+)?o\s+pedido\b", "improcedente", "improc_rejeito_pedido"
    )
    t.register(
        r"\bimprocedente\s+(?:a\s+)?(?:ação|pedido)\b",
        "improcedente",
        "improc_pedido_improcedente",
        negative_pattern=r"(?:não\s+é\s+caso|parcialmente)",
    )
    t.register(
        r"\bjulgo\s+improcedente\s+a\s+pretensão\b", "improcedente", "improc_julgo_improc_pretensao"
    )

    # 3. PARCIALMENTE PROCEDENTE
    t.register(
        r"\b(?:julgo|julgando)\s+parcialmente\s+procedentes?\b",
        "parcialmente procedente",
        "parcial_julgo_parcial",
    )
    t.register(
        r"\b(?:julgo|julgando)\s+procedente\s+em\s+parte\b",
        "parcialmente procedente",
        "parcial_procedente_em_parte",
    )
    t.register(
        r"\bacolho\s+(?:em\s+parte|parcialmente)\b",
        "parcialmente procedente",
        "parcial_acolho_em_parte",
    )
    t.register(
        r"\bparcialmente\s+procedente\b", "parcialmente procedente", "parcial_parcialmente_proc"
    )
    t.register(
        r"\bprocedência\s+parcial\b", "parcialmente procedente", "parcial_procedencia_parcial"
    )

    # 4. EXTINTO SEM MÉRITO (CPC art. 485)
    t.register(
        r"\b(?:extingo|julgo\s+extinto)\s+o\s+processo\s+sem\s+resolução\s+(?:de|do)\s+mérito\b",
        "extinto sem mérito",
        "extinto_sem_resolucao",
    )
    t.register(
        r"\bextinto\s+sem\s+resolução\s+do\s+mérito\b",
        "extinto sem mérito",
        "extinto_sem_resolucao_2",
    )
    t.register(
        r"\bart\.?\s*485\b",
        "extinto sem mérito",
        "extinto_art_485",
        negative_pattern=r"(?:não\s+se\s+aplica|afasto\s+o\s+art|rejeito\s+o\s+art)",
    )
    t.register(
        r"\bindefiro\s+a\s+petição\s+inicial\b", "extinto sem mérito", "extinto_indefiro_inicial"
    )
    t.register(r"\bjulgo\s+extinto\s+o\s+processo\b", "extinto sem mérito", "extinto_julgo_extinto")

    # 5. ACORDO (CPC art. 487, III, b)
    t.register(
        r"\bhomologo\s+(?:por\s+sentença\s+)?o\s+acordo\b",
        "acordo",
        "acordo_homologo_acordo",
        negative_pattern=r"(?:rejeito|deixo\s+de)",
    )
    t.register(r"\bhomologo\s+a\s+transação\b", "acordo", "acordo_homologo_transacao")
    t.register(r"\bhomologo\s+a\s+avença\b", "acordo", "acordo_homologo_avenca")
    t.register(r"\bhomologação\s+de\s+acordo\b", "acordo", "acordo_homologacao")

    return t
