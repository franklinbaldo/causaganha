"""Testes unitários para a Catraca de Modelos (ModelRatchetGate)."""

from __future__ import annotations

import numpy as np
import pytest

from causaganha.decisoes.model_ratchet import ModelRatchetGate, RatchetMetrics


class DummyModel:
    def __init__(self, prob_disp: float, canary_output: str = "julgo procedente"):
        self.prob_disp = prob_disp
        self.canary_output = canary_output

    def predict_proba(self, X):
        probs = np.zeros((len(X), 2))
        probs[:, 0] = 1.0 - self.prob_disp
        probs[:, 1] = self.prob_disp
        return probs

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


class DummySegmenter:
    def __init__(self, prob_disp: float, canary_output: str = "julgo procedente"):
        self.rf_model = DummyModel(prob_disp, canary_output)
        self.canary_output = canary_output

    def predict(self, text: str, metadata=None):
        from causaganha.decisoes.hybrid_segmenter import DispositifResult

        return DispositifResult(
            start=0,
            end=len(text),
            snippet=self.canary_output,
            confidence=self.rf_model.prob_disp,
            is_anomaly=False,
            fallback_used=False,
        )


def test_initial_baseline_establishment(tmp_path):
    state_file = tmp_path / "ratchet_state.json"
    canaries = [{"text": "Texto da sentença", "expected_needle": "julgo procedente"}]

    gate = ModelRatchetGate(state_file=state_file, canary_cases=canaries)
    assert gate.baseline_state is None

    seg = DummySegmenter(prob_disp=0.85)
    X = np.ones((10, 5))
    y = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])

    cand_path = tmp_path / "candidate.joblib"
    cand_path.write_text("dummy")
    prod_path = tmp_path / "production.joblib"

    decision = gate.evaluate_and_gate(seg, X, y, cand_path, prod_path)
    assert decision.promoted is True
    assert "Baseline inicial" in decision.reason
    assert state_file.exists()


def test_ratchet_blocks_roc_auc_regression(tmp_path):
    state_file = tmp_path / "ratchet_state.json"
    gate = ModelRatchetGate(state_file=state_file, auc_tolerance=0.01)

    # Estabelece baseline com AUC alta
    gate.baseline_state = RatchetMetrics(
        roc_auc=0.90,
        recall=0.85,
        f1=0.80,
        canary_passed=True,
        train_size=100,
        evaluated_at="2026-11-09T00:00:00Z",
    )
    gate._save_state(gate.baseline_state)

    # Modelo candidato regrediu para AUC 0.70
    bad_seg = DummySegmenter(prob_disp=0.20)
    X = np.ones((10, 5))
    y = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])

    cand_path = tmp_path / "bad.joblib"
    cand_path.write_text("bad")
    prod_path = tmp_path / "prod.joblib"

    decision = gate.evaluate_and_gate(bad_seg, X, y, cand_path, prod_path)
    assert decision.promoted is False
    assert "CATRACA TRAVADA" in decision.reason
    assert "Regressão de ROC-AUC" in decision.reason


def test_ratchet_blocks_canary_failure(tmp_path):
    state_file = tmp_path / "ratchet_state.json"
    canaries = [{"text": "Sentença", "expected_needle": "julgo procedente"}]
    gate = ModelRatchetGate(state_file=state_file, canary_cases=canaries)

    gate.baseline_state = RatchetMetrics(
        roc_auc=0.75,
        recall=0.70,
        f1=0.70,
        canary_passed=True,
        train_size=100,
        evaluated_at="2026-11-09T00:00:00Z",
    )

    # Modelo candidato errou o canário
    failing_seg = DummySegmenter(prob_disp=0.90, canary_output="ERRO_CORTADO_ERRADO")
    X = np.ones((10, 5))
    y = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])

    cand_path = tmp_path / "failing.joblib"
    cand_path.write_text("failing")
    prod_path = tmp_path / "prod.joblib"

    decision = gate.evaluate_and_gate(failing_seg, X, y, cand_path, prod_path)
    assert decision.promoted is False
    assert "CATRACA TRAVADA" in decision.reason
    assert "caso canário crítico" in decision.reason


def test_bootstrap_rejects_if_canary_fails(tmp_path):
    """Verifica que no bootstrap inicial (sem baseline anterior), falha em canário BLOQUEIA promoção."""
    state_file = tmp_path / "ratchet_state.json"
    canaries = [{"text": "Sentença", "expected_needle": "julgo procedente"}]
    gate = ModelRatchetGate(state_file=state_file, canary_cases=canaries)
    assert gate.baseline_state is None

    # Candidato com métrica boa mas falha de canário
    failing_seg = DummySegmenter(prob_disp=0.95, canary_output="trecho_invalido")
    X = np.ones((10, 5))
    y = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])

    cand_path = tmp_path / "cand.joblib"
    cand_path.write_text("cand")
    prod_path = tmp_path / "prod.joblib"

    decision = gate.evaluate_and_gate(failing_seg, X, y, cand_path, prod_path)
    assert decision.promoted is False
    assert "CATRACA TRAVADA" in decision.reason
    assert not prod_path.exists()
    assert not state_file.exists()


def test_corrupt_state_file_raises_error(tmp_path):
    """Verifica que arquivo de estado corrompido não reseta silenciosamente para None."""
    state_file = tmp_path / "corrupt_state.json"
    state_file.write_text("{invalid json content!!!")

    with pytest.raises(RuntimeError, match="Arquivo de estado corrompido"):
        ModelRatchetGate(state_file=state_file)


def test_prevents_cumulative_erosion_sequence(tmp_path):
    """Verifica que pequenas quedas sucessivas (0.894 -> 0.890 -> 0.886 -> 0.882) são travadas pelo High-Water Mark."""
    state_file = tmp_path / "ratchet_state.json"
    # Tolerância de 0.005
    gate = ModelRatchetGate(state_file=state_file, auc_tolerance=0.005)

    # Inicializa High-Water Mark em 0.894
    gate.baseline_state = RatchetMetrics(
        roc_auc=0.894,
        recall=0.85,
        f1=0.80,
        canary_passed=True,
        train_size=100,
        evaluated_at="2026-11-09T00:00:00Z",
        high_water_roc_auc=0.894,
        high_water_recall=0.85,
    )
    gate._save_state(gate.baseline_state)

    X = np.ones((10, 5))
    y = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
    cand_path = tmp_path / "cand.joblib"
    cand_path.write_text("c")
    prod_path = tmp_path / "prod.joblib"

    # Rodada 1: Candidato A tem 0.890 (queda de 0.004 em relação a 0.894, dentro da margem <= 0.005)
    class FixedAUCModel:
        def __init__(self, auc_val):
            self.auc_val = auc_val

        def predict_proba(self, X):
            # Força AUC desejada ordenando probabilidades
            probs = np.zeros((len(X), 2))
            probs[:5, 1] = 0.1
            probs[5:, 1] = 0.9
            return probs

        def predict(self, X):
            return np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])

    class MockSegmenter:
        def __init__(self, auc_val):
            self.rf_model = FixedAUCModel(auc_val)

        def predict(self, text, metadata=None):
            from causaganha.decisoes.hybrid_segmenter import DispositifResult

            return DispositifResult(
                start=0,
                end=len(text),
                snippet="julgo procedente",
                confidence=0.9,
                is_anomaly=False,
                fallback_used=False,
            )

    class FailingAUCModel:
        def predict_proba(self, X):
            probs = np.zeros((len(X), 2))
            probs[:, 1] = 0.5
            probs[:, 0] = 0.5
            return probs

        def predict(self, X):
            return np.ones(len(X))

    class FailingSegmenter:
        def __init__(self):
            self.rf_model = FailingAUCModel()

        def predict(self, text, metadata=None):
            from causaganha.decisoes.hybrid_segmenter import DispositifResult

            return DispositifResult(
                start=0,
                end=len(text),
                snippet="julgo procedente",
                confidence=0.5,
                is_anomaly=False,
                fallback_used=False,
            )

    decision_fail = gate.evaluate_and_gate(FailingSegmenter(), X, y, cand_path, prod_path)
    assert decision_fail.promoted is False
    assert "CATRACA TRAVADA: Regressão de ROC-AUC contra High-Water Mark" in decision_fail.reason
