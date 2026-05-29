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

import numpy as np
import structlog

from causaganha.analysis.bayesian_fusion import (
    OUTCOME_KEYS,
    OutcomeDistribution,
    normalize,
)


logger = structlog.get_logger()

# Default location of the anchor set relative to project root
DEFAULT_ANCHOR_PATH = Path("data/anchor_set.parquet")

# Number of pending anchors to accumulate before flushing to parquet
_FLUSH_THRESHOLD = 10

# Defaults exposed so callers can reference them without instantiating the class
DEFAULT_MAX_ANCHORS_PER_CLASS = 1000
DEFAULT_NEAR_DUPLICATE_SIM = 0.95

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
        max_anchors_per_class: int = DEFAULT_MAX_ANCHORS_PER_CLASS,
        near_duplicate_sim: float = DEFAULT_NEAR_DUPLICATE_SIM,
    ) -> None:
        """Initialize classifier with anchor set path and k-NN parameters."""
        self.anchor_path = Path(anchor_path)
        self.k = k
        self.min_sim = min_sim
        self.max_anchors_per_class = max_anchors_per_class
        self.near_duplicate_sim = near_duplicate_sim

        self._embeddings: np.ndarray | None = None   # (N, D) float32
        self._labels: list[str] | None = None         # len N
        self._confidences: list[float] | None = None  # len N
        self._loaded_processes: set[str] = set()      # for in-memory dedup
        self._pending_anchors: list[dict] = []        # batched before flush
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
        import ibis  # noqa: PLC0415

        if self._loaded:
            return

        if not self.anchor_path.exists():
            msg = (
                f"Anchor set not found at {self.anchor_path}. "
                "Run `scripts/build_anchor_set.py` to create it."
            )
            raise FileNotFoundError(msg)

        # Single materialization: one DuckDB pass over the parquet for all columns
        df = (
            ibis.read_parquet(self.anchor_path)
            .select("outcome", "confidence", "numero_processo", "embedding")
            .execute()
        )

        outcome_counts = df["outcome"].value_counts().to_dict()
        logger.info(
            "anchor_set_loaded",
            path=str(self.anchor_path),
            n_anchors=len(df),
            outcomes=outcome_counts,
        )

        self._embeddings = self._parse_embeddings(df["embedding"])
        self._labels = df["outcome"].tolist()
        self._confidences = df["confidence"].tolist()
        self._loaded_processes = set(df["numero_processo"].tolist())
        self._loaded = True

    @staticmethod
    def _parse_embeddings(col: object) -> np.ndarray:
        """Convert embedding column to a float32 matrix.

        Supports embeddings stored as:
        - ``bytes`` (raw float32 binary from numpy tobytes())
        - ``list[float]`` (JSON-serializable format)
        """
        first = col.iloc[0] if len(col) else None

        # Fast path: all bytes — single frombuffer on concatenated bytes (no Python loop)
        if isinstance(first, bytes):
            dim = len(first) // 4  # float32 = 4 bytes per element
            flat = np.frombuffer(b"".join(col), dtype=np.float32)
            return flat.reshape(-1, dim)

        # Slow path: mixed or list[float] format — iterate per-row
        import io  # noqa: PLC0415
        rows = []
        for val in col:
            if isinstance(val, (list, np.ndarray)):
                rows.append(np.array(val, dtype=np.float32))
            else:
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

        if self._embeddings is None or self._labels is None or self._confidences is None:
            msg = "Anchor set failed to load — embeddings/labels/confidences are None."
            raise RuntimeError(msg)

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

        # Weighted vote: weight = similarity * anchor_confidence
        vote_weights: dict[str, float] = dict.fromkeys(OUTCOME_KEYS, 0.0)
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

        loop = asyncio.get_running_loop()
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

        # Skip if already in-memory (dedup by case number)
        if numero_processo in self._loaded_processes:
            logger.debug("anchor_rejected_duplicate", numero_processo=numero_processo)
            return False

        if self._loaded and self._labels is not None and self._embeddings is not None:
            # Reject if this class is already at the per-class cap
            class_count = self._labels.count(outcome)
            if class_count >= self.max_anchors_per_class:
                logger.debug(
                    "anchor_rejected_class_cap",
                    outcome=outcome,
                    count=class_count,
                    cap=self.max_anchors_per_class,
                )
                return False

            # Reject near-duplicates: if closest same-class anchor exceeds
            # near_duplicate_sim the region is already well-covered
            same_class_idx = [i for i, lb in enumerate(self._labels) if lb == outcome]
            if same_class_idx:
                same_embs = self._embeddings[same_class_idx]
                q = embedding / (np.linalg.norm(embedding) + 1e-9)
                max_sim = float((same_embs @ q).max())
                if max_sim >= self.near_duplicate_sim:
                    logger.debug(
                        "anchor_rejected_near_duplicate",
                        outcome=outcome,
                        max_sim=round(max_sim, 3),
                        threshold=self.near_duplicate_sim,
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
            self._loaded_processes.add(numero_processo)

        # Track regardless of load state — prevents same-session duplicates
        # even when the anchor set hasn't been loaded yet (e.g. bootstrap runs)
        self._loaded_processes.add(numero_processo)

        # Queue for batched parquet write
        self._pending_anchors.append({
            "numero_processo": numero_processo,
            "texto_truncado": texto_truncado,
            "embedding": embedding.astype(np.float32).tobytes(),
            "outcome": outcome,
            "confidence": confidence,
            "annotation_src": annotation_src,
        })

        if len(self._pending_anchors) >= _FLUSH_THRESHOLD:
            self.flush()

        logger.info(
            "anchor_added",
            outcome=outcome,
            confidence=confidence,
            src=annotation_src,
            total=len(self._labels) if self._labels else "?",
        )
        return True

    def flush(self) -> int:
        """Write all pending anchors to the parquet file.

        Called automatically when the pending queue reaches _FLUSH_THRESHOLD.
        Call explicitly before process exit to ensure all anchors are saved.

        Returns:
            Number of anchors written.
        """
        if not self._pending_anchors:
            return 0

        import ibis  # noqa: PLC0415

        pending = self._pending_anchors
        self._pending_anchors = []

        new_table = ibis.memtable(pending)

        if self.anchor_path.exists():
            existing = ibis.read_parquet(self.anchor_path)
            # Build the full expression lazily; new_ids are small (≤ _FLUSH_THRESHOLD)
            new_ids = [row["numero_processo"] for row in pending]
            combined = (
                existing.filter(~existing["numero_processo"].isin(new_ids))
                .union(new_table)
            )
        else:
            self.anchor_path.parent.mkdir(parents=True, exist_ok=True)
            combined = new_table

        # Single materialization: execute once, derive count, write from memory
        combined_df = combined.execute()
        n_total = len(combined_df)
        ibis.memtable(combined_df).to_parquet(str(self.anchor_path))
        logger.info("anchor_set_flushed", n_written=len(pending), total=n_total)
        return len(pending)

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
