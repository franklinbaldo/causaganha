"""Thematic decision searches cannot accidentally become archive-wide scans."""

from __future__ import annotations

import pytest

from causaganha.decisoes.planner import (
    DecisionSearchBudgetError,
    plan_decision_search,
)
from causaganha.decisoes.published import PublishedDecisionDataset


def _datasets() -> list[PublishedDecisionDataset]:
    return [
        PublishedDecisionDataset(
            fonte="juris",
            url="https://example/2026-01.parquet",
            periodo="2026-01",
        ),
        PublishedDecisionDataset(
            fonte="juris",
            url="https://example/2026-02.parquet",
            periodo="2026-02",
        ),
        PublishedDecisionDataset(
            fonte="juris",
            url="https://example/2026-08.parquet",
            periodo="2026-08",
        ),
        PublishedDecisionDataset(
            fonte="stj",
            url="https://example/stj.parquet",
        ),
        PublishedDecisionDataset(
            fonte="tcu",
            url="https://example/tcu.parquet",
        ),
    ]


def test_thematic_juris_requires_both_dates() -> None:
    with pytest.raises(DecisionSearchBudgetError, match="data_inicio e data_fim"):
        plan_decision_search(_datasets(), fonte="juris", data_inicio="2026-01-01")


def test_thematic_juris_refuses_more_than_six_calendar_months() -> None:
    with pytest.raises(DecisionSearchBudgetError, match="no máximo 6 meses"):
        plan_decision_search(
            _datasets(),
            fonte="juris",
            data_inicio="2026-01-01",
            data_fim="2026-07-01",
        )


def test_date_window_selects_only_published_juris_partitions_in_range() -> None:
    plan = plan_decision_search(
        _datasets(),
        fonte="todas",
        data_inicio="2026-01-15",
        data_fim="2026-02-20",
    )

    assert [item.periodo for item in plan.juris] == ["2026-01", "2026-02"]
    assert [item.fonte for item in plan.stj] == ["stj"]
    assert [item.fonte for item in plan.tcu] == ["tcu"]
    assert plan.total_datasets == 4


def test_stj_only_does_not_require_juris_partition_window() -> None:
    plan = plan_decision_search(_datasets(), fonte="stj")

    assert plan.juris == ()
    assert len(plan.stj) == 1


def test_tcu_only_selects_tcu_datasets_without_requiring_a_date_window() -> None:
    plan = plan_decision_search(_datasets(), fonte="tcu")

    assert plan.juris == ()
    assert plan.stj == ()
    assert len(plan.tcu) == 1
    assert plan.tcu[0].fonte == "tcu"
    assert plan.total_datasets == 1


def test_cnj_path_may_skip_thematic_window_because_selection_is_already_bounded() -> None:
    plan = plan_decision_search(
        _datasets(),
        fonte="juris",
        consulta_por_cnj=True,
    )

    assert len(plan.juris) == 3


def test_invalid_or_inverted_dates_are_rejected_before_query_execution() -> None:
    with pytest.raises(DecisionSearchBudgetError, match="formato ISO"):
        plan_decision_search(
            _datasets(),
            fonte="juris",
            data_inicio="01/01/2026",
            data_fim="2026-02-01",
        )

    with pytest.raises(DecisionSearchBudgetError, match="posterior"):
        plan_decision_search(
            _datasets(),
            fonte="juris",
            data_inicio="2026-03-01",
            data_fim="2026-02-01",
        )
