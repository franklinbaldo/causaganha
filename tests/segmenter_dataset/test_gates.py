from __future__ import annotations

import pytest

from segmenter_dataset.gates import (
    GateResult,
    GateSeverity,
    InvalidKnownLimitationError,
    UnknownGateError,
    classify_gate,
    evaluate_gates,
)
from segmenter_dataset.schemas import KnownLimitation


def test_classify_gate_rigid() -> None:
    assert classify_gate("ontology_schema_valid") is GateSeverity.RIGID


def test_classify_gate_advisory() -> None:
    assert classify_gate("multiple_tribunals") is GateSeverity.ADVISORY


def test_classify_gate_unknown_raises() -> None:
    with pytest.raises(UnknownGateError):
        classify_gate("made_up_gate_name")


def test_evaluate_gates_all_pass() -> None:
    evaluation = evaluate_gates([GateResult(name="ontology_schema_valid", passed=True)], [])
    assert evaluation.release_allowed is True


def test_known_limitation_cannot_name_rigid_gate() -> None:
    results = [GateResult(name="ontology_schema_valid", passed=False, detail="bad offsets")]
    limitations = [KnownLimitation(gate="ontology_schema_valid", reason="please ignore")]
    with pytest.raises(InvalidKnownLimitationError):
        evaluate_gates(results, limitations)


def test_known_limitation_cannot_name_unknown_gate() -> None:
    with pytest.raises(InvalidKnownLimitationError):
        evaluate_gates([], [KnownLimitation(gate="invented", reason="no")])


def test_evaluate_gates_advisory_failure_blocks_without_known_limitation() -> None:
    results = [GateResult(name="multiple_tribunals", passed=False, detail="TJRO only")]
    evaluation = evaluate_gates(results, [])
    assert evaluation.release_allowed is False
    assert len(evaluation.blocking_unwaived_advisory_failures) == 1


def test_evaluate_gates_advisory_failure_waived_by_known_limitation() -> None:
    results = [GateResult(name="multiple_tribunals", passed=False, detail="TJRO only")]
    limitations = [KnownLimitation(gate="multiple_tribunals", reason="TJRO-only")]
    evaluation = evaluate_gates(results, limitations)
    assert evaluation.release_allowed is True
    assert len(evaluation.waived_advisory_failures) == 1
