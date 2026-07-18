from __future__ import annotations

import pytest

from segmenter_dataset.gates import (
    GateResult,
    GateSeverity,
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
    results = [GateResult(name="ontology_schema_valid", passed=True)]
    evaluation = evaluate_gates(results, [])
    assert evaluation.release_allowed is True


def test_evaluate_gates_rigid_failure_blocks_even_with_known_limitation() -> None:
    results = [GateResult(name="ontology_schema_valid", passed=False, detail="bad offsets")]
    # A known_limitation naming a rigid gate cannot waive it (RFC 0012 §12.1) —
    # classify_gate still resolves it to RIGID regardless of what's in
    # known_limitations, so evaluate_gates never consults the list for it.
    limitations = [KnownLimitation(gate="ontology_schema_valid", reason="please ignore")]
    evaluation = evaluate_gates(results, limitations)
    assert evaluation.release_allowed is False
    assert len(evaluation.blocking_rigid_failures) == 1


def test_evaluate_gates_advisory_failure_blocks_without_known_limitation() -> None:
    results = [GateResult(name="multiple_tribunals", passed=False, detail="TJRO only")]
    evaluation = evaluate_gates(results, [])
    assert evaluation.release_allowed is False
    assert len(evaluation.blocking_unwaived_advisory_failures) == 1


def test_evaluate_gates_advisory_failure_waived_by_known_limitation() -> None:
    results = [GateResult(name="multiple_tribunals", passed=False, detail="TJRO only")]
    limitations = [
        KnownLimitation(gate="multiple_tribunals", reason="v8.1 is explicitly TJRO-only")
    ]
    evaluation = evaluate_gates(results, limitations)
    assert evaluation.release_allowed is True
    assert len(evaluation.waived_advisory_failures) == 1
