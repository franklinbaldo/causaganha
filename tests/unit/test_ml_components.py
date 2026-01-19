import pytest
from pathlib import Path
import tempfile
import sqlite3
import numpy as np
from causaganha.ml.embeddings import EmbeddingCache
from causaganha.ml.online_learner import WinnerPredictor
from causaganha.ml.types import WinnerLabel

class TestEmbeddingCache:
    def test_set_and_get(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "cache.sqlite"
            cache = EmbeddingCache(db_path=str(db_path))

            text = "test text"
            model = "test-model"
            vector = [0.1, 0.2, 0.3]

            # Initial get should return None
            assert cache.get(text, model) is None

            # Set
            cache.set(text, model, vector)

            # Get should return vector
            result = cache.get(text, model)
            assert result == vector

            # Different model/text should return None
            assert cache.get("other text", model) is None
            assert cache.get(text, "other-model") is None

class TestWinnerPredictor:
    def test_cold_start(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = WinnerPredictor(model_dir=tmpdir)
            assert not predictor.is_trained

            result = predictor.predict([0.1, 0.1])
            assert result.prediction is None
            assert result.confidence == 0.0

    def test_train_and_predict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = WinnerPredictor(model_dir=tmpdir)

            # Train with some dummy data (linearly separable)
            # Class 0: Plaintiff (small values), Class 1: Defendant (large values)
            vector1 = [0.1, 0.1]
            vector2 = [0.9, 0.9]

            # SGD needs more examples to learn reliably, or we accept that 2 examples might not be enough for correct classification boundary immediately with default learning rate
            # Let's feed it a few times to ensure it learns
            for _ in range(10):
                predictor.update(vector1, WinnerLabel.PLAINTIFF_WON)
                predictor.update(vector2, WinnerLabel.DEFENDANT_WON)

            assert predictor.is_trained

            # Predict
            res1 = predictor.predict(vector1)
            assert res1.prediction == WinnerLabel.PLAINTIFF_WON

            res2 = predictor.predict(vector2)
            assert res2.prediction == WinnerLabel.DEFENDANT_WON

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Train a model
            predictor1 = WinnerPredictor(model_dir=tmpdir)
            predictor1.update([0.5, 0.5], WinnerLabel.PLAINTIFF_WON)
            version1 = predictor1.model_version

            # Load new instance from same dir
            predictor2 = WinnerPredictor(model_dir=tmpdir)
            assert predictor2.is_trained
            assert predictor2.training_counter == 1
            assert predictor2.model_version == version1

            # Verify prediction capability persists
            # (Note: with 1 sample SGD might not predict class 0 surely but classes are set)
            res = predictor2.predict([0.5, 0.5])
            # Just check it runs and returns a label from the classes
            assert res.prediction in [WinnerLabel.PLAINTIFF_WON, WinnerLabel.DEFENDANT_WON]
