"""Analyzer for judicial decisions."""
import asyncio
import os
from typing import Iterable

import structlog
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.exceptions import ModelRetry

from causaganha.domain.models_analysis import BatchDecisionAnalysis, DecisionAnalysis


logger = structlog.get_logger()


class DecisionAnalyzer:
    """Analyzer for judicial decisions using Pydantic AI."""

    agent: Agent
    batch_agent: Agent
    api_keys: list[str]
    current_key_index: int
    model_name: str

    def __init__(self, api_key: str | None = None, model: str = "google-gla:gemini-2.5-flash") -> None:
        """Initialize the DecisionAnalyzer.

        Args:
            api_key: Optional API key (deprecated/unused if env var set).
            model: The model name to use.
        """
        self.model_name = model

        # Load multiple API keys from environment
        gemini_keys = os.getenv("GEMINI_API_KEYS", "")
        if gemini_keys:
            self.api_keys = [key.strip() for key in gemini_keys.split(",") if key.strip()]
        else:
            # Fallback to single key
            single_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            self.api_keys = [single_key] if single_key else []

        if not self.api_keys:
            raise ValueError("No API keys available. Set GEMINI_API_KEYS, GEMINI_API_KEY, or GOOGLE_API_KEY")

        self.current_key_index = 0
        logger.info("analyzer_initialized", available_keys=len(self.api_keys))

        # Initialize agents with first key
        self._create_agents()

    def _create_agents(self) -> None:
        """Create or recreate agents with current API key."""
        current_key = self.api_keys[self.current_key_index]

        # Set the API key in environment for pydantic-ai
        os.environ["GOOGLE_API_KEY"] = current_key

        # Single decision agent
        self.agent = Agent(
            model=self.model_name,
            output_type=DecisionAnalysis,
            system_prompt=(
                "You are a legal expert analyzing Brazilian judicial decisions. "
                "Extract structured information about case outcomes, parties, and their legal representatives. "
                "\n\n"
                "CRITICAL INSTRUCTIONS FOR LAWYER IDENTIFICATION:\n"
                "1. When a lawyer has an OAB number listed (e.g., 'ADVOGADO: FULANO - RO1234'), use that OAB.\n"
                "2. When a public attorney (Procuradoria/AGU/PGE) has NO OAB listed, CREATE a synthetic identifier:\n"
                "   - 'PROCURADORIA FEDERAL' → 'PROCURADORIA-FEDERAL-RO'\n"
                "   - 'PROCURADORIA MUNICIPAL DE ARIQUEMES' → 'PROCURADORIA-MUNICIPAL-ARIQUEMES-RO'\n"
                "   - 'PROCURADORIA GERAL DO ESTADO' → 'PGE-RO'\n"
                "   - 'AGU' → 'AGU-RO'\n"
                "3. ALWAYS identify BOTH winner AND loser lawyers when they exist in the text.\n"
                "4. The loser is typically: the defendant who lost, the party ordered to pay, or the appellant whose appeal was denied.\n"
                "\n"
                "Extract: outcome, parties, lawyers (with OAB or synthetic ID), judge name, decision type, and summary."
            ),
        )

        # Batch decision agent
        self.batch_agent = Agent(
            model=self.model_name,
            output_type=BatchDecisionAnalysis,
            system_prompt=(
                "You are a legal expert analyzing Brazilian judicial decisions. "
                "You will receive multiple decision texts to analyze in a single batch. "
                "\n\n"
                "CRITICAL INSTRUCTIONS FOR LAWYER IDENTIFICATION:\n"
                "1. When a lawyer has an OAB number listed (e.g., 'ADVOGADO: FULANO - RO1234'), use that OAB.\n"
                "2. When a public attorney (Procuradoria/AGU/PGE) has NO OAB listed, CREATE a synthetic identifier:\n"
                "   - 'PROCURADORIA FEDERAL' → 'PROCURADORIA-FEDERAL-RO'\n"
                "   - 'PROCURADORIA MUNICIPAL DE ARIQUEMES' → 'PROCURADORIA-MUNICIPAL-ARIQUEMES-RO'\n"
                "   - 'PROCURADORIA GERAL DO ESTADO' → 'PGE-RO'\n"
                "   - 'AGU' → 'AGU-RO'\n"
                "3. ALWAYS identify BOTH winner AND loser lawyers when they exist in the text.\n"
                "4. The loser is typically: the defendant who lost, the party ordered to pay, or the appellant whose appeal was denied.\n"
                "\n"
                "For EACH decision, extract: outcome, parties, lawyers (with OAB or synthetic ID), judge name, decision type, and summary. "
                "CRITICAL: Results MUST be in the EXACT same order as the input texts."
            ),
        )

    def _switch_to_next_key(self) -> bool:
        """Switch to next available API key. Returns True if switched, False if no more keys."""
        if self.current_key_index + 1 < len(self.api_keys):
            self.current_key_index += 1
            logger.info("switching_api_key", index=self.current_key_index, total=len(self.api_keys))
            self._create_agents()
            return True
        return False

    async def analyze_decision(self, content: str | bytes) -> DecisionAnalysis:
        """Analyze a decision and extract structured data with automatic key rotation on 429."""
        logger.info("analyzing_decision", length=len(content))

        if isinstance(content, bytes):
            payload = [
                "Analyze this PDF decision.",
                BinaryContent(data=content, media_type="application/pdf"),
            ]
        else:
            payload = f"Analyze this decision:\n\n{content}"

        # Try with current key, retry with next keys on 429 errors
        for attempt in range(len(self.api_keys)):
            try:
                result = await self.agent.run(payload)
                return result.data
            except Exception as e:
                error_str = str(e)
                # Check for 429 rate limit error
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                    logger.warning(
                        "rate_limit_hit",
                        key_index=self.current_key_index,
                        attempt=attempt + 1,
                        total_keys=len(self.api_keys),
                    )
                    if self._switch_to_next_key():
                        logger.info("retrying_with_next_key")
                        continue
                    else:
                        logger.error("all_keys_exhausted")
                        raise
                else:
                    # Not a rate limit error, propagate immediately
                    raise

        # Should not reach here, but for type safety
        raise RuntimeError("Failed to analyze decision with all available keys")

    async def analyze_bulk(self, texts: Iterable[str]) -> list[DecisionAnalysis]:
        """Analyze multiple decision texts in a single API call with automatic key rotation on 429."""
        texts_list = list(texts)
        if not texts_list:
            return []

        logger.info("analyzing_bulk_decisions", count=len(texts_list))

        user_content = ["Analyze the following decisions in order."]
        for i, text in enumerate(texts_list):
            user_content.append(f"--- DECISION {i + 1} START ---")
            user_content.append(text)
            user_content.append(f"--- DECISION {i + 1} END ---")

        # Try with current key, retry with next keys on 429 errors
        for attempt in range(len(self.api_keys)):
            try:
                result = await self.batch_agent.run(user_content)

                if len(result.data.results) != len(texts_list):
                    logger.warning(
                        "batch_analysis_count_mismatch",
                        expected=len(texts_list),
                        got=len(result.data.results),
                    )

                return result.data.results
            except Exception as e:
                error_str = str(e)
                # Check for 429 rate limit error
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                    logger.warning(
                        "rate_limit_hit_bulk",
                        key_index=self.current_key_index,
                        attempt=attempt + 1,
                        total_keys=len(self.api_keys),
                    )
                    if self._switch_to_next_key():
                        logger.info("retrying_bulk_with_next_key")
                        continue
                    else:
                        logger.error("all_keys_exhausted_bulk")
                        raise
                else:
                    # Not a rate limit error, propagate immediately
                    raise

        # Should not reach here, but for type safety
        raise RuntimeError("Failed to analyze bulk with all available keys")

    async def analyze_batch_concurrent(self, texts: list[str]) -> list[DecisionAnalysis | Exception]:
        """Analyze multiple decisions concurrently (individual calls)."""

        logger.info("starting_concurrent_analysis", count=len(texts))

        tasks = [self.analyze_decision(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return list(results)
