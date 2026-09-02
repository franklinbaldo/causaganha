"""Bound the public decision-search surface before any remote DuckDB scan.

The JURIS archive is partitioned by month/type. A thematic search that blindly
opens every historical Parquet would be technically valid and operationally
bad. This module makes the scan budget part of the product contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from causaganha.decisoes.published import PublishedDecisionDataset


DecisionSource = Literal["todas", "juris", "stj", "tcu"]
_MAX_JURIS_MONTHS = 6


class DecisionSearchBudgetError(ValueError):
    """The requested thematic search exceeds the supported public scan budget."""


@dataclass(frozen=True, slots=True)
class DecisionSearchPlan:
    """Datasets selected for one bounded decision/content query."""

    juris: tuple[PublishedDecisionDataset, ...]
    stj: tuple[PublishedDecisionDataset, ...]
    data_inicio: date | None
    data_fim: date | None
    tcu: tuple[PublishedDecisionDataset, ...] = ()
    max_juris_months: int = _MAX_JURIS_MONTHS

    @property
    def total_datasets(self) -> int:
        return len(self.juris) + len(self.stj) + len(self.tcu)


def _parse_iso_date(value: str | None, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        msg = f"{field} deve estar em formato ISO AAAA-MM-DD."
        raise DecisionSearchBudgetError(msg) from exc


def _month_index(value: date) -> int:
    return value.year * 12 + value.month - 1


def _month_span(start: date, end: date) -> int:
    return _month_index(end) - _month_index(start) + 1


def _period_index(periodo: str) -> int:
    try:
        year_text, month_text = periodo.split("-", maxsplit=1)
        year = int(year_text)
        month = int(month_text)
    except (TypeError, ValueError) as exc:
        msg = f"Período publicado inválido: {periodo!r}."
        raise DecisionSearchBudgetError(msg) from exc
    if not 1 <= month <= 12:
        msg = f"Período publicado inválido: {periodo!r}."
        raise DecisionSearchBudgetError(msg)
    return year * 12 + month - 1


def plan_decision_search(
    datasets: list[PublishedDecisionDataset],
    *,
    fonte: DecisionSource = "todas",
    data_inicio: str | None = None,
    data_fim: str | None = None,
    consulta_por_cnj: bool = False,
) -> DecisionSearchPlan:
    """Select datasets while refusing an unbounded thematic JURIS scan.

    A CNJ lookup should normally use ``processo_consultar`` and its thin index;
    ``consulta_por_cnj=True`` only records that a caller already has an equally
    bounded source-selection path. The first thematic search surface requires a
    complete date interval whenever JURIS participates, capped at six calendar
    months. STJ and TCU are each one canonical dataset and can be
    date-filtered inside DuckDB.
    """
    start = _parse_iso_date(data_inicio, "data_inicio")
    end = _parse_iso_date(data_fim, "data_fim")
    if start and end and start > end:
        msg = "data_inicio não pode ser posterior a data_fim."
        raise DecisionSearchBudgetError(msg)

    wants_juris = fonte in {"todas", "juris"}
    if wants_juris and not consulta_por_cnj:
        if start is None or end is None:
            msg = (
                "Busca temática em JURIS exige data_inicio e data_fim para limitar "
                "o scan dos Parquets publicados."
            )
            raise DecisionSearchBudgetError(msg)
        span = _month_span(start, end)
        if span > _MAX_JURIS_MONTHS:
            msg = (
                f"Busca temática em JURIS aceita no máximo {_MAX_JURIS_MONTHS} "
                "meses por consulta; divida o período."
            )
            raise DecisionSearchBudgetError(msg)

    juris = [item for item in datasets if item.fonte == "juris"] if wants_juris else []
    if juris and start is not None and end is not None:
        start_month = _month_index(start)
        end_month = _month_index(end)
        juris = [
            item
            for item in juris
            if item.periodo is not None and start_month <= _period_index(item.periodo) <= end_month
        ]

    stj = [item for item in datasets if item.fonte == "stj"] if fonte in {"todas", "stj"} else []
    tcu = [item for item in datasets if item.fonte == "tcu"] if fonte in {"todas", "tcu"} else []
    return DecisionSearchPlan(
        juris=tuple(juris),
        stj=tuple(stj),
        tcu=tuple(tcu),
        data_inicio=start,
        data_fim=end,
    )
