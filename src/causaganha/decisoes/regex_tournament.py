"""Torneio Competitivo de Regexes (Regex Tournament & Leaderboard).

Implementa a dinâmica de seleção natural e ranqueamento de expressões regulares:
- Cada regex candidata é testada contra o acervo real.
- Acertos (True Positives) somam pontos.
- Falsos Positivos (False Positives) recebem penalidade severa (FP Penalty).
- Para cada categoria processual, apenas o Top-K de regexes promovidas é utilizado em produção.
- Regexes que acumulam falsos positivos são automaticamente rebaixadas (DEMOTED).
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any


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
    ):
        self.pattern_id = pattern_id
        self.pattern = pattern
        self.category = category.lower().strip()
        self.source = source
        self.description = description
        self.fp_penalty = fp_penalty

        self.tp: int = 0
        self.fp: int = 0
        self.fn: int = 0
        self.total_tested: int = 0
        self.precision: float = 0.0
        self.recall: float = 0.0
        self.score: float = 0.0
        self.status: str = "CANDIDATE"  # CANDIDATE, PROMOTED, DEMOTED

        self._compiled: re.Pattern[str] | None = None

    @property
    def compiled(self) -> re.Pattern[str]:
        if self._compiled is None:
            self._compiled = re.compile(self.pattern, re.IGNORECASE)
        return self._compiled

    def matches(self, text: str) -> bool:
        """Verifica se o padrão tem match no texto."""
        if not text:
            return False
        return bool(self.compiled.search(text))

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
    ) -> CompetitiveRegex:
        """Registra uma nova regex candidata no pool de sua categoria."""
        cat = category.lower().strip()
        if cat not in self.categories:
            self.categories[cat] = []

        # Evita duplicidade de padrão
        for existing in self.categories[cat]:
            if existing.pattern == pattern:
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

    def classify_best(self, text: str) -> tuple[str, float, CompetitiveRegex | None]:
        """Aplica apenas as melhores regexes de cada categoria em ordem de pontuação."""
        # Coleta as top regexes de todas as categorias
        candidate_matches: list[tuple[str, CompetitiveRegex]] = []
        for cat in self.categories:
            top_rules = self.get_top_k(cat)
            for r in top_rules:
                if r.matches(text):
                    candidate_matches.append((cat, r))
                    break  # Primeira melhor da categoria acertou

        if not candidate_matches:
            return "unknown", 0.0, None

        # Se mais de uma categoria deu match, vence a regex com maior score histórico
        candidate_matches.sort(key=lambda x: x[1].score, reverse=True)
        winner_cat, winner_reg = candidate_matches[0]

        # Confiança derivada da precisão histórica comprovada da regex
        confidence = winner_reg.precision

        return winner_cat, confidence, winner_reg

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
    t.register(r"\bjulgo\s+procedentes?\b(?!\s+em\s+parte)", "procedente", "proc_julgo_procedente")
    t.register(r"\bacolho\s+integralmente\b", "procedente", "proc_acolho_integral")
    t.register(
        r"\bprocedente\s+(?:a\s+)?(?:ação|pedido|pretensão)\b",
        "procedente",
        "proc_procedente_pedido",
    )
    t.register(r"\bcondeno\s+o\s+r[eé]u\b", "procedente", "proc_condeno_reu")
    t.register(r"\bjulgo\s+procedente\s+o\s+pedido\b", "procedente", "proc_julgo_proc_pedido")
    t.register(r"\bacolher\s+o\s+pedido\s+inicial\b", "procedente", "proc_acolher_pedido_inicial")

    # 2. IMPROCEDENTE
    t.register(r"\bjulgo\s+improcedentes?\b", "improcedente", "improc_julgo_improcedente")
    t.register(
        r"\brejeito\s+(?:integralmente\s+)?o\s+pedido\b", "improcedente", "improc_rejeito_pedido"
    )
    t.register(
        r"\bimprocedente\s+(?:a\s+)?(?:ação|pedido)\b", "improcedente", "improc_pedido_improcedente"
    )
    t.register(
        r"\bjulgo\s+improcedente\s+a\s+pretensão\b", "improcedente", "improc_julgo_improc_pretensao"
    )

    # 3. PARCIALMENTE PROCEDENTE
    t.register(
        r"\bjulgo\s+parcialmente\s+procedentes?\b",
        "parcialmente procedente",
        "parcial_julgo_parcial",
    )
    t.register(
        r"\bparcialmente\s+procedente\b", "parcialmente procedente", "parcial_parcialmente_proc"
    )
    t.register(
        r"\bprocedente\s+em\s+parte\b", "parcialmente procedente", "parcial_procedente_em_parte"
    )
    t.register(
        r"\bprocedência\s+parcial\b", "parcialmente procedente", "parcial_procedencia_parcial"
    )
    t.register(
        r"\bacolho\s+em\s+parte\s+o\s+pedido\b",
        "parcialmente procedente",
        "parcial_acolho_em_parte",
    )

    # 4. EXTINTO SEM MÉRITO (CPC art. 485)
    t.register(
        r"\bextingo\s+o\s+processo\s+sem\s+resolução\s+(?:de|do)\s+mérito\b",
        "extinto sem mérito",
        "extinto_sem_resolucao",
    )
    t.register(
        r"\bextinto\s+sem\s+resolução\s+do\s+mérito\b",
        "extinto sem mérito",
        "extinto_sem_resolucao_2",
    )
    t.register(r"\bart\.?\s*485\b", "extinto sem mérito", "extinto_art_485")
    t.register(
        r"\bindefiro\s+a\s+petição\s+inicial\b", "extinto sem mérito", "extinto_indefiro_inicial"
    )
    t.register(r"\bjulgo\s+extinto\s+o\s+processo\b", "extinto sem mérito", "extinto_julgo_extinto")

    # 5. ACORDO (CPC art. 487, III, b)
    t.register(
        r"\bhomologo\s+(?:por\s+sentença\s+)?o\s+acordo\b", "acordo", "acordo_homologo_acordo"
    )
    t.register(r"\bhomologo\s+a\s+transação\b", "acordo", "acordo_homologo_transacao")
    t.register(r"\bhomologo\s+a\s+avença\b", "acordo", "acordo_homologo_avenca")
    t.register(r"\bhomologação\s+de\s+acordo\b", "acordo", "acordo_homologacao")

    return t
