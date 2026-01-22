"""Heuristic-based outcome classifier for Brazilian legal decisions.

Pure function-based approach using regex patterns, embeddings, and legal rules.
No LLM calls - just pattern matching and similarity scoring.
"""

import re
from dataclasses import dataclass
from typing import Literal

import numpy as np
import structlog

from causaganha.v2.analysis.embedding_service_v2 import EmbeddingService


logger = structlog.get_logger()

# Outcome type
Outcome = Literal["WIN", "LOSS", "PARTIAL", "UNKNOWN"]


@dataclass
class OutcomePrediction:
    """Prediction result with confidence and reasoning."""

    outcome: Outcome
    confidence: float  # 0.0 to 1.0
    reasoning: str
    matched_patterns: list[str]
    winner_party: str | None = None
    loser_party: str | None = None


class HeuristicClassifier:
    """Heuristic-based classifier for legal outcome prediction.

    Uses multiple strategies:
    1. Regex patterns for direct outcome phrases
    2. Appeal context analysis (who appealed, what happened)
    3. Embedding similarity with outcome descriptions
    4. Party extraction (autor, réu, INSS, etc.)
    """

    # Direct outcome patterns (highest confidence)
    PROCEDENTE_PATTERNS = [
        r"julgo\s+procedente",
        r"julgo\s+totalmente\s+procedente",
        r"procedente\s+o\s+pedido",
        r"procedentes\s+os\s+pedidos",
        r"dar\s+provimento\s+(?:à|a)\s+apela[çc][ãa]o\s+(?:do|da)\s+autor",
        r"conceder\s+o\s+benef[íi]cio",
        r"condenar\s+(?:o|a)\s+(?:réu|r[ée]|inss|união)",
    ]

    IMPROCEDENTE_PATTERNS = [
        r"julgo\s+improcedente",
        r"improcedente\s+o\s+pedido",
        r"improcedentes\s+os\s+pedidos",
        r"negar\s+provimento\s+(?:à|a)\s+apela[çc][ãa]o\s+(?:do|da)\s+autor",
        r"indefiro\s+o\s+pedido",
        r"indeferir\s+o\s+pedido",
    ]

    PARCIAL_PATTERNS = [
        r"julgo\s+parcialmente\s+procedente",
        r"parcialmente\s+procedente",
        r"procedente\s+em\s+parte",
        r"defiro\s+em\s+parte",
    ]

    # Appeal patterns (need context to determine outcome)
    APPEAL_PATTERNS = {
        "negar_provimento": r"negar\s+provimento\s+(?:ao|à|a)",
        "dar_provimento": r"dar\s+provimento\s+(?:ao|à|a)",
        "negar_provimento_inss": r"negar\s+provimento\s+(?:à|a)\s+apela[çc][ãa]o\s+do\s+inss",
        "negar_provimento_autor": r"negar\s+provimento\s+(?:à|a)\s+apela[çc][ãa]o\s+(?:do|da)\s+autor",
        "dar_provimento_inss": r"dar\s+provimento\s+(?:à|a)\s+apela[çc][ãa]o\s+do\s+inss",
        "manter_sentenca": r"manter\s+(?:a\s+)?senten[çc]a",
    }

    # Party patterns
    PARTY_PATTERNS = {
        "autor": r"(?:autor|autora|requerente|impetrante|apelante|exequente)",
        "reu": r"(?:r[ée]u|r[ée]|requerido|impetrado|apelado|executado)",
        "inss": r"inss|instituto\s+nacional\s+do\s+seguro\s+social",
        "uniao": r"uni[ãa]o|fazenda\s+p[úu]blica",
        "banco": r"banco|caixa\s+econ[ôo]mica",
    }

    # Outcome phrase embeddings for similarity matching
    OUTCOME_PHRASES = {
        "WIN": [
            "o autor ganhou a ação judicial",
            "pedido procedente em favor do requerente",
            "condenação do réu ao pagamento",
            "benefício concedido ao autor",
        ],
        "LOSS": [
            "o autor perdeu a ação judicial",
            "pedido improcedente negado ao autor",
            "autor não teve direito reconhecido",
            "pedido foi indeferido",
        ],
        "PARTIAL": [
            "pedido parcialmente procedente",
            "autor ganhou parte do pedido",
            "condenação parcial do réu",
        ],
    }

    def __init__(self, embedding_service: EmbeddingService | None = None):
        """Initialize classifier.

        Args:
            embedding_service: Optional embedding service for similarity matching.
                              If None, will use regex patterns only.
        """
        self.embedding_service = embedding_service
        self._outcome_embeddings: dict[Outcome, list[list[float]]] | None = None

    async def _initialize_outcome_embeddings(self) -> None:
        """Pre-compute embeddings for outcome phrases."""
        if not self.embedding_service:
            return

        self._outcome_embeddings = {}
        for outcome, phrases in self.OUTCOME_PHRASES.items():
            embeddings = []
            for phrase in phrases:
                emb = await self.embedding_service.embed_text(
                    phrase,
                    task_type="RETRIEVAL_DOCUMENT",
                )
                embeddings.append(emb)
            self._outcome_embeddings[outcome] = embeddings

        logger.info("outcome_embeddings_initialized", num_outcomes=len(self._outcome_embeddings))

    def _regex_match_score(self, text: str, patterns: list[str]) -> tuple[float, list[str]]:
        """Check if text matches any regex patterns.

        Returns:
            (score, matched_patterns) where score is 0.0-1.0
        """
        text_lower = text.lower()
        matched = []

        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                matched.append(pattern)

        if not matched:
            return 0.0, []

        # More matches = higher confidence
        score = min(1.0, len(matched) * 0.3 + 0.7)
        return score, matched

    def _analyze_appeal_context(self, text: str) -> tuple[Outcome, float, str]:
        """Analyze appeal decision context to determine outcome.

        Returns:
            (outcome, confidence, reasoning)
        """
        text_lower = text.lower()

        # Check who appealed
        has_inss = bool(re.search(self.PARTY_PATTERNS["inss"], text_lower))
        has_autor = bool(re.search(self.PARTY_PATTERNS["autor"], text_lower))

        # Check appeal result
        negar_inss = bool(
            re.search(self.APPEAL_PATTERNS["negar_provimento_inss"], text_lower)
        )
        negar_autor = bool(
            re.search(self.APPEAL_PATTERNS["negar_provimento_autor"], text_lower)
        )
        dar_inss = bool(re.search(self.APPEAL_PATTERNS["dar_provimento_inss"], text_lower))
        manter = bool(re.search(self.APPEAL_PATTERNS["manter_sentenca"], text_lower))

        # Logic: "negar provimento à apelação do INSS" = INSS lost = autor won
        if negar_inss:
            return "WIN", 0.85, "INSS appeal denied (NEGAR PROVIMENTO À APELAÇÃO DO INSS)"

        # Logic: "negar provimento à apelação do autor" = autor lost
        if negar_autor:
            return "LOSS", 0.85, "Author appeal denied (NEGAR PROVIMENTO À APELAÇÃO DO AUTOR)"

        # Logic: "dar provimento à apelação do INSS" = INSS won = autor lost
        if dar_inss:
            return "LOSS", 0.85, "INSS appeal granted (DAR PROVIMENTO À APELAÇÃO DO INSS)"

        # Logic: "manter sentença" needs prior context (unknown without it)
        if manter:
            return "UNKNOWN", 0.4, "Sentence maintained but prior outcome unclear"

        return "UNKNOWN", 0.0, "No clear appeal context found"

    async def _embedding_similarity_score(self, text: str) -> tuple[Outcome, float]:
        """Calculate similarity with outcome phrases using embeddings.

        Returns:
            (best_outcome, confidence)
        """
        if not self.embedding_service or not self._outcome_embeddings:
            return "UNKNOWN", 0.0

        # Embed the input text
        text_embedding = await self.embedding_service.embed_text(
            text, task_type="RETRIEVAL_QUERY"
        )
        text_vec = np.array(text_embedding)

        # Find best matching outcome
        best_outcome: Outcome = "UNKNOWN"
        best_score = 0.0

        for outcome, phrase_embeddings in self._outcome_embeddings.items():
            scores = []
            for phrase_emb in phrase_embeddings:
                phrase_vec = np.array(phrase_emb)
                # Cosine similarity
                similarity = np.dot(text_vec, phrase_vec) / (
                    np.linalg.norm(text_vec) * np.linalg.norm(phrase_vec)
                )
                scores.append(similarity)

            # Use max similarity across phrases
            max_score = max(scores) if scores else 0.0
            if max_score > best_score:
                best_score = max_score
                best_outcome = outcome

        # Convert similarity to confidence (0.7+ is good)
        confidence = max(0.0, min(1.0, (best_score - 0.6) / 0.3))

        return best_outcome, confidence

    def _extract_parties(self, text: str) -> tuple[str | None, str | None]:
        """Extract winner and loser party names.

        Returns:
            (winner, loser) or (None, None)
        """
        text_lower = text.lower()

        # Find all parties mentioned
        parties = []

        if re.search(self.PARTY_PATTERNS["autor"], text_lower):
            parties.append("AUTOR")
        if re.search(self.PARTY_PATTERNS["inss"], text_lower):
            parties.append("INSS")
        if re.search(self.PARTY_PATTERNS["uniao"], text_lower):
            parties.append("UNIÃO")
        if re.search(self.PARTY_PATTERNS["banco"], text_lower):
            parties.append("BANCO")

        # If we have 2 parties and one is autor, we can determine winner/loser
        if len(parties) >= 2 and "AUTOR" in parties:
            others = [p for p in parties if p != "AUTOR"]
            return None, None  # Need outcome context to determine

        return None, None

    async def predict(
        self,
        intimacao_text: str,
        dependencies: dict | None = None,
    ) -> OutcomePrediction:
        """Predict outcome using heuristics.

        Args:
            intimacao_text: Text of the legal decision/intimation
            dependencies: Optional context (e.g., prior decisions, party info)

        Returns:
            OutcomePrediction with outcome, confidence, and reasoning
        """
        if dependencies is None:
            dependencies = {}

        # Initialize embeddings on first use
        if self.embedding_service and self._outcome_embeddings is None:
            await self._initialize_outcome_embeddings()

        matched_patterns = []
        scores: dict[Outcome, float] = {"WIN": 0.0, "LOSS": 0.0, "PARTIAL": 0.0, "UNKNOWN": 0.0}
        reasoning_parts = []

        # Strategy 1: Direct regex patterns (highest priority)
        procedente_score, proc_patterns = self._regex_match_score(
            intimacao_text, self.PROCEDENTE_PATTERNS
        )
        if procedente_score > 0:
            scores["WIN"] = max(scores["WIN"], procedente_score)
            matched_patterns.extend(proc_patterns)
            reasoning_parts.append(f"Direct PROCEDENTE pattern (conf={procedente_score:.2f})")

        improcedente_score, improc_patterns = self._regex_match_score(
            intimacao_text, self.IMPROCEDENTE_PATTERNS
        )
        if improcedente_score > 0:
            scores["LOSS"] = max(scores["LOSS"], improcedente_score)
            matched_patterns.extend(improc_patterns)
            reasoning_parts.append(
                f"Direct IMPROCEDENTE pattern (conf={improcedente_score:.2f})"
            )

        parcial_score, parcial_patterns = self._regex_match_score(
            intimacao_text, self.PARCIAL_PATTERNS
        )
        if parcial_score > 0:
            scores["PARTIAL"] = max(scores["PARTIAL"], parcial_score)
            matched_patterns.extend(parcial_patterns)
            reasoning_parts.append(f"Direct PARCIAL pattern (conf={parcial_score:.2f})")

        # Strategy 2: Appeal context analysis
        appeal_outcome, appeal_conf, appeal_reason = self._analyze_appeal_context(
            intimacao_text
        )
        if appeal_conf > 0.5:
            scores[appeal_outcome] = max(scores[appeal_outcome], appeal_conf)
            reasoning_parts.append(f"Appeal analysis: {appeal_reason} (conf={appeal_conf:.2f})")

        # Strategy 3: Embedding similarity (if available)
        if self.embedding_service:
            emb_outcome, emb_conf = await self._embedding_similarity_score(intimacao_text)
            if emb_conf > 0.3:
                scores[emb_outcome] = max(scores[emb_outcome], emb_conf * 0.7)  # Lower weight
                reasoning_parts.append(
                    f"Embedding similarity to {emb_outcome} (conf={emb_conf:.2f})"
                )

        # Determine final outcome (highest score)
        if all(s == 0.0 for s in scores.values()):
            final_outcome: Outcome = "UNKNOWN"
            final_confidence = 0.0
            final_reasoning = "No patterns matched"
        else:
            final_outcome = max(scores.items(), key=lambda x: x[1])[0]
            final_confidence = scores[final_outcome]
            final_reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Multiple heuristics"

        # Extract parties
        winner_party, loser_party = self._extract_parties(intimacao_text)

        logger.info(
            "heuristic_prediction",
            outcome=final_outcome,
            confidence=final_confidence,
            num_patterns=len(matched_patterns),
        )

        return OutcomePrediction(
            outcome=final_outcome,
            confidence=final_confidence,
            reasoning=final_reasoning,
            matched_patterns=matched_patterns[:5],  # Top 5 patterns
            winner_party=winner_party,
            loser_party=loser_party,
        )


async def predict_outcome(
    intimacao_text: str,
    dependencies: dict | None = None,
    use_embeddings: bool = True,
) -> OutcomePrediction:
    """Pure function: Predict legal outcome using heuristics.

    Args:
        intimacao_text: Text of legal decision/intimation
        dependencies: Optional context (prior decisions, party info, etc.)
        use_embeddings: Whether to use embedding similarity (requires model loading)

    Returns:
        OutcomePrediction with outcome, confidence, reasoning

    Example:
        >>> prediction = await predict_outcome(
        ...     "Julgo procedente o pedido para condenar o INSS..."
        ... )
        >>> print(prediction.outcome)  # "WIN"
        >>> print(prediction.confidence)  # 0.85
    """
    # Initialize embedding service if requested
    embedding_service = None
    if use_embeddings:
        embedding_service = await EmbeddingService.create(provider="local")

    # Create classifier and predict
    classifier = HeuristicClassifier(embedding_service=embedding_service)
    prediction = await classifier.predict(intimacao_text, dependencies)

    return prediction
