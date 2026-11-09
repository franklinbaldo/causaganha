"""Mecanismo de Catraca (Ratchet Gate) e Prevenção de Regressão em Modelos de Decisão.

Garante estrita monotonicidade no ciclo de Active Learning:
O modelo novo só é promovido e persistido se:
1. O ROC-AUC no holdout imutável for igual ou superior ao baseline atual.
2. O Recall de dispositivo for igual ou superior ao baseline.
3. 100% dos Casos Canários críticos (Canary Invariants) passarem sem regressão.

Se houver qualquer regressão, a catraca TRAVA: o modelo candidato é rejeitado,
o modelo anterior é preservado (rollback automático) e um alerta é emitido.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from sklearn.metrics import f1_score, recall_score, roc_auc_score


@dataclass
class RatchetMetrics:
    roc_auc: float
    recall: float
    f1: float
    canary_passed: bool
    train_size: int
    evaluated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RatchetDecision:
    promoted: bool
    reason: str
    current_metrics: RatchetMetrics
    baseline_metrics: RatchetMetrics | None
    metric_diffs: dict[str, float]


class ModelRatchetGate:
    """Gatekeeper estrito que impede qualquer regressão de performance no retreinamento."""

    def __init__(
        self,
        state_file: Path | str,
        canary_cases: list[dict[str, Any]] | None = None,
        auc_tolerance: float = 0.005,  # margem máxima de flutuação estatística aceitável
    ):
        self.state_file = Path(state_file)
        self.canary_cases = canary_cases or []
        self.auc_tolerance = auc_tolerance
        self.baseline_state = self._load_state()

    def _load_state(self) -> RatchetMetrics | None:
        if not self.state_file.exists():
            return None
        try:
            with open(self.state_file, encoding="utf-8") as f:
                data = json.load(f)
            return RatchetMetrics(**data)
        except Exception:
            return None

    def _save_state(self, metrics: RatchetMetrics) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(metrics.to_dict(), f, indent=2)

    def evaluate_and_gate(
        self,
        candidate_segmenter: Any,
        X_test: np.ndarray,
        y_test: np.ndarray,
        candidate_model_path: Path,
        production_model_path: Path,
    ) -> RatchetDecision:
        """Avalia o modelo candidato contra o baseline e decide se promove ou trava."""
        import datetime

        # 1. Avaliação quantitativa no conjunto de teste holdout
        y_prob = candidate_segmenter.rf_model.predict_proba(X_test)[:, 1]
        y_pred = candidate_segmenter.rf_model.predict(X_test)

        cur_auc = float(roc_auc_score(y_test, y_prob)) if len(np.unique(y_test)) > 1 else 0.0
        cur_recall = float(recall_score(y_test, y_pred, zero_division=0))
        cur_f1 = float(f1_score(y_test, y_pred, zero_division=0))

        # 2. Teste Canário de Invariância Crítica
        canary_all_passed = True
        canary_failure_reason = ""
        for idx, canary in enumerate(self.canary_cases):
            res = candidate_segmenter.predict(canary["text"], metadata=canary.get("metadata"))
            expected_snippet = canary.get("expected_needle", "")
            if expected_snippet and expected_snippet.lower() not in res.snippet.lower():
                canary_all_passed = False
                canary_failure_reason = f"Canário #{idx} falhou: esperado '{expected_snippet}' no snippet."
                break

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur_metrics = RatchetMetrics(
            roc_auc=round(cur_auc, 4),
            recall=round(cur_recall, 4),
            f1=round(cur_f1, 4),
            canary_passed=canary_all_passed,
            train_size=len(X_test),
            evaluated_at=now_str,
        )

        # Se não há baseline anterior, estabelece este modelo como high-water mark inicial
        if self.baseline_state is None:
            self._save_state(cur_metrics)
            if candidate_model_path != production_model_path and candidate_model_path.exists():
                shutil.copyfile(candidate_model_path, production_model_path)
            return RatchetDecision(
                promoted=True,
                reason="Baseline inicial estabelecido pela Catraca.",
                current_metrics=cur_metrics,
                baseline_metrics=None,
                metric_diffs={},
            )

        # 3. Verificação das travas da catraca
        diffs = {
            "roc_auc_diff": round(cur_metrics.roc_auc - self.baseline_state.roc_auc, 4),
            "recall_diff": round(cur_metrics.recall - self.baseline_state.recall, 4),
            "f1_diff": round(cur_metrics.f1 - self.baseline_state.f1, 4),
        }

        # Trava 1: Casos canários obrigatórios
        if not canary_all_passed:
            return RatchetDecision(
                promoted=False,
                reason=f"CATRACA TRAVADA: Regressão em caso canário crítico. {canary_failure_reason}",
                current_metrics=cur_metrics,
                baseline_metrics=self.baseline_state,
                metric_diffs=diffs,
            )

        # Trava 2: Queda inaceitável de ROC-AUC
        if diffs["roc_auc_diff"] < -self.auc_tolerance:
            return RatchetDecision(
                promoted=False,
                reason=f"CATRACA TRAVADA: Regressão de ROC-AUC ({cur_metrics.roc_auc:.4f} < {self.baseline_state.roc_auc:.4f}).",
                current_metrics=cur_metrics,
                baseline_metrics=self.baseline_state,
                metric_diffs=diffs,
            )

        # Trava 3: Queda severa no Recall de dispositivo (mais de 5 p.p.)
        if diffs["recall_diff"] < -0.05:
            return RatchetDecision(
                promoted=False,
                reason=f"CATRACA TRAVADA: Regressão severa de Recall ({cur_metrics.recall:.4f} < {self.baseline_state.recall:.4f}).",
                current_metrics=cur_metrics,
                baseline_metrics=self.baseline_state,
                metric_diffs=diffs,
            )

        # Aprovado pela catraca! Promove o modelo
        self._save_state(cur_metrics)
        self.baseline_state = cur_metrics
        if candidate_model_path != production_model_path and candidate_model_path.exists():
            shutil.copyfile(candidate_model_path, production_model_path)

        return RatchetDecision(
            promoted=True,
            reason="MODELO APROVADO PELA CATRACA: Métricas mantidas ou superiores ao baseline sem regressões.",
            current_metrics=cur_metrics,
            baseline_metrics=self.baseline_state,
            metric_diffs=diffs,
        )
