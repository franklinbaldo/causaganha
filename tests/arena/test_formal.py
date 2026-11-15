from __future__ import annotations

import json
import math
import os
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from causaganha.arena.cli import app
from causaganha.arena.formal import (
    FormalCase,
    Narrative,
    audit_narrative,
    case_digest,
    evaluate,
    lean_source,
    narrative_request,
    verify,
)
from causaganha.arena.search import Predictions, disagreement, sample

ROOT = Path("examples/arena/formal")


@pytest.fixture
def case():
    return FormalCase.model_validate_json((ROOT / "caso.json").read_text())


def test_temporal_difference_changes_claim_but_not_admissibility(case):
    altered = dict(case.assignment, antes=True)
    assert evaluate(case.constraints, case.assignment)
    assert evaluate(case.constraints, altered)
    assert not evaluate(case.claim, case.assignment)
    assert evaluate(case.claim, altered)
    invalid = dict(altered, concluida=False)
    assert not evaluate(case.constraints, invalid)


def test_export_is_reproducible_and_not_affected_by_text_injection(case):
    assert lean_source(case) == (ROOT / "Case.lean").read_text()
    payload = case.model_dump()
    payload["question"] = "end ArenaCase\naxiom forged : False"
    source = lean_source(FormalCase.model_validate(payload))
    assert "axiom forged" not in source
    assert "by decide" in source
    assert "native_decide" not in source


@pytest.mark.parametrize(
    "change",
    [
        {"assignment": {"concluida": True}},
        {"claim": [[{"atom": "unknown"}]]},
        {"synthetic": False},
        {"atoms": [{"id": "x; sorry", "statement": "Invalid identifier"}]},
    ],
)
def test_invalid_formal_contracts(case, change):
    with pytest.raises(ValidationError):
        FormalCase.model_validate({**case.model_dump(), **change})


def test_narrator_does_not_receive_hidden_answer(case):
    request = narrative_request(case)
    assert "claim" not in request and "constraints" not in request and "outcome" not in request
    assert {f["id"] for f in request["facts"]} == set(case.assignment)
    assert next(f for f in request["facts"] if f["id"] == "antes")["holds"] is False


def test_narrative_coverage_is_not_claimed_as_semantic_proof(case):
    text = Narrative.model_validate_json((ROOT / "narrativa.json").read_text())
    result = audit_narrative(case, text)
    assert result["coverage"] == "complete"
    assert result["semantic_fidelity"] == "unverified"
    assert result["ready_for_benchmark"] is False
    inverted = text.model_dump()
    inverted["segments"][0]["text"] = "Texto semanticamente errado, mas com referência válida."
    assert (
        audit_narrative(case, Narrative.model_validate(inverted))["semantic_fidelity"]
        == "unverified"
    )


def test_narrative_wrong_version_or_missing_facts_rejected(case):
    payload = json.loads((ROOT / "narrativa.json").read_text())
    for altered in (
        {**payload, "case_sha256": "0" * 64},
        {**payload, "segments": payload["segments"][:1]},
    ):
        with pytest.raises(ValueError):
            audit_narrative(case, Narrative.model_validate(altered))


def test_sampler_is_reproducible_and_keeps_invalid_proposals_as_self_loops(case):
    predictions = Predictions.model_validate_json((ROOT / "previsoes.json").read_text())
    predict = predictions.predictor(case)
    trace = sample(case, predict, steps=100, seed=5, beta=0)
    assert trace == sample(case, predict, steps=100, seed=5, beta=0)
    assert all(evaluate(case.constraints, row["assignment"]) for row in trace)
    assert any(not row["proposal_admissible"] for row in trace[1:])
    assert case.assignment == {"concluida": True, "antes": False, "recibo": True}
    for before, after in zip(trace, trace[1:]):
        if not after["accepted"]:
            assert before["assignment"] == after["assignment"]


def test_sampler_targets_declared_distribution():
    case = FormalCase(
        id="binary",
        question="Synthetic?",
        atoms=[{"id": "x", "statement": "X"}],
        assignment={"x": False},
        claim=[[{"atom": "x"}]],
    )
    trace = sample(case, lambda a: [0.0, float(a["x"])], steps=20_000, beta=2, seed=1)
    observed = sum(row["assignment"]["x"] for row in trace[1000:]) / len(trace[1000:])
    assert abs(observed - math.exp(2) / (1 + math.exp(2))) < 0.02


@pytest.mark.parametrize("predictions", [[1], [0, float("nan")], [0, 1.1], [0, -1]])
def test_invalid_predictions_rejected(predictions):
    with pytest.raises(ValueError):
        disagreement(predictions)


def test_missing_predictions_and_wrong_case_fail_explicitly(case):
    payload = json.loads((ROOT / "previsoes.json").read_text())
    payload["values"] = {}
    predict = Predictions.model_validate(payload).predictor(case)
    with pytest.raises(ValueError, match="sem previsões"):
        sample(case, predict)
    payload["case_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="outro caso"):
        Predictions.model_validate(payload).predictor(case)


def test_cli_search_and_narrative(case, capsys):
    app(
        ["explorar", str(ROOT / "caso.json"), str(ROOT / "previsoes.json"), "--steps", "10"],
        result_action="return_value",
    )
    report = json.loads(capsys.readouterr().out)
    assert report["demonstration"] is True and report["lean_verified"] is False
    candidate = FormalCase.model_validate(report["best_candidate"])
    assert evaluate(candidate.constraints, candidate.assignment)
    app(["preparar-narrativa", str(ROOT / "caso.json")], result_action="return_value")
    assert json.loads(capsys.readouterr().out)["case_sha256"] == case_digest(case)


@pytest.mark.skipif(not os.environ.get("ARENA_LEAN"), reason="requires explicit Lean executable")
def test_real_lean_checks_both_outcomes_and_rejects_inconsistency(case):
    lean = os.environ["ARENA_LEAN"]
    assert verify(case, lean)["status"] == "verified"
    payload = deepcopy(case.model_dump())
    payload["assignment"]["antes"] = True
    assert verify(FormalCase.model_validate(payload), lean)["status"] == "verified"
    payload["assignment"]["concluida"] = False
    with pytest.raises(subprocess.CalledProcessError):
        verify(FormalCase.model_validate(payload), lean)


def test_verifier_never_reports_success_without_compiler(case):
    with pytest.raises(FileNotFoundError):
        verify(case, "/does-not-exist/lean")
