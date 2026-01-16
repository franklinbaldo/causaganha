import joblib
import numpy as np
from pathlib import Path
from sklearn.linear_model import SGDClassifier
from typing import Optional
import structlog
from datetime import datetime, UTC
import hashlib
import tempfile
import shutil

from causaganha.ml.types import WinnerLabel, PredictionResult

logger = structlog.get_logger()

class WinnerPredictor:
    def __init__(self, model_dir: str = ".causaganha/models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model_path = self.model_dir / "winner_predictor.joblib"
        self.metadata_path = self.model_dir / "winner_predictor_metadata.joblib"

        self.clf = SGDClassifier(loss="log_loss") # logistic regression
        self.classes = [WinnerLabel.PLAINTIFF_WON.value, WinnerLabel.DEFENDANT_WON.value]
        self.is_trained = False
        self.training_counter = 0
        self.model_version = None

        self._load()

    def _load(self):
        if self.model_path.exists() and self.metadata_path.exists():
            try:
                self.clf = joblib.load(self.model_path)
                metadata = joblib.load(self.metadata_path)
                self.training_counter = metadata.get("training_counter", 0)
                self.model_version = metadata.get("model_version")
                self.is_trained = True
                logger.info("model_loaded", version=self.model_version, count=self.training_counter)
            except Exception as e:
                logger.warning("model_load_failed", error=str(e))
                # Reset if load fails
                self.is_trained = False
                self.training_counter = 0
                self.model_version = None
        else:
            logger.info("model_not_found_starting_fresh")

    def _save(self):
        try:
            # Update version
            timestamp = datetime.now(UTC).isoformat()
            version_str = f"{self.training_counter}-{timestamp}"
            self.model_version = hashlib.md5(version_str.encode()).hexdigest()

            metadata = {
                "training_counter": self.training_counter,
                "model_version": self.model_version,
                "classes": self.classes,
                "updated_at": timestamp
            }

            # Atomic write
            # Create a temporary file in the same directory to ensure atomic move
            with tempfile.NamedTemporaryFile(dir=self.model_dir, delete=False) as tf:
                joblib.dump(self.clf, tf.name)
                temp_model_path = Path(tf.name)

            with tempfile.NamedTemporaryFile(dir=self.model_dir, delete=False) as tf:
                joblib.dump(metadata, tf.name)
                temp_meta_path = Path(tf.name)

            shutil.move(temp_model_path, self.model_path)
            shutil.move(temp_meta_path, self.metadata_path)

        except Exception as e:
            logger.error("model_save_failed", error=str(e))

    def predict(self, vector: list[float]) -> PredictionResult:
        if not self.is_trained:
            return PredictionResult(prediction=None, confidence=0.0, model_version=None)

        try:
            X = np.array([vector])
            # predict_proba returns array of shape (n_samples, n_classes)
            probs = self.clf.predict_proba(X)[0]

            # We need to map probs to classes correctly
            # clf.classes_ might not be in the same order as self.classes
            # but usually partial_fit(classes=...) fixes it.

            max_prob_idx = np.argmax(probs)
            max_prob = probs[max_prob_idx]
            prediction_val = self.clf.classes_[max_prob_idx]

            # Map back to Enum
            label = WinnerLabel(prediction_val)

            return PredictionResult(
                prediction=label,
                confidence=float(max_prob),
                model_version=self.model_version
            )
        except Exception as e:
            logger.error("prediction_failed", error=str(e))
            return PredictionResult(prediction=None, confidence=0.0, model_version=self.model_version)

    def update(self, vector: list[float], label: WinnerLabel):
        if label == WinnerLabel.UNCLEAR:
            return

        X = np.array([vector])
        y = np.array([label.value])

        self.clf.partial_fit(X, y, classes=self.classes)
        self.training_counter += 1
        self.is_trained = True
        self._save()
