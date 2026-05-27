"""Judicial named entity recognition using LeNER-Br (BERT encoder).

Wraps `pierreguillou/ner-bert-base-cased-pt-lenerbr` via HuggingFace
`transformers.pipeline`. The model is loaded lazily on first call to avoid
paying the ~440MB model load cost when the NER pipeline isn't used.

LeNER-Br labels (BIO scheme):
    PESSOA        — Person names (judges, lawyers, parties)
    ORGANIZACAO   — Organizations (tribunals, companies, public bodies)
    LOCAL         — Locations
    TEMPO         — Temporal expressions
    LEGISLACAO    — Legislation references
    JURISPRUDENCIA — Case law references (súmulas, precedents)

Performance (CPU, 512 tokens):
    ~22ms inference, F1=0.89 on PT-BR legal text out-of-the-box.

Usage:
    ner = JudicialNER()
    entities = ner.extract("O juiz João Silva condenou o réu.")
    # {"PESSOA": ["João Silva"], "ORGANIZACAO": [], ...}
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from functools import cached_property
from typing import TYPE_CHECKING, Self

import structlog


if TYPE_CHECKING:
    from transformers import Pipeline


logger = structlog.get_logger()

NER_MODEL = "pierreguillou/ner-bert-base-cased-pt-lenerbr"

# Entity types produced by LeNER-Br
LENER_LABELS: list[str] = [
    "PESSOA",
    "ORGANIZACAO",
    "LOCAL",
    "TEMPO",
    "LEGISLACAO",
    "JURISPRUDENCIA",
]


class JudicialNER:
    """Wrapper around LeNER-Br for judicial named entity recognition.

    Runs on the dispositivo slice (not the full text) to keep inference
    fast and focused on the operative section.

    Args:
        model: HuggingFace model ID. Defaults to LeNER-Br.
        device: -1 for CPU, 0+ for GPU index.
        thread_workers: Thread pool size for async calls.
    """

    def __init__(
        self,
        model: str = NER_MODEL,
        device: int = -1,
        thread_workers: int = 2,
    ) -> None:
        """Initialize with model identifier and device selection."""
        self.model_name = model
        self.device = device
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=thread_workers,
            thread_name_prefix="ner",
        )
        logger.info("judicial_ner_init", model=model, device=device)

    @cached_property
    def _pipeline(self) -> Pipeline:
        """Lazily load the HuggingFace NER pipeline on first use."""
        try:
            from transformers import pipeline as hf_pipeline  # noqa: PLC0415
        except ImportError as exc:
            msg = (
                "transformers is required for JudicialNER. "
                "Install with: uv sync --group ner"
            )
            raise ImportError(msg) from exc

        logger.info("loading_ner_model", model=self.model_name)
        pipe = hf_pipeline(
            "ner",
            model=self.model_name,
            aggregation_strategy="simple",
            device=self.device,
        )
        logger.info("ner_model_loaded", model=self.model_name)
        return pipe

    def extract(self, text: str) -> dict[str, list[str]]:
        """Extract named entities grouped by label.

        Args:
            text: Input text (ideally the dispositivo slice, ≤512 tokens).

        Returns:
            Dict mapping label → deduplicated list of entity strings.
            Keys are always present (empty list if no entities found).
        """
        if not text:
            return {label: [] for label in LENER_LABELS}

        raw = self._pipeline(text)

        result: dict[str, list[str]] = {label: [] for label in LENER_LABELS}
        seen: dict[str, set[str]] = {label: set() for label in LENER_LABELS}

        for ent in raw:
            label = ent.get("entity_group", "")
            word = ent.get("word", "").strip()
            if label in result and word and word not in seen[label]:
                seen[label].add(word)
                result[label].append(word)

        logger.debug(
            "ner_extraction_complete",
            n_entities=sum(len(v) for v in result.values()),
            labels={k: len(v) for k, v in result.items() if v},
        )
        return result

    async def aextract(self, text: str) -> dict[str, list[str]]:
        """Async wrapper — runs BERT inference in thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.extract(text),
        )

    def __enter__(self) -> Self:
        """Support use as a context manager."""
        return self

    def __exit__(self, *_: object) -> None:
        """Shutdown thread pool on context manager exit."""
        self._executor.shutdown(wait=True)

    def __del__(self) -> None:
        """Best-effort cleanup if context manager wasn't used."""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)
