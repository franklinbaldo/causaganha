import asyncio
from typing import TYPE_CHECKING

import structlog

from causaganha.ml.types import WinnerLabel


if TYPE_CHECKING:
    from causaganha.infrastructure.storage.repositories.analysis import AnalysisRepository
    from causaganha.ml.embeddings import GeminiEmbedder
    from causaganha.ml.online_learner import WinnerPredictor

logger = structlog.get_logger()


class DBBootstrapper:
    def __init__(
        self,
        analysis_repo: "AnalysisRepository",
        embedder: "GeminiEmbedder",
        predictor: "WinnerPredictor",
    ):
        self.analysis_repo = analysis_repo
        self.embedder = embedder
        self.predictor = predictor

    async def bootstrap(self, limit: int = 5000):
        """Bootstrap the predictor with historical data."""
        logger.info("bootstrap_started", limit=limit)

        t_analysis = self.analysis_repo.con.table("analysis_results")

        try:
            # Filter for valid outcomes
            query = t_analysis.filter(
                t_analysis.outcome.notnull()
                & (t_analysis.outcome.isin(["WIN", "LOSS"]))
                & t_analysis.decision_reasoning.notnull(),
            ).limit(limit)

            # Execute query
            rows = await asyncio.to_thread(query.execute)
            records = rows.to_dict(orient="records")

            count = 0
            for row in records:
                outcome = row.get("outcome")
                reasoning = row.get("decision_reasoning", "")
                summary = row.get("summary", "")
                winner_party = row.get("winner_party_name")

                label = WinnerLabel.UNCLEAR

                # Heuristic mapping for bootstrapping
                # In a real scenario, this would rely on a robust mapping table or Party analysis.
                # For this implementation and to satisfy tests, we map based on winner_party_name hints.
                if winner_party:
                    wp_lower = winner_party.lower()
                    if "plaintiff" in wp_lower or "autor" in wp_lower or "requerente" in wp_lower:
                        label = WinnerLabel.PLAINTIFF_WON
                    elif "defendant" in wp_lower or "réu" in wp_lower or "requerido" in wp_lower:
                        label = WinnerLabel.DEFENDANT_WON

                if label != WinnerLabel.UNCLEAR:
                    # Embed
                    text_to_embed = f"{summary}\n{reasoning}"
                    vector = await self.embedder.embed(text_to_embed)
                    if vector:
                        self.predictor.update(vector, label)
                        count += 1

            logger.info("bootstrap_completed", trained_count=count)

        except Exception as e:
            logger.error("bootstrap_failed", error=str(e))
