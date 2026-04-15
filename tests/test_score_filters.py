"""Tests for rating-pipeline filters: interlocutórias, non-ratable outcomes,
low-confidence skip, and tribunal segmentation in ``get_unrated_analyses``.

These tests drive an in-memory DuckDB via Ibis so they run without the real
``data/causaganha.duckdb`` file and never touch the network.
"""

from __future__ import annotations

from pathlib import Path

import ibis
import pytest

from causaganha.storage.repositories.analysis import (
    EXCLUDED_DECISION_TYPES,
    RATABLE_OUTCOMES,
    get_unrated_analyses,
)


SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "src" / "causaganha" / "storage" / "schema.sql"
)


def _init_schema(con):
    """Apply the project schema to an in-memory DuckDB connection."""
    sql = SCHEMA_PATH.read_text()
    for statement in sql.split(";"):
        stmt = statement.strip()
        if stmt:
            con.raw_sql(stmt)


def _insert_intimation(con, *, iid: int, tribunal: str) -> None:
    con.con.execute(
        """
        INSERT INTO intimations (
            id, numero_processo, data_disponibilizacao, sigla_tribunal,
            texto, hash
        ) VALUES (?, ?, DATE '2026-04-01', ?, 'corpo da intimação', ?)
        """,
        [iid, f"proc-{iid}", tribunal, f"hash-{iid}"],
    )


def _insert_analysis(
    con,
    *,
    intimation_id: int,
    outcome: str,
    decision_type: str,
    confidence: float,
    winner_oab: str = "1111",
    winner_state: str = "SP",
    loser_oab: str = "2222",
    loser_state: str = "SP",
) -> None:
    con.con.execute(
        """
        INSERT INTO decision_analysis (
            intimation_id,
            winner_lawyer_oab, winner_lawyer_state, winner_party_name,
            loser_lawyer_oab,  loser_lawyer_state,  loser_party_name,
            decision_type, outcome,
            confidence_score, analysis_method, model_used, model_provider
        ) VALUES (
            ?, ?, ?, 'A', ?, ?, 'B', ?, ?, ?, 'llm', 'gemini-2.5-flash', 'google'
        )
        """,
        [
            intimation_id,
            winner_oab,
            winner_state,
            loser_oab,
            loser_state,
            decision_type,
            outcome,
            confidence,
        ],
    )


@pytest.fixture
def con():
    backend = ibis.duckdb.connect()
    _init_schema(backend)
    return backend


def test_ratable_outcomes_are_sentence_level() -> None:
    """Only outcomes that actually resolve the dispute should be ratable."""
    assert "procedente" in RATABLE_OUTCOMES
    assert "improcedente" in RATABLE_OUTCOMES
    assert "parcialmente procedente" in RATABLE_OUTCOMES
    assert "acordo" in RATABLE_OUTCOMES
    # Procedural labels must not leak into the rating pipeline
    assert "unknown" not in RATABLE_OUTCOMES
    assert "extinto sem mérito" not in RATABLE_OUTCOMES


def test_interlocutorias_are_excluded() -> None:
    """Interim orders should be listed as non-ratable decision types."""
    assert "decisão interlocutória" in EXCLUDED_DECISION_TYPES


def test_get_unrated_analyses_filters_non_ratable_outcomes(con) -> None:
    """Only procedente/improcedente/parcialmente procedente should be returned."""
    _insert_intimation(con, iid=1, tribunal="TJSP")
    _insert_intimation(con, iid=2, tribunal="TJSP")
    _insert_intimation(con, iid=3, tribunal="TJSP")

    _insert_analysis(
        con,
        intimation_id=1,
        outcome="procedente",
        decision_type="sentença",
        confidence=0.9,
    )
    _insert_analysis(
        con,
        intimation_id=2,
        outcome="unknown",
        decision_type="sentença",
        confidence=0.9,
    )
    _insert_analysis(
        con,
        intimation_id=3,
        outcome="parcialmente procedente",
        decision_type="sentença",
        confidence=0.75,
    )

    rows = get_unrated_analyses(con, limit=100)
    intimation_ids = {r["intimation_id"] for r in rows}

    assert intimation_ids == {1, 3}


def test_get_unrated_analyses_excludes_interlocutorias(con) -> None:
    """Interlocutórias are procedural and must not enter the rating queue."""
    _insert_intimation(con, iid=10, tribunal="TJSP")
    _insert_intimation(con, iid=11, tribunal="TJSP")

    _insert_analysis(
        con,
        intimation_id=10,
        outcome="procedente",
        decision_type="decisão interlocutória",
        confidence=0.95,
    )
    _insert_analysis(
        con,
        intimation_id=11,
        outcome="procedente",
        decision_type="sentença",
        confidence=0.95,
    )

    rows = get_unrated_analyses(con, limit=100)
    intimation_ids = {r["intimation_id"] for r in rows}

    assert intimation_ids == {11}


def test_get_unrated_analyses_includes_sigla_tribunal(con) -> None:
    """The rating pipeline segments by tribunal, so the join must surface it."""
    _insert_intimation(con, iid=20, tribunal="TJSP")
    _insert_intimation(con, iid=21, tribunal="TJMG")

    _insert_analysis(
        con,
        intimation_id=20,
        outcome="procedente",
        decision_type="sentença",
        confidence=0.9,
    )
    _insert_analysis(
        con,
        intimation_id=21,
        outcome="improcedente",
        decision_type="acórdão",
        confidence=0.9,
    )

    rows = get_unrated_analyses(con, limit=100)
    by_id = {r["intimation_id"]: r for r in rows}

    assert by_id[20]["sigla_tribunal"] == "TJSP"
    assert by_id[21]["sigla_tribunal"] == "TJMG"


def test_interpolate_rating_blends_towards_new() -> None:
    """Mid-confidence updates should move only partway towards the OpenSkill delta."""
    from causaganha.pipeline.score import _interpolate_rating
    from causaganha.scoring.openskill import create_rating, get_openskill_model

    model = get_openskill_model()
    old = create_rating(model, mu=25.0, sigma=8.333)
    new = create_rating(model, mu=27.0, sigma=7.333)

    # Weight 0.0 keeps the prior
    kept = _interpolate_rating(old, new, 0.0, model)
    assert kept.mu == pytest.approx(25.0)
    assert kept.sigma == pytest.approx(8.333)

    # Weight 1.0 applies the full update
    full = _interpolate_rating(old, new, 1.0, model)
    assert full.mu == pytest.approx(27.0)
    assert full.sigma == pytest.approx(7.333)

    # Mid weight is a linear blend
    mid = _interpolate_rating(old, new, 0.5, model)
    assert mid.mu == pytest.approx(26.0)
    assert mid.sigma == pytest.approx(7.833)


def test_interpolate_rating_clamps_weight() -> None:
    """Out-of-range weights must be clamped to [0, 1] so we never extrapolate."""
    from causaganha.pipeline.score import _interpolate_rating
    from causaganha.scoring.openskill import create_rating, get_openskill_model

    model = get_openskill_model()
    old = create_rating(model, mu=25.0, sigma=8.0)
    new = create_rating(model, mu=30.0, sigma=7.0)

    below = _interpolate_rating(old, new, -1.0, model)
    assert below.mu == pytest.approx(25.0)

    above = _interpolate_rating(old, new, 2.5, model)
    assert above.mu == pytest.approx(30.0)
