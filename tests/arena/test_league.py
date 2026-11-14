from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from causaganha.arena.league import League, agreement, replay
from causaganha.arena.models import Disposition, Level, Rules, Season
from causaganha_cli.__main__ import app


def disposition(share=1):
    return {"merits": share is not None, "claimant_share": share}


def vote(competitor, share=1):
    return {
        "competitor": competitor,
        "text": "Fundamentação de demonstração.",
        "disposition": disposition(share),
    }


def match(case, claimant="a", defendant="b", panels=None, share=1):
    return {
        "case_id": case,
        "claimant": {"competitor": claimant, "text": "Pedido de demonstração."},
        "defendant": {"competitor": defendant, "text": "Defesa de demonstração."},
        "panels": panels or [],
        "anchor": {
            "court": "stj",
            "source_url": "https://example.org/demo",
            "document_sha256": "0" * 64,
            "disposition": disposition(share),
        },
    }


def season(rounds, **rules):
    return Season.model_validate(
        {
            "demonstration": True,
            "rules": {"min_cases": 1, **rules},
            "competitors": [{"id": c, "model": f"demo-{c}", "revision": "v1"} for c in "abcd"],
            "rounds": [{"id": str(i), "matches": matches} for i, matches in enumerate(rounds)],
        }
    )


def test_earned_career_and_separate_superior_courts():
    result = replay(
        season(
            [
                [match("1"), match("2", "c", "d")],
                [match("3", "c", "d", [{"level": "juizo", "votes": [vote("a")]}])],
                [
                    match(
                        "4",
                        "b",
                        "d",
                        [
                            {"level": "juizo", "votes": [vote("c")]},
                            {"level": "tribunal", "votes": [vote("a")]},
                        ],
                    )
                ],
            ]
        )
    )
    assert result["history"][0]["seats"][Level.JUIZO] == ["a", "c"]
    assert result["history"][0]["seats"][Level.TRIBUNAL] == []
    assert result["seats"][Level.STJ] == ["a"]
    assert result["seats"][Level.STF] == ["a"]
    assert result["standings"][0]["reward"] == 7


def test_promotion_cannot_be_used_in_same_round():
    with pytest.raises(ValueError, match="sem habilitação"):
        replay(
            season(
                [
                    [
                        match("1"),
                        match(
                            "2",
                            "c",
                            "d",
                            [
                                {"level": "juizo", "votes": [vote("a")]},
                            ],
                        ),
                    ]
                ]
            )
        )


def test_repeated_case_cannot_manufacture_promotion():
    with pytest.raises(ValueError, match="Mesmo caso"):
        replay(season([[match("1")], [match("1")]], min_cases=3))


@pytest.mark.parametrize("claimant,judges", [("a", ["a"]), ("a", ["unknown"])])
def test_conflicts_and_unregistered_participants(claimant, judges):
    with pytest.raises(ValueError):
        replay(
            season(
                [
                    [
                        match(
                            "1",
                            claimant,
                            "b",
                            [
                                {"level": "juizo", "votes": [vote(j) for j in judges]},
                            ],
                        )
                    ]
                ]
            )
        )


def test_dissent_scores_against_superior_not_local_majority():
    league = League(Rules(min_cases=1), list("abcdefg"))
    league.qualifications = {c: set(Level) for c in league.competitors}
    record = match(
        "1",
        "a",
        "b",
        [
            {"level": "juizo", "votes": [vote("c")]},
            {"level": "tribunal", "votes": [vote("d", 0), vote("e", 0), vote("f", 1)]},
        ],
    )
    league.play(
        Season.model_validate(
            {**season([[match("x")]]).model_dump(), "rounds": [{"id": "1", "matches": [record]}]}
        )
        .rounds[0]
        .matches[0],
        league.seats(),
    )
    assert league.average("f", Level.TRIBUNAL) == 1
    assert league.average("d", Level.TRIBUNAL) == 0
    assert league.average("c", Level.JUIZO) == 0


def test_seats_are_scarce_and_reassigned_by_performance():
    league = League(Rules(stf_seats=11, stj_seats=35), [f"m{i:02}" for i in range(40)])
    league.qualifications = {c: set(Level) for c in league.competitors}
    assert len(league.seats()[Level.STF]) == 11
    assert len(league.seats()[Level.STJ]) == 35
    league.record("m39", Level.STF, "case", 1)
    assert league.seats()[Level.STF][0] == "m39"
    assert "m10" not in league.seats()[Level.STF]


def test_procedural_outcomes_do_not_become_merits_losses():
    result = replay(season([[match("1", share=None)]]))
    assert result["standings"][0]["roles"][Level.ADVOCACIA]["cases"] == 0
    assert (
        agreement(
            Disposition(merits=False, claimant_share=None),
            Disposition(merits=True, claimant_share=0),
        )
        == 0
    )


def test_tied_panel_rejected():
    league = League(Rules(), list("abcd"))
    league.qualifications = {c: set(Level) for c in league.competitors}
    record = match("1", panels=[{"level": "juizo", "votes": [vote("c"), vote("d", 0)]}])
    with pytest.raises(ValueError, match="sem maioria"):
        league.play(season([[record]]).rounds[0].matches[0], league.seats())


@pytest.mark.parametrize("share", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_scores_rejected(share):
    with pytest.raises(ValidationError):
        Disposition(merits=True, claimant_share=share)


def test_cli_replays_example_and_outputs_schema(capsys):
    app(["arena", "avaliar", "examples/arena/demonstracao.json"], result_action="return_value")
    report = json.loads(capsys.readouterr().out)
    assert report["demonstration"] is True
    assert report["seats"]["stf"] == ["a"]
    app(["arena", "contrato"], result_action="return_value")
    assert "rounds" in json.loads(capsys.readouterr().out)["properties"]


def test_example_roundtrip_and_no_unknown_fields():
    payload = json.loads(Path("examples/arena/demonstracao.json").read_text())
    assert replay(Season.model_validate(payload)) == replay(
        Season.model_validate(deepcopy(payload))
    )
    payload["typo"] = True
    with pytest.raises(ValidationError):
        Season.model_validate(payload)


def test_minimum_distinct_cases_before_promotion():
    result = replay(season([[match("1"), match("2")], [match("3")]], min_cases=3))
    assert result["history"][0]["seats"][Level.JUIZO] == []
    assert result["history"][1]["seats"][Level.JUIZO] == ["a"]


def test_duplicate_checkpoint_cannot_occupy_multiple_seats():
    payload = season([[match("1")]]).model_dump()
    payload["competitors"][1]["model"] = payload["competitors"][0]["model"]
    with pytest.raises(ValidationError, match="duplicados"):
        Season.model_validate(payload)


def test_superior_judge_scores_against_real_anchor():
    league = League(Rules(), list("abcdefg"))
    league.qualifications = {c: set(Level) for c in league.competitors}
    record = match(
        "1",
        panels=[
            {"level": "juizo", "votes": [vote("c")]},
            {"level": "tribunal", "votes": [vote("d")]},
            {"level": "stj", "votes": [vote("e", 0)]},
        ],
    )
    league.play(season([[record]]).rounds[0].matches[0], league.seats())
    assert league.average("e", Level.STJ) == 0
    assert league.average("d", Level.TRIBUNAL) == 0
    assert league.average("c", Level.JUIZO) == 1
