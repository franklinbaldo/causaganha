import asyncio
from typing import Any

import structlog

from causaganha.infrastructure.storage.repositories.analysis import AnalysisRepository
from causaganha.ml.bootstrap import DBBootstrapper
from causaganha.ml.embeddings import EmbeddingCache, GeminiEmbedder
from causaganha.ml.online_learner import WinnerPredictor
from causaganha.ml.teacher import LLMTeacher
from causaganha.ml.types import (
    WinnerBootstrapMode,
    WinnerClassifierMode,
    WinnerLabel,
)


logger = structlog.get_logger()


class WinnerClassifierRunner:
    def __init__(
        self,
        mode: WinnerClassifierMode,
        bootstrap_mode: WinnerBootstrapMode,
        bootstrap_limit: int,
        jobs: int,
        analysis_repo: AnalysisRepository,
    ):
        self.mode = mode
        self.bootstrap_mode = bootstrap_mode
        self.bootstrap_limit = bootstrap_limit
        self.jobs = jobs
        self.analysis_repo = analysis_repo

        self.embedder = None
        self.predictor = None
        self.teacher = None

        if mode != WinnerClassifierMode.OFF:
            self._init_components()

    def _init_components(self):
        cache = EmbeddingCache()
        self.embedder = GeminiEmbedder(cache=cache)
        self.predictor = WinnerPredictor()

        if self.mode == WinnerClassifierMode.TEACH:
            self.teacher = LLMTeacher()

        # Handle bootstrap
        asyncio.create_task(self._handle_bootstrap())

    async def _handle_bootstrap(self):
        should_bootstrap = False
        if self.bootstrap_mode == WinnerBootstrapMode.FORCE:
            should_bootstrap = True
        elif self.bootstrap_mode == WinnerBootstrapMode.AUTO:
            if self.mode == WinnerClassifierMode.TEACH and not self.predictor.is_trained:
                should_bootstrap = True

        if should_bootstrap:
            bootstrapper = DBBootstrapper(self.analysis_repo, self.embedder, self.predictor)
            await bootstrapper.bootstrap(limit=self.bootstrap_limit)

    async def process_decision(self, text: str) -> dict[str, Any]:
        """Process a single decision text."""
        if self.mode == WinnerClassifierMode.OFF or not text:
            return {}

        result = {}

        # 1. Embed (Parallelizable)
        vector = await self.embedder.embed(text)
        if not vector:
            return {}

        # 2. Predict (Fast, thread-safeish if read-only, but verify)
        # Predictor reads state.
        pred_result = self.predictor.predict(vector)

        if pred_result.prediction:
            result["winner_ml_pred"] = pred_result.prediction.value
            result["winner_ml_confidence"] = pred_result.confidence
            result["winner_model_version"] = pred_result.model_version

        # 3. Teach (Parallelizable) & Train (Serialized)
        if self.mode == WinnerClassifierMode.TEACH and self.teacher:
            # Call teacher
            label = await self.teacher.label(text)
            result["winner_teacher_label"] = label.value

            if label != WinnerLabel.UNCLEAR and vector:
                # Train (Serialized)
                # We are calling this from concurrent tasks.
                # Ideally, partial_fit is not thread safe if called concurrently?
                # SGDClassifier.partial_fit is generally not thread safe for concurrent updates on same instance.
                # We need a lock.
                # But since we are running in asyncio, we are in a single thread usually?
                # Yes, standard asyncio is single threaded.
                # So unless `update` does `await` (yields control), it is atomic with respect to other tasks.
                # My `WinnerPredictor.update` is synchronous (calls sklearn and joblib dump).
                # However, joblib dump is IO.
                # But it's synchronous IO. So it blocks the event loop.
                # This ensures serialization naturally in asyncio single-threaded runner!
                # BUT, it blocks the loop, which is bad for throughput.
                # Ideally we should offload save to thread, but then we need a lock.
                # For now, let's keep it simple: sync update blocks loop -> implies serialization.

                self.predictor.update(vector, label)

                # Update result with new version
                result["winner_model_version"] = self.predictor.model_version

        return result
