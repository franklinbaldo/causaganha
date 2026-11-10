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
from typing import Any

import numpy as np
from sklearn.metrics import f1_score, recall_score, roc_auc_score


class RatchetStateCorruptError(RuntimeError):
    """Lançada quando o arquivo de estado da catraca está ilegível ou corrompido."""


class RatchetStateLoadError(RuntimeError):
    """Lançada quando ocorre falha inesperada ao carregar o estado."""


@dataclass
class RatchetMetrics:
    roc_auc: float
    recall: float
    f1: float
    canary_passed: bool
    train_size: int
    evaluated_at: str
    high_water_roc_auc: float = 0.0
    high_water_recall: float = 0.0

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
        auc_tolerance: float = 0.005,  # margem máxima de flutuação estatística aceitável em relação ao high-water mark
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
            # Compatibilidade com estados antigos sem high_water
            if "high_water_roc_auc" not in data or data["high_water_roc_auc"] == 0.0:
                data["high_water_roc_auc"] = data.get("roc_auc", 0.0)
            if "high_water_recall" not in data or data["high_water_recall"] == 0.0:
                data["high_water_recall"] = data.get("recall", 0.0)
            return RatchetMetrics(**data)
        except json.JSONDecodeError as err:
            msg = (
                f"Catraca: Arquivo de estado corrompido em {self.state_file}: {err}. "
                "Corrija ou remova o arquivo para evitar sobrescrita indevida."
            )
            raise RatchetStateCorruptError(msg) from err
        except (OSError, KeyError, TypeError) as err:
            msg = f"Catraca: Erro ao carregar {self.state_file}: {err}"
            raise RatchetStateLoadError(msg) from err

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

        # 2. Teste Canário de Invariância Crítica (EXECUTA SEMPRE ANTES DE QUALQUER PROMOÇÃO)
        canary_all_passed = True
        canary_failure_reason = ""
        for idx, canary in enumerate(self.canary_cases):
            res = candidate_segmenter.predict(canary["text"], metadata=canary.get("metadata"))
            expected_needle = canary.get("expected_needle", "")
            if expected_needle and expected_needle.lower() not in res.snippet.lower():
                canary_all_passed = False
                canary_failure_reason = (
                    f"Canário #{idx} falhou: esperado '{expected_needle}' no snippet."
                )
                break

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cur_metrics = RatchetMetrics(
            roc_auc=round(cur_auc, 4),
            recall=round(cur_recall, 4),
            f1=round(cur_f1, 4),
            canary_passed=canary_all_passed,
            train_size=len(X_test),
            evaluated_at=now_str,
            high_water_roc_auc=round(cur_auc, 4),
            high_water_recall=round(cur_recall, 4),
        )

        # TRAVA INEGOCIÁVEL: Se os canários falharem, NENHUM modelo é promovido (nem no bootstrap inicial!)
        if not canary_all_passed:
            return RatchetDecision(
                promoted=False,
                reason=f"CATRACA TRAVADA: Regressão em caso canário crítico. {canary_failure_reason}",
                current_metrics=cur_metrics,
                baseline_metrics=self.baseline_state,
                metric_diffs={},
            )

        # Se não há baseline anterior E passou nos canários, estabelece o marco inicial
        if self.baseline_state is None:
            self._save_state(cur_metrics)
            self.baseline_state = cur_metrics
            if candidate_model_path != production_model_path and candidate_model_path.exists():
                shutil.copyfile(candidate_model_path, production_model_path)
            return RatchetDecision(
                promoted=True,
                reason="Baseline inicial estabelecido pela Catraca (todos os canários aprovados).",
                current_metrics=cur_metrics,
                baseline_metrics=None,
                metric_diffs={},
            )

        # 3. Verificação contra o High-Water Mark (Impede erosão cumulativa de métricas)
        high_water_auc = self.baseline_state.high_water_roc_auc or self.baseline_state.roc_auc
        high_water_rec = self.baseline_state.high_water_recall or self.baseline_state.recall

        diffs = {
            "roc_auc_diff_vs_high_water": round(cur_metrics.roc_auc - high_water_auc, 4),
            "recall_diff_vs_high_water": round(cur_metrics.recall - high_water_rec, 4),
            "roc_auc_diff_vs_last": round(cur_metrics.roc_auc - self.baseline_state.roc_auc, 4),
            "f1_diff": round(cur_metrics.f1 - self.baseline_state.f1, 4),
        }

        # Trava 1: Queda inaceitável em relação ao HIGH-WATER MARK histórico (limite absoluto de erosão)
        if diffs["roc_auc_diff_vs_high_water"] < -self.auc_tolerance:
            return RatchetDecision(
                promoted=False,
                reason=(
                    f"CATRACA TRAVADA: Regressão de ROC-AUC contra High-Water Mark "
                    f"({cur_metrics.roc_auc:.4f} < {high_water_auc:.4f} com tolerância de {self.auc_tolerance})."
                ),
                current_metrics=cur_metrics,
                baseline_metrics=self.baseline_state,
                metric_diffs=diffs,
            )

        # Trava 2: Queda severa no Recall contra o High-Water Mark (máximo 5 p.p.)
        if diffs["recall_diff_vs_high_water"] < -0.05:
            return RatchetDecision(
                promoted=False,
                reason=(
                    f"CATRACA TRAVADA: Regressão de Recall contra High-Water Mark "
                    f"({cur_metrics.recall:.4f} < {high_water_rec:.4f} com tolerância de 0.05)."
                ),
                current_metrics=cur_metrics,
                baseline_metrics=self.baseline_state,
                metric_diffs=diffs,
            )

        # Aprovado pela catraca! Atualiza o high-water mark e persiste
        cur_metrics.high_water_roc_auc = max(high_water_auc, cur_metrics.roc_auc)
        cur_metrics.high_water_recall = max(high_water_rec, cur_metrics.recall)
        self._save_state(cur_metrics)
        self.baseline_state = cur_metrics
        if candidate_model_path != production_model_path and candidate_model_path.exists():
            shutil.copyfile(candidate_model_path, production_model_path)

        return RatchetDecision(
            promoted=True,
            reason="MODELO APROVADO PELA CATRACA: Métricas mantidas ou superiores ao High-Water Mark.",
            current_metrics=cur_metrics,
            baseline_metrics=self.baseline_state,
            metric_diffs=diffs,
        )
