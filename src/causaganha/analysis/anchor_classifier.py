"""Anchor-based k-NN classifier for judicial outcome classification.

Uses a hand-curated + auto-growing anchor set of labeled decisions to
classify new decisions via cosine similarity nearest-neighbor voting.

The anchor set is stored as a Parquet file with pre-computed embeddings,
making inference fast (no API call, just matrix multiply on CPU).

Architecture:
    1. Load anchor_set.parquet → pre-computed embeddings + labels
    2. New decision text → LocalEmbedder → query embedding
    3. Cosine similarity vs. all anchors → top-k neighbors
    4. Weighted vote by similarity → OutcomeDistribution

The anchor set grows automatically when:
    - LLM fallback is triggered (high confidence LLM labels added)
    - A 2% random sample is classified by LLM
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import structlog

from causaganha.analysis.bayesian_fusion import (
    OUTCOME_KEYS,
    OutcomeDistribution,
    normalize,
)


if TYPE_CHECKING:
    import pandas as pd

logger = structlog.get_logger()

# Default location of the anchor set relative to project root
DEFAULT_ANCHOR_PATH = Path("data/anchor_set.parquet")

# Columns expected in anchor_set.parquet
ANCHOR_SCHEMA = {
    "numero_processo": str,
    "texto_truncado": str,   # first 1000 chars of decision text
    "outcome": str,          # one of OUTCOME_KEYS
    "confidence": float,     # annotation confidence (LLM or manual)
    "annotation_src": str,   # "llm" | "manual" | "auto"
    "embedding": object,     # bytes or list[float] — 256-dim EmbeddingGemma
}


class AnchorClassifier:
    """k-NN classifier using pre-computed embeddings from an anchor set.

    Inference is a single cosine similarity computation (matrix multiply)
    followed by a weighted vote — runs in < 5ms even for 10k anchors.

    Args:
        anchor_path: Path to anchor_set.parquet.
        k: Number of nearest neighbors for voting. Default: 7.
        min_sim: Minimum cosine similarity to include a neighbor in the vote.
            Neighbors below this threshold are excluded. Default: 0.60.

    Raises:
        FileNotFoundError: If anchor_path does not exist. Run
            ``scripts/build_anchor_set.py`` to create it.
    """

    def __init__(
        self,
        anchor_path: Path | str = DEFAULT_ANCHOR_PATH,
        k: int = 7,
        min_sim: float = 0.60,
    ) -> None:
        self.anchor_path = Path(anchor_path)
        self.k = k
        self.min_sim = min_sim

        self._embeddings: np.ndarray | None = None   # (N, D) float32
        self._labels: list[str] | None = None         # len N
        self._confidences: list[float] | None = None  # len N
        self._loaded = False

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load anchor set from parquet into memory.

        Called lazily on first classify() call. Can be called explicitly
        to pre-warm before processing a batch.

        Raises:
            FileNotFoundError: If the parquet file does not exist.
        """
        import pandas as pd  # noqa: PLC0415

        if self._loaded:
            return

        if not self.anchor_path.exists():
            msg = (
                f"Anchor set not found at {self.anchor_path}. "
                "Run `scripts/build_anchor_set.py` to create it."
            )
            raise FileNotFoundError(msg)

        df = pd.read_parquet(self.anchor_path)
        logger.info(
            "anchor_set_loaded",
            path=str(self.anchor_path),
            n_anchors=len(df),
            outcomes=df["outcome"].value_counts().to_dict(),
        )

        # Parse embeddings from stored format (bytes → float32 ndarray)
        embeddings = self._parse_embeddings(df)
        self._embeddings = embeddings                         # (N, D)
        self._labels = df["outcome"].tolist()
        self._confidences = df["confidence"].tolist()
        self._loaded = True

    @staticmethod
    def _parse_embeddings(df: "pd.DataFrame") -> np.ndarray:
        """Convert embedding column to a float32 matrix.

        Supports embeddings stored as:
        - ``bytes`` (raw float32 binary from numpy tobytes())
        - ``list[float]`` (JSON-serializable format)
        """
        import io  # noqa: PLC0415

        rows = []
        for val in df["embedding"]:
            if isinstance(val, bytes):
                rows.append(np.frombuffer(val, dtype=np.float32))
            elif isinstance(val, (list, np.ndarray)):
                rows.append(np.array(val, dtype=np.float32))
            else:
                # Try to deserialize from numpy save format
                buf = io.BytesIO(val)
                rows.append(np.load(buf))

        return np.stack(rows, axis=0)  # (N, D)

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify(
        self,
        query_embedding: np.ndarray,
    ) -> OutcomeDistribution:
        """Classify a single embedding via weighted k-NN vote.

        Args:
            query_embedding: 1-D float32 array of shape (D,).
                Should be L2-normalized (as returned by LocalEmbedder).

        Returns:
            OutcomeDistribution with probabilities summing to 1.0.
            Returns a uniform prior if no anchor clears min_sim.
        """
        if not self._loaded:
            self.load()

        assert self._embeddings is not None
        assert self._labels is not None
        assert self._confidences is not None

        # Cosine similarities via matrix multiply (embeddings already L2-normed)
        q = query_embedding / (np.linalg.norm(query_embedding) + 1e-9)
        sims = self._embeddings @ q  # (N,)

        # Select top-k above threshold
        top_idx = np.argsort(sims)[::-1][: self.k]
        top_sims = sims[top_idx]

        # Filter by minimum similarity
        valid_mask = top_sims >= self.min_sim
        if not valid_mask.any():
            logger.debug(
                "knn_no_valid_neighbors",
                top_sim=float(top_sims[0]) if len(top_sims) > 0 else 0.0,
                threshold=self.min_sim,
            )
            # Return uniform distribution when anchor set can't help
            from causaganha.analysis.bayesian_fusion import uniform_prior  # noqa: PLC0415
            return uniform_prior()

        valid_idx = top_idx[valid_mask]
        valid_sims = top_sims[valid_mask]

        # Weighted vote: weight = similarity × anchor_confidence
        vote_weights: dict[str, float] = {k: 0.0 for k in OUTCOME_KEYS}
        for idx, sim in zip(valid_idx, valid_sims, strict=True):
            label = self._labels[idx]
            anchor_conf = self._confidences[idx]
            if label in vote_weights:
                vote_weights[label] += float(sim) * anchor_conf

        logger.debug(
            "knn_vote_complete",
            n_neighbors=int(valid_mask.sum()),
            top_neighbor_sim=round(float(valid_sims[0]), 3),
            top_vote=max(vote_weights, key=vote_weights.__getitem__),
        )

        return normalize(vote_weights)

    async def aclassify(
        self,
        query_embedding: np.ndarray,
    ) -> OutcomeDistribution:
        """Async wrapper for classify() — runs in thread pool."""
        import asyncio  # noqa: PLC0415

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.classify, query_embedding)

    # ------------------------------------------------------------------
    # Anchor Set Growth
    # ------------------------------------------------------------------

    def maybe_add_anchor(
        self,
        numero_processo: str,
        texto_truncado: str,
        embedding: np.ndarray,
        outcome: str,
        confidence: float,
        annotation_src: str = "llm",
        min_confidence: float = 0.85,
    ) -> bool:
        """Add a new anchor if it meets quality criteria.

        Called after an LLM classifies a decision (either as fallback
        or as part of random sampling). High-confidence LLM outputs
        are added to the anchor set to improve future k-NN accuracy.

        The new anchor is appended to the in-memory arrays immediately
        (for same-session inference) and saved to parquet on flush.

        Args:
            numero_processo: Case number for deduplication.
            texto_truncado: First 1000 chars of decision text.
            embedding: Pre-computed embedding (D,) float32.
            outcome: LLM-assigned outcome label.
            confidence: LLM confidence score.
            annotation_src: Source tag ("llm", "manual", "auto").
            min_confidence: Minimum LLM confidence to accept. Default: 0.85.

        Returns:
            True if the anchor was added, False if rejected.
        """
        if confidence < min_confidence:
            logger.debug(
                "anchor_rejected_low_confidence",
                outcome=outcome,
                confidence=confidence,
                threshold=min_confidence,
            )
            return False

        if outcome not in OUTCOME_KEYS or outcome == "unknown":
            logger.debug(
                "anchor_rejected_unknown_outcome",
                outcome=outcome,
            )
            return False

        # Add to in-memory arrays
        if self._loaded and self._embeddings is not None:
            self._embeddings = np.vstack([
                self._embeddings,
                embedding.reshape(1, -1).astype(np.float32),
            ])
            self._labels = self._labels or []
            self._labels.append(outcome)
            self._confidences = self._confidences or []
            self._confidences.append(confidence)

        # Persist to parquet
        self._append_to_parquet(
            numero_processo=numero_processo,
            texto_truncado=texto_truncado,
            embedding=embedding,
            outcome=outcome,
            confidence=confidence,
            annotation_src=annotation_src,
        )

        logger.info(
            "anchor_added",
            outcome=outcome,
            confidence=confidence,
            src=annotation_src,
            total=len(self._labels) if self._labels else "?",
        )
        return True

    def _append_to_parquet(
        self,
        numero_processo: str,
        texto_truncado: str,
        embedding: np.ndarray,
        outcome: str,
        confidence: float,
        annotation_src: str,
    ) -> None:
        """Append a single row to the anchor parquet file."""
        import pandas as pd  # noqa: PLC0415

        new_row = pd.DataFrame([{
            "numero_processo": numero_processo,
            "texto_truncado": texto_truncado,
            "outcome": outcome,
            "confidence": confidence,
            "annotation_src": annotation_src,
            "embedding": embedding.astype(np.float32).tobytes(),
        }])

        if self.anchor_path.exists():
            existing = pd.read_parquet(self.anchor_path)
            # Deduplicate by numero_processo
            existing = existing[
                existing["numero_processo"] != numero_processo
            ]
            combined = pd.concat([existing, new_row], ignore_index=True)
        else:
            self.anchor_path.parent.mkdir(parents=True, exist_ok=True)
            combined = new_row

        combined.to_parquet(self.anchor_path, index=False)

    @property
    def n_anchors(self) -> int:
        """Return the number of loaded anchors."""
        if self._labels is None:
            return 0
        return len(self._labels)

    @property
    def outcome_counts(self) -> dict[str, int]:
        """Return count of anchors per outcome label."""
        if not self._labels:
            return {}
        from collections import Counter  # noqa: PLC0415
        return dict(Counter(self._labels))
