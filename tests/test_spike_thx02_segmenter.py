"""Offline tests of the experimental THX-02 region segmentation adapter."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from scripts import spike_thx02_segmenter as spike


def test_split_preserves_offsets_and_no_overlap():
    s = "  I - RELATÓRIO\nTexto com espaços.\n\nII - FUNDAMENTAÇÃO\nA lei se aplica.\n\nIII - DISPOSITIVO\nJulgo procedente. "
    units = spike.split_units(s, max_chars=160)
    assert len(units) >= 3
    assert all(s[u.start : u.end] == u.text for u in units)
    assert all(a.end <= b.start for a, b in zip(units, units[1:], strict=False))
    assert "RELATÓRIO" in "".join(u.text for u in units)


def test_no_markup_or_source_rewrite_for_very_long_prose():
    s = "Palavra " * 500
    units = spike.split_units(s, max_chars=100)
    assert len(units) > 1
    assert all(s[u.start : u.end] == u.text for u in units)
    assert all(len(u.text) <= 100 for u in units)


def test_split_empty():
    assert spike.split_units("   \n ") == []


def test_max_chars_validation():
    with pytest.raises(ValueError):
        spike.split_units("abc", max_chars=79)


def test_payload_matches_api_and_counts_decisions():
    s = "RELATÓRIO\n\nDISPOSITIVO\nJulgo procedente."
    units = spike.split_units(s)
    payload = spike.request_items(s, units)
    assert payload["model"] == "thx-02"
    assert len(payload["items"]) == len(units)
    for item in payload["items"]:
        assert "model" not in item
        assert item["questions"]["papel"]["type"] == "choice"
        assert item["questions"]["papel"]["criteria"] == spike.ROLES


def test_anonymous_limit_rejected():
    units = [spike.Unit(i, i + 1, "x") for i in range(61)]
    with pytest.raises(ValueError, match="too many"):
        spike.request_items("x" * 61, units)


def _answer(label="dispositivo", p=0.92):
    remainder = (1-p)/(len(spike.ROLES)-1) if type(p) in (int, float) else 0.0
    probabilities = {name: remainder for name in spike.ROLES}
    probabilities[label] = p
    return {"answers": {"papel": {"type": "choice", "choice": label, "probabilities": probabilities}}}


def test_parses_batch_and_abstains_below_threshold():
    units = [spike.Unit(0, 3, "abc"), spike.Unit(4, 7, "def")]
    got = spike.parse_results(units, {"results": [_answer(p=0.99), _answer(p=0.41)]}, threshold=0.8)
    assert [p.label for p in got] == ["dispositivo", "unknown"]
    assert [p.status for p in got] == ["accepted", "abstained"]
    assert got[0].probability == 0.99


def test_api_error_is_unavailable_not_inferred():
    units = [spike.Unit(0, 3, "abc")]
    got = spike.parse_results(units, {"results": [{"error": "overloaded"}]})
    assert got[0].status == "unavailable"
    assert got[0].label == "unknown"


@pytest.mark.parametrize("bad", ["wrong", True, 2.0, -1.0, None])
def test_invalid_probabilities_fail_closed(bad):
    units = [spike.Unit(0, 3, "abc")]
    got = spike.parse_results(units, {"results": [_answer(p=bad)]})
    assert got[0].status == "unavailable"


def test_batch_length_mismatch_is_error():
    with pytest.raises(ValueError, match="unexpected"):
        spike.parse_results([spike.Unit(0, 3, "abc")], {"results": []})


def test_adjacent_accepted_regions_merge_without_gap_loss():
    p = [
        spike.Prediction(0, 4, "dispositivo", 0.93, "accepted"),
        spike.Prediction(5, 9, "dispositivo", 0.91, "accepted"),
        spike.Prediction(10, 14, "unknown", 0.71, "abstained"),
        spike.Prediction(15, 22, "dispositivo", 0.98, "accepted"),
    ]
    regions = spike.merge_regions(p)
    assert [(r["start"], r["end"]) for r in regions] == [(0, 9), (15, 22)]
    assert regions[0]["min_probability"] == 0.91


def test_gold_audit_does_not_claim_model_quality():
    doc = {"text": "I - RELATÓRIO\nAção ajuizada.\n\nII - FUNDAMENTAÇÃO\nRequisitos provados.", "label": [
        {"category": "relatorio_inicio", "start": 4, "end": 13},
        {"category": "fundamentacao_legal", "start": 50, "end": 58},
    ]}
    result = spike.boundary_ceiling([doc], tolerance=30)
    assert result["documents"] == 1
    assert result["gold_structural_boundaries"] == 1
    assert result["ceiling_recall"] == 1
    assert "not THX" in result["interpretation"]


def test_fixture_and_offline_cli(monkeypatch, capsys):
    p = Path(__file__).parent / "fixtures" / "thx02_segmenter_synthetic.jsonl"
    monkeypatch.setattr("sys.argv", ["spike_thx02_segmenter.py", "--source", str(p)])
    assert spike.main() == 0
    got = json.loads(capsys.readouterr().out)
    assert got["transmitted"] is False
    assert got["regions"] == []
    assert got["decisions_requested"] > 0


def test_no_network_in_unit_suite(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("must not make live requests in offline mode")

    monkeypatch.setattr(httpx.Client, "post", deny)
    p = Path(__file__).parent / "fixtures" / "thx02_segmenter_synthetic.jsonl"
    monkeypatch.setattr("sys.argv", ["spike_thx02_segmenter.py", "--source", str(p)])
    assert spike.main() == 0


def test_live_custom_path_requires_explicit_opt_in(monkeypatch):
    monkeypatch.setattr("sys.argv", ["spike_thx02_segmenter.py", "--live", "--source", "other.jsonl"])
    with pytest.raises(SystemExit):
        spike.main()


def test_live_http_contract_with_fake_response(monkeypatch, capsys):
    calls = []

    def mock_post(_self, url, *, headers, json):
        calls.append({"url": url, "headers": headers, "payload": json})
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"results": [_answer("dispositivo", 0.95) for _ in json["items"]]},
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    p = Path(__file__).parent / "fixtures" / "thx02_segmenter_synthetic.jsonl"
    monkeypatch.setattr("sys.argv", ["spike_thx02_segmenter.py", "--live", "--source", str(p)])
    assert spike.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["transmitted"] is True
    assert report["regions"][0]["label"] == "dispositivo"
    assert calls[0]["payload"]["model"] == "thx-02"
    assert "Authorization" not in calls[0]["headers"] or calls[0]["headers"]["Authorization"].startswith("Bearer ")