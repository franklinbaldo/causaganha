"""Unit/contract tests for experimental THX-02 classifier (no HTTP calls)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import spike_thx02 as spike


def _choice_answer(name: str, selected: str, probability: float = 0.97) -> dict:
    choices = tuple(spike.QUESTIONS[name]["criteria"])
    assert selected in choices
    remaining = (1 - probability) / (len(choices) - 1)
    return {
        "type": "choice",
        "choice": selected,
        "confidence": 0.1,  # Deliberately differs from selected probability.
        "probabilities": {key: probability if key == selected else remaining for key in choices},
    }


def _response(outcome: str, polo: str, direct: str = "unknown") -> dict:
    return {
        "model": "THX-02",
        "answers": {
            "decision_type": _choice_answer("decision_type", "acordao"),
            "outcome": _choice_answer("outcome", outcome),
            "recorrente_polo": _choice_answer("recorrente_polo", polo),
            "winner_direct": _choice_answer("winner_direct", direct),
        },
        "usage": {"input_tokens": 150, "output_tokens": 0, "thoughts": 0},
        "latency_ms": 82.3,
    }


@pytest.mark.parametrize(
    ("outcome", "polo", "expected"),
    [
        ("procedente", None, "A"),
        ("improcedente", None, "P"),
        ("acordo", None, "draw"),
        ("parcialmente procedente", None, "unknown"),
        ("extinto sem mérito", None, "unknown"),
        ("provido", "A", "A"),
        ("provido", "P", "P"),
        ("não provido", "A", "P"),
        ("não provido", "P", "A"),
        ("provido", "ambos", "unknown"),
        ("provido", "unknown", "unknown"),
        ("parcialmente provido", "A", "unknown"),
        ("não conhecido", "A", "unknown"),
        ("prejudicado", "P", "unknown"),
    ],
)
def test_resolve_winner_is_conservative(outcome: str, polo: str | None, expected: str) -> None:
    assert spike.resolve_winner(outcome, polo) == expected


def test_contract_request_has_four_questions_and_explicit_model() -> None:
    item = spike.make_item({"text": "ACÓRDÃO"}, think=True, tta=4)
    assert item["think"] == "auto"
    assert item["tta"] == 4
    assert len(item["questions"]) == 4
    assert set(item["questions"]["outcome"]["criteria"]) == set(spike.OUTCOME_LABELS)


def test_decode_uses_selected_probability_not_vendor_confidence() -> None:
    doc = {"id": "test-1", "text": "Acórdão"}
    answer = spike.decode_response(doc, _response("nao_provido", "P", "A"), threshold=0.90)
    assert answer["outcome"] == "não provido"
    assert answer["recorrente_polo"] == "P"
    assert answer["winner"] == "A"
    assert answer["winner_rule_probability"] == pytest.approx(0.97)
    assert answer["winner_direct"] == "A"
    assert answer["abstained"] is False
    assert "text" not in answer


def test_low_confidence_abstains() -> None:
    doc = {"id": "test-2", "text": "Acórdão"}
    response = _response("provido", "A", "A")
    response["answers"]["recorrente_polo"] = _choice_answer("recorrente_polo", "A", 0.65)
    answer = spike.decode_response(doc, response, threshold=0.90)
    assert answer["winner"] == "unknown"
    assert answer["abstained"] is True
    assert answer["winner_direct"] == "A"  # independent diagnostic, not overriding abstention


def test_partial_and_procedural_cases_abstain_even_when_confident() -> None:
    doc = {"id": "test-3", "text": "Acórdão"}
    for label in ("parcialmente_provido", "nao_conhecido", "extinto_sem_merito", "unknown"):
        prediction = spike.decode_response(doc, _response(label, "P"), 0.9)
        assert prediction["winner"] == "unknown"


def test_invalid_probabilities_raise_instead_of_silently_accepting() -> None:
    response = _response("provido", "A")
    response["answers"]["outcome"]["probabilities"]["alien"] = 0.1
    with pytest.raises(ValueError, match="different option set"):
        spike.decode_response({"id": "test-4", "text": "Acórdão"}, response, 0.90)


def test_interlocutory_type_prevents_false_positive_winner() -> None:
    doc = {"id": "test-interloc", "text": "Citação de sentença alheia"}
    response = _response("procedente", "nao_aplicavel", "A")
    response["answers"]["decision_type"] = _choice_answer(
        "decision_type", "interlocutoria"
    )
    prediction = spike.decode_response(doc, response, 0.90)
    assert prediction["winner"] == "unknown"


def test_wrong_model_rejected() -> None:
    response = _response("provido", "A")
    response["model"] = "THX-01"
    with pytest.raises(ValueError, match="Wrong model"):
        spike.decode_response({"id": "test-4", "text": "Acórdão"}, response, 0.90)


def test_send_batch_uses_correct_endpoint_without_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    class FakeHTTP:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit: int) -> bytes:
            return json.dumps({"results": [_response("provido", "A")]}).encode()

    def fake_open(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeHTTP()

    monkeypatch.setattr(spike, "urlopen", fake_open)
    item = spike.make_item({"text": "FICTÍCIO"}, think=False, tta=1)
    result = spike.send_batch([item])
    assert len(result) == 1
    assert captured["url"] == "https://api.hal-x.ai/v1/decide/batch"
    assert captured["body"]["model"] == "thx-02"
    assert "Authorization" not in captured["headers"]
    assert captured["body"]["items"][0]["state"] == "FICTÍCIO"
    assert captured["timeout"] == 120


def test_send_batch_rejects_partial_results(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeHTTP:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit: int) -> bytes:
            return b'{"results": []}'

    monkeypatch.setattr(spike, "urlopen", lambda *_args, **_kwargs: FakeHTTP())
    with pytest.raises(ValueError, match="cardinality mismatch"):
        spike.send_batch([{"state": "FICTÍCIO", "questions": spike.QUESTIONS}])


def test_fixtures_are_synthetic_with_unique_ids_and_known_gold() -> None:
    fixture = (
        Path(spike.__file__).resolve().parent.parent / "tests/fixtures/thx02_spike.jsonl"
    )
    docs = spike.load_jsonl(fixture)
    assert len(docs) == 12
    assert all(doc["gold_outcome"] in spike.OUTCOME_LABELS.values() for doc in docs)
    assert all(doc["gold_winner"] in {"A", "P", "draw", "unknown"} for doc in docs)
    assert any(doc["gold_outcome"] == "não conhecido" for doc in docs)


def test_parse_gold_directory_without_guessing_appeal_polo(tmp_path: Path) -> None:
    fixture = tmp_path / "gold.md"
    fixture.write_text(
        "---\noutcome: não provido\nrecorrente_polo: null\n---\n"
        "ACÓRDÃO. Mantém-se sentença.\n",
        encoding="utf-8",
    )
    docs = spike.load_gold_dir(tmp_path, limit=1)
    assert docs[0]["gold_outcome"] == "não provido"
    assert docs[0]["gold_winner"] == "unknown"


def test_metrics_gate_and_conditional_separately() -> None:
    sample = [
        {
            "id": "1", "outcome": "procedente", "gold_outcome": "procedente",
            "winner": "A", "gold_winner": "A", "winner_direct": "A",
        },
        {
            "id": "2", "outcome": "não provido", "gold_outcome": "não provido",
            "winner": "unknown", "gold_winner": "P", "winner_direct": "P",
        },
        {
            "id": "3", "outcome": "unknown", "gold_outcome": "unknown",
            "winner": "unknown", "gold_winner": "unknown", "winner_direct": "unknown",
        },
    ]
    metrics = spike.summarize(sample)
    assert metrics["gate_recall"] == 0.5
    assert metrics["conditional_accuracy"] == 0.5
    assert metrics["outcome_accuracy"] == 1.0
    assert metrics["direct_winner_accuracy"] == 1.0


def test_main_defaults_to_offline_no_network(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setattr(spike, "send_batch", lambda *_a, **_k: pytest.fail("HTTP attempted"))
    assert spike.main([]) == 0
    message = json.loads(capsys.readouterr().out)
    assert message["mode"] == "offline"
    assert message["decisions"] == 48


def test_explicit_permission_required_for_gold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(spike, "send_batch", lambda *_a, **_k: pytest.fail("HTTP attempted"))
    with pytest.raises(SystemExit):
        spike.main(["--gold-dir", "data/benchmark/decisions", "--live"])


def test_live_synthetic_with_mock_api_writes_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setattr(
        spike, "send_batch",
        lambda items, **_kw: [
            _response("procedente", "nao_aplicavel", "A") for _ in items
        ],
    )
    output = tmp_path / "result.jsonl"
    assert spike.main(["--live", "--limit", "1", "--output", str(output)]) == 0
    records = spike.load_jsonl(output)
    assert len(records) == 1
    assert records[0]["winner"] == "A"
    assert records[0]["gold_winner"] == "A"
    assert "text" not in output.read_text()
    assert json.loads(capsys.readouterr().out)["conditional_accuracy"] == 1.0
