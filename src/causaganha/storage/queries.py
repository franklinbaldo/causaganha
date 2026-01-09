"""Database queries.

DEPRECATED: Use IntimationRepository in src/causaganha.storage.repositories.intimation.py instead.
This module is kept for temporary backward compatibility during refactoring.
"""

from typing import Any

from ibis import BaseBackend

from causaganha.domain.models import Intimation
from causaganha.storage.repositories.analysis import AnalysisRepository
from causaganha.storage.repositories.intimation import IntimationRepository


async def store_intimations(con: BaseBackend, intimations: list[Intimation]) -> None:
    """Store a list of intimations in the database asynchronously.

    Deprecated. Use IntimationRepository.store_intimations.
    """
    repo = IntimationRepository(con)
    await repo.store_intimations(intimations)


async def get_unanalyzed_intimations(con: BaseBackend, limit: int = 100) -> list[dict[str, Any]]:
    """Fetch intimations that have not been analyzed yet.

    Deprecated. Use IntimationRepository.get_unanalyzed_intimations.
    """
    repo = IntimationRepository(con)
    return await repo.get_unanalyzed_intimations(limit)


async def store_analysis_result(con: BaseBackend, result: dict[str, Any]) -> None:
    """Store analysis result.

    Deprecated. Use AnalysisRepository.store_analysis_result.
    """
    repo = AnalysisRepository(con)
    await repo.store_analysis_result(result)
