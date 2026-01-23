"""Analysis strategy enumerations and configuration."""

from enum import Enum


class AnalysisStrategy(str, Enum):
    """Strategy for decision analysis.

    Determines which analysis method(s) to use and when.
    """

    LLM = "llm"
    """Use LLM only (expensive but accurate)."""

    RAG = "rag"
    """Use RAG only (cheap but may have lower accuracy)."""

    HYBRID = "hybrid"
    """Use RAG first, fallback to LLM if confidence is low (optimal)."""

    AUTO = "auto"
    """Automatically choose best strategy (currently same as HYBRID)."""

    @classmethod
    def default(cls) -> "AnalysisStrategy":
        """Get the default strategy.

        Returns:
            Default analysis strategy (HYBRID).
        """
        return cls.HYBRID

    def is_rag_enabled(self) -> bool:
        """Check if RAG is enabled in this strategy.

        Returns:
            True if RAG can be used, False otherwise.
        """
        return self in {self.RAG, self.HYBRID, self.AUTO}

    def is_llm_enabled(self) -> bool:
        """Check if LLM is enabled in this strategy.

        Returns:
            True if LLM can be used, False otherwise.
        """
        return self in {self.LLM, self.HYBRID, self.AUTO}

    def requires_fallback(self) -> bool:
        """Check if this strategy uses LLM fallback logic.

        Returns:
            True if hybrid fallback logic should be used, False otherwise.
        """
        return self in {self.HYBRID, self.AUTO}
