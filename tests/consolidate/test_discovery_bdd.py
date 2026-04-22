"""BDD step definitions for tests/consolidate/features/discovery.feature."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pytest_bdd import given, parsers, scenarios, then, when


if TYPE_CHECKING:
    from pathlib import Path

from causaganha.consolidate import manifest_reader
from tests.consolidate.conftest import write_manifest


scenarios("features/discovery.feature")


@pytest.fixture
def ctx() -> dict:
    return {"dates": [], "counts": {}}


@given(
    parsers.parse("a sync-manifest with {count:d} dates: {d1}, {d2}, {d3}"),
    target_fixture="manifest",
)
def manifest_with_three_dates(tmp_path: Path, count: int, d1: str, d2: str, d3: str) -> Path:
    path = tmp_path / "sync-manifest.csv"
    write_manifest(
        path,
        [
            {"date": d1, "ia_status": "uploaded"},
            {"date": d2, "ia_status": "uploaded"},
            {"date": d3, "ia_status": "uploaded"},
        ],
    )
    return path


@given('all 3 dates have ia_status="uploaded"')
def _noop_already_uploaded() -> None:
    # handled in manifest construction above
    pass


@given(
    parsers.parse("a sync-manifest with {count:d} dates"),
    target_fixture="manifest",
)
def manifest_with_mixed(tmp_path: Path, count: int) -> Path:
    # The following step-defs populate it specifically
    path = tmp_path / "sync-manifest.csv"
    write_manifest(path, [])
    return path


@given(parsers.parse('date {date_str} has ia_status="uploaded"'))
def append_uploaded(manifest: Path, date_str: str) -> None:
    existing = manifest.read_text().strip().splitlines()
    existing.append(f"TJSP,{date_str},uploaded,,200,")
    manifest.write_text("\n".join(existing) + "\n")


@given(parsers.parse('date {date_str} has djen_status="absent" and no ia_status'))
def append_absent(manifest: Path, date_str: str) -> None:
    existing = manifest.read_text().strip().splitlines()
    existing.append(f"TJSP,{date_str},,absent,404,")
    manifest.write_text("\n".join(existing) + "\n")


@given("no sync-manifest file exists", target_fixture="manifest")
def no_manifest(tmp_path: Path) -> Path:
    return tmp_path / "absent.csv"


@given(
    parsers.parse("a sync-manifest with {up:d} uploaded, {ab:d} absent, and {unk:d} unknown rows"),
    target_fixture="manifest",
)
def manifest_with_counts(tmp_path: Path, up: int, ab: int, unk: int) -> Path:
    path = tmp_path / "sync-manifest.csv"
    rows: list[dict] = [
        {"tribunal": "TJSP", "date": f"2026-01-{i + 1:02d}", "ia_status": "uploaded"}
        for i in range(up)
    ]
    rows.extend(
        {"tribunal": "TJRS", "date": f"2026-02-{i + 1:02d}", "djen_status": "absent"}
        for i in range(ab)
    )
    rows.extend(
        {"tribunal": "TJBA", "date": f"2026-03-{i + 1:02d}"}
        for i in range(unk)
    )
    write_manifest(path, rows)
    return path


@when("I list dates with uploads")
def list_dates(manifest: Path, ctx: dict) -> None:
    ctx["dates"] = list(manifest_reader.dates_with_uploads(manifest))


@when("I request the counts summary")
def list_counts(manifest: Path, ctx: dict) -> None:
    ctx["counts"] = manifest_reader.counts_summary(manifest)


@then("all 3 dates appear")
def check_all_three(ctx: dict) -> None:
    assert len(ctx["dates"]) == 3


@then("they are sorted newest-first")
def check_sorted_desc(ctx: dict) -> None:
    assert ctx["dates"] == sorted(ctx["dates"], reverse=True)


@then(parsers.parse("only {date_str} appears"))
def check_only_date(ctx: dict, date_str: str) -> None:
    assert ctx["dates"] == [date_str]


@then("the result is empty")
def check_empty(ctx: dict) -> None:
    assert ctx["dates"] == []


@then(parsers.parse("uploaded count equals {n:d}"))
def check_uploaded(ctx: dict, n: int) -> None:
    assert ctx["counts"]["uploaded"] == n


@then(parsers.parse("absent count equals {n:d}"))
def check_absent(ctx: dict, n: int) -> None:
    assert ctx["counts"]["absent"] == n


@then(parsers.parse("total count equals {n:d}"))
def check_total(ctx: dict, n: int) -> None:
    assert ctx["counts"]["total"] == n
