"""Tests for per-tribunal ratings and leaderboard hygiene.

Covers:
- ``update_lawyer_rating`` keys on ``(oab_number, oab_state, tribunal)``, so the
  same lawyer can hold distinct ratings in distinct leagues.
- ``list_leaderboard`` hides lawyers below the minimum match count and only
  exposes the conservative rating (never raw mu/sigma).
"""

from __future__ import annotations

from pathlib import Path

import ibis
import pytest

from causaganha.storage.repositories.rating import (
    MIN_MATCHES_FOR_LEADERBOARD,
    get_lawyer_rating,
    list_leaderboard,
    update_lawyer_rating,
)


SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent / "src" / "causaganha" / "storage" / "schema.sql"
)


def _init_schema(con):
    sql = SCHEMA_PATH.read_text()
    for statement in sql.split(";"):
        stmt = statement.strip()
        if stmt:
            con.raw_sql(stmt)


@pytest.fixture
def con():
    backend = ibis.duckdb.connect()
    _init_schema(backend)
    return backend


def test_same_lawyer_has_independent_ratings_per_tribunal(con) -> None:
    """A lawyer active in two tribunais should get two independent rating rows."""
    update_lawyer_rating(
        con,
        oab_number="1234",
        oab_state="SP",
        lawyer_name="ADV A",
        mu=26.0,
        sigma=7.5,
        wins=5,
        losses=3,
        tribunal="TJSP",
    )
    update_lawyer_rating(
        con,
        oab_number="1234",
        oab_state="SP",
        lawyer_name="ADV A",
        mu=24.0,
        sigma=8.0,
        wins=2,
        losses=4,
        tribunal="TJMG",
    )

    tjsp = get_lawyer_rating(con, "1234", "SP", tribunal="TJSP")
    tjmg = get_lawyer_rating(con, "1234", "SP", tribunal="TJMG")

    assert tjsp is not None
    assert tjmg is not None
    assert tjsp["mu"] == pytest.approx(26.0)
    assert tjmg["mu"] == pytest.approx(24.0)
    assert tjsp["wins"] == 5
    assert tjmg["wins"] == 2


def test_update_lawyer_rating_upserts_on_same_tribunal(con) -> None:
    """Re-updating the same (oab, state, tribunal) must overwrite, not duplicate."""
    update_lawyer_rating(
        con,
        oab_number="9999",
        oab_state="RJ",
        lawyer_name="ADV B",
        mu=25.0,
        sigma=8.0,
        wins=10,
        losses=10,
        tribunal="TJRJ",
    )
    update_lawyer_rating(
        con,
        oab_number="9999",
        oab_state="RJ",
        lawyer_name="ADV B",
        mu=27.0,
        sigma=6.5,
        wins=15,
        losses=10,
        tribunal="TJRJ",
    )

    df = con.table("lawyer_ratings").to_pandas()
    mine = df[(df["oab_number"] == "9999") & (df["tribunal"] == "TJRJ")]
    assert len(mine) == 1
    assert mine.iloc[0]["mu"] == pytest.approx(27.0)
    assert mine.iloc[0]["wins"] == 15


def test_list_leaderboard_hides_lawyers_below_min_matches(con) -> None:
    """Lawyers below MIN_MATCHES_FOR_LEADERBOARD must not appear publicly."""
    # Below threshold
    update_lawyer_rating(
        con,
        oab_number="100",
        oab_state="SP",
        lawyer_name="Novato",
        mu=30.0,
        sigma=5.0,
        wins=5,
        losses=5,
        tribunal="TJSP",
    )
    # Exactly at threshold
    update_lawyer_rating(
        con,
        oab_number="200",
        oab_state="SP",
        lawyer_name="Veterano",
        mu=27.0,
        sigma=5.0,
        wins=MIN_MATCHES_FOR_LEADERBOARD - 1,
        losses=1,
        tribunal="TJSP",
    )
    # Well above threshold
    update_lawyer_rating(
        con,
        oab_number="300",
        oab_state="SP",
        lawyer_name="Craque",
        mu=28.0,
        sigma=4.0,
        wins=50,
        losses=10,
        tribunal="TJSP",
    )

    rows = list_leaderboard(con, tribunal="TJSP")
    oabs = {r["oab_number"] for r in rows}

    assert "100" not in oabs, "Lawyer below min matches must not appear"
    assert "200" in oabs
    assert "300" in oabs


def test_list_leaderboard_does_not_leak_mu_sigma(con) -> None:
    """Raw mu/sigma are internals; only the conservative rating is public."""
    update_lawyer_rating(
        con,
        oab_number="400",
        oab_state="SP",
        lawyer_name="Expostor",
        mu=35.0,
        sigma=3.0,
        wins=100,
        losses=20,
        tribunal="TJSP",
    )

    rows = list_leaderboard(con, tribunal="TJSP")
    assert rows, "Expected at least one leaderboard row"

    fields = set(rows[0].keys())
    assert "rating" in fields
    assert "mu" not in fields, "Raw mu must not appear in the public leaderboard"
    assert "sigma" not in fields, "Raw sigma must not appear in the public leaderboard"


def test_list_leaderboard_is_ordered_by_conservative_rating(con) -> None:
    """Leaderboard ordering must follow mu - 3*sigma, not raw mu."""
    # Higher mu but very uncertain
    update_lawyer_rating(
        con,
        oab_number="500",
        oab_state="SP",
        lawyer_name="Inflado",
        mu=35.0,
        sigma=8.0,  # mu - 3*sigma = 11
        wins=30,
        losses=5,
        tribunal="TJSP",
    )
    # Lower mu but well-established
    update_lawyer_rating(
        con,
        oab_number="600",
        oab_state="SP",
        lawyer_name="Sólido",
        mu=28.0,
        sigma=2.0,  # mu - 3*sigma = 22
        wins=60,
        losses=20,
        tribunal="TJSP",
    )

    rows = list_leaderboard(con, tribunal="TJSP")
    assert len(rows) == 2
    # The sólid player must rank ahead of the inflated one
    assert rows[0]["oab_number"] == "600"
    assert rows[1]["oab_number"] == "500"


def test_list_leaderboard_scopes_by_tribunal(con) -> None:
    """Leaderboard for TJSP must not include lawyers who only rate at TJMG."""
    update_lawyer_rating(
        con,
        oab_number="700",
        oab_state="SP",
        lawyer_name="Paulista",
        mu=28.0,
        sigma=4.0,
        wins=40,
        losses=10,
        tribunal="TJSP",
    )
    update_lawyer_rating(
        con,
        oab_number="800",
        oab_state="MG",
        lawyer_name="Mineiro",
        mu=29.0,
        sigma=4.0,
        wins=40,
        losses=10,
        tribunal="TJMG",
    )

    sp_rows = list_leaderboard(con, tribunal="TJSP")
    mg_rows = list_leaderboard(con, tribunal="TJMG")

    sp_oabs = {r["oab_number"] for r in sp_rows}
    mg_oabs = {r["oab_number"] for r in mg_rows}

    assert sp_oabs == {"700"}
    assert mg_oabs == {"800"}
