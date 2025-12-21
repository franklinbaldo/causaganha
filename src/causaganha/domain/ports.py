"""Domain ports and interfaces."""

from typing import Any, Protocol

from causaganha.domain.models import Intimation


class IntimationRepository(Protocol):
    """Protocol for intimation storage and retrieval."""

    async def get_unanalyzed_intimations(self, limit: int = 100) -> list[Intimation]:
        """Fetch intimations that have not been analyzed yet."""
        ...

    async def store_analysis_results_batch(self, results: list[dict[str, Any]]) -> None:
        """Store analysis results in batch."""
        ...
