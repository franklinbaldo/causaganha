"""Domain interfaces and protocols."""

from typing import Any, Protocol

from causaganha.domain.models import Intimation


class IntimationRepositoryProtocol(Protocol):
    """Protocol for intimation storage."""

    async def store_intimations(self, intimations: list[Intimation]) -> None:
        """Store a list of intimations."""
        ...

    async def get_unanalyzed_intimations(self, limit: int = 100) -> list[Intimation]:
        """Fetch intimations that have not been analyzed yet."""
        ...

    async def get_unarchived_intimations(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch intimations that have not been archived yet."""
        ...

    async def mark_as_archived(self, intimation_id: str, ia_url: str) -> None:
        """Mark an intimation as archived."""
        ...

    async def get_all_intimations(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch all intimations."""
        ...


class AnalysisRepositoryProtocol(Protocol):
    """Protocol for analysis results storage."""

    async def store_analysis_result(self, result: dict[str, Any]) -> None:
        """Store analysis result."""
        ...

    async def store_analysis_results_batch(self, results: list[dict[str, Any]]) -> None:
        """Store analysis results in batch."""
        ...

    async def get_unscored_analyses(self, limit: int = 100) -> list[dict[str, Any]]:
        """Fetch unscored analyses."""
        ...

    async def mark_analyses_scored(self, ids: list[Any]) -> None:
        """Mark analyses as scored."""
        ...


class LawyerRatingRepositoryProtocol(Protocol):
    """Protocol for lawyer rating storage."""

    async def get_lawyer_ratings(self, oabs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """Fetch ratings for a list of lawyers (oab, state)."""
        ...

    async def save_lawyer_ratings(self, ratings: list[dict[str, Any]]) -> None:
        """Save updated lawyer ratings."""
        ...
