"""Domain interfaces and protocols."""

from datetime import date
from typing import Any, Protocol

from causaganha.domain.models import Intimation


class AnalysisSourceProtocol(Protocol):
    """Protocol for accessing analysis results."""

    async def get_unscored_analyses(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch analyses that have not been scored yet.

        Args:
            limit: Maximum number of analyses to fetch.

        Returns:
            List of analysis records as dictionaries.
        """
        ...

    async def mark_analyses_scored(self, ids: list[Any]) -> None:
        """Mark analyses as having been scored.

        Args:
            ids: List of analysis IDs to mark.
        """
        ...


class LawyerRatingStoreProtocol(Protocol):
    """Protocol for accessing and storing lawyer ratings."""

    async def get_lawyer_ratings(self, oabs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """Fetch existing ratings for a list of lawyers.

        Args:
            oabs: List of (oab_number, oab_state) tuples.

        Returns:
            List of rating records as dictionaries.
        """
        ...

    async def save_lawyer_ratings(self, ratings: list[dict[str, Any]]) -> None:
        """Save or update lawyer ratings.

        Args:
            ratings: List of rating records to save.
        """
        ...


class CourtClientProtocol(Protocol):
    """Protocol for fetching intimations from a court source."""

    async def get_intimations_by_court(
        self,
        sigla_tribunal: str,
        data_disponibilizacao_inicio: date | None = None,
        data_disponibilizacao_fim: date | None = None,
        pagina: int = 1,
        itens_por_pagina: int = 100,
    ) -> list[Intimation]:
        """Fetch intimations from the court API.

        Args:
            sigla_tribunal: The court acronym (e.g., TJRO).
            data_disponibilizacao_inicio: Start date.
            data_disponibilizacao_fim: End date.
            pagina: Page number.
            itens_por_pagina: Items per page.

        Returns:
            List of domain Intimation objects.
        """
        ...

    async def close(self) -> None:
        """Close the underlying client."""
        ...
