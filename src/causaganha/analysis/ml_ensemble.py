"""Ensemble of scikit-learn classifiers trained on top of embeddings.

Each classifier takes a 256-dim EmbeddingGemma vector as input and
outputs a probability distribution over judicial outcomes. Multiple
classifiers are trained and their probabilities are averaged (soft voting)
before being fed into the Bayesian fusion layer.

Classifiers included:
    - LogisticRegression (fast, interpretable baseline)
    - RandomForestClassifier (non-linear, handles noisy labels)
    - GradientBoostingClassifier (strong, sklearn GBDT)
    - LinearSVC via CalibratedClassifierCV (SVM with probability calibration)
    - MLPClassifier (small neural head on top of embeddings)

All models are persisted as a single joblib file for fast reload.

Workflow:
    1. Build anchor set (scripts/build_anchor_set.py)
    2. Train: EmbeddingEnsemble.train(anchor_path)
    3. Save: ensemble.save("data/ml_ensemble.joblib")
    4. Inference: ensemble.predict_proba(embedding) → OutcomeDistribution
    5. Feed into bayesian_fusion.fuse()

GitHub Actions: train weekly or on anchor set updates (via workflow_dispatch).
"""

from __future__ import annotations

import io
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
    pass

logger = structlog.get_logger()

# Default paths
DEFAULT_ENSEMBLE_PATH = Path("data/ml_ensemble.joblib")
DEFAULT_ANCHOR_PATH = Path("data/anchor_set.parquet")

# Minimum samples per class needed to train (avoid degenerate models)
MIN_SAMPLES_PER_CLASS = 5


def _build_classifiers() -> list[tuple[str, object]]:
    """Build list of (name, classifier) pairs.

    All classifiers output ``predict_proba`` with shape (N, n_classes).
    Uses CalibratedClassifierCV to add probability calibration where needed.
    """
    from sklearn.calibration import CalibratedClassifierCV  # noqa: PLC0415
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier  # noqa: PLC0415
    from sklearn.linear_model import LogisticRegression  # noqa: PLC0415
    from sklearn.neural_network import MLPClassifier  # noqa: PLC0415
    from sklearn.svm import LinearSVC  # noqa: PLC0415

    return [
        (
            "logistic_regression",
            LogisticRegression(
                C=1.0,
                max_iter=1000,
                multi_class="multinomial",
                solver="lbfgs",
                class_weight="balanced",
                random_state=42,
            ),
        ),
        (
            "random_forest",
            RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            ),
        ),
        (
            "gradient_boosting",
            GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=4,
                random_state=42,
            ),
        ),
        (
            "svm_calibrated",
            CalibratedClassifierCV(
                LinearSVC(
                    C=1.0,
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=42,
                ),
                method="isotonic",
                cv=3,
            ),
        ),
        (
            "mlp",
            MLPClassifier(
                hidden_layer_sizes=(128, 64),
                activation="relu",
                max_iter=300,
                early_stopping=True,
                random_state=42,
            ),
        ),
    ]


class EmbeddingEnsemble:
    """Ensemble of sklearn classifiers trained on embedding vectors.

    After training, each classifier predicts a probability distribution
    over the outcome classes. The ensemble combines them via soft voting
    (average of probabilities), then normalizes to sum to 1.0.

    Args:
        ensemble_path: Where to save/load the trained ensemble.
        anchor_path: Parquet file with training data (from anchor set).

    Example:
        # Train once:
        ensemble = EmbeddingEnsemble()
        metrics = ensemble.train(anchor_path="data/anchor_set.parquet")
        ensemble.save()

        # Inference:
        ensemble = EmbeddingEnsemble.load()
        dist = ensemble.predict_proba(embedding)
        # dist == {"procedente": 0.72, "improcedente": 0.20, ...}
    """

    def __init__(
        self,
        ensemble_path: Path | str = DEFAULT_ENSEMBLE_PATH,
        anchor_path: Path | str = DEFAULT_ANCHOR_PATH,
    ) -> None:
        self.ensemble_path = Path(ensemble_path)
        self.anchor_path = Path(anchor_path)
        self._classifiers: list[tuple[str, object]] = []
        self._classes: list[str] = []  # outcome labels matching clf.classes_
        self._is_trained = False

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, anchor_path: Path | str | None = None) -> dict:
        """Train all classifiers on the anchor set.

        Args:
            anchor_path: Override the default anchor parquet path.

        Returns:
            Dict with per-classifier cross-validation accuracy scores.

        Raises:
            FileNotFoundError: If anchor parquet does not exist.
            ValueError: If training data is insufficient.
        """
        import pandas as pd  # noqa: PLC0415
        from sklearn.model_selection import cross_val_score  # noqa: PLC0415
        from sklearn.preprocessing import LabelEncoder  # noqa: PLC0415

        path = Path(anchor_path or self.anchor_path)
        if not path.exists():
            msg = f"Anchor set not found at {path}. Run scripts/build_anchor_set.py first."
            raise FileNotFoundError(msg)

        df = pd.read_parquet(path)
        logger.info("training_ensemble", n_samples=len(df), path=str(path))

        # Parse embeddings
        X = self._parse_embeddings(df)  # (N, D)
        y_raw = df["outcome"].tolist()

        # Filter out "unknown" labels (not useful for training)
        valid_mask = [label in OUTCOME_KEYS and label != "unknown" for label in y_raw]
        X = X[valid_mask]
        y_raw = [y for y, m in zip(y_raw, valid_mask, strict=True) if m]

        if len(X) < MIN_SAMPLES_PER_CLASS * 3:
            msg = (
                f"Insufficient training data: {len(X)} samples after filtering. "
                f"Need at least {MIN_SAMPLES_PER_CLASS * 3}. "
                "Run scripts/build_anchor_set.py to generate more labeled data."
            )
            raise ValueError(msg)

        # Filter classes with too few samples
        from collections import Counter  # noqa: PLC0415
        counts = Counter(y_raw)
        valid_classes = {cls for cls, cnt in counts.items() if cnt >= MIN_SAMPLES_PER_CLASS}
        final_mask = [label in valid_classes for label in y_raw]
        X = X[final_mask]
        y_raw = [y for y, m in zip(y_raw, final_mask, strict=True) if m]

        logger.info(
            "training_data_prepared",
            n_samples=len(X),
            classes=dict(Counter(y_raw)),
            embedding_dim=X.shape[1],
        )

        # Encode labels
        le = LabelEncoder()
        y = le.fit_transform(y_raw)
        self._classes = list(le.classes_)
        self._label_encoder = le

        # Train each classifier + cross-validate
        classifiers = _build_classifiers()
        trained = []
        cv_results = {}

        for name, clf in classifiers:
            try:
                logger.info("training_classifier", name=name)
                clf.fit(X, y)
                scores = cross_val_score(clf, X, y, cv=min(5, min(counts.values())), scoring="f1_macro")
                cv_results[name] = {
                    "cv_f1_macro_mean": round(float(scores.mean()), 3),
                    "cv_f1_macro_std": round(float(scores.std()), 3),
                }
                logger.info(
                    "classifier_trained",
                    name=name,
                    cv_f1_mean=cv_results[name]["cv_f1_macro_mean"],
                    cv_f1_std=cv_results[name]["cv_f1_macro_std"],
                )
                trained.append((name, clf))
            except Exception:
                logger.exception("classifier_training_failed", name=name)

        self._classifiers = trained
        self._is_trained = True

        logger.info(
            "ensemble_training_complete",
            n_classifiers=len(trained),
            cv_results=cv_results,
        )

        return cv_results

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict_proba(
        self,
        embedding: np.ndarray,
    ) -> OutcomeDistribution:
        """Predict outcome probabilities for a single embedding.

        Runs all trained classifiers and returns the soft-voted average
        of their probability distributions.

        Args:
            embedding: 1-D float32 array of shape (D,).

        Returns:
            OutcomeDistribution over OUTCOME_KEYS.

        Raises:
            RuntimeError: If the ensemble has not been trained or loaded.
        """
        if not self._is_trained or not self._classifiers:
            msg = "Ensemble is not trained. Call train() or load() first."
            raise RuntimeError(msg)

        x = embedding.reshape(1, -1)

        # Accumulate probability arrays from each classifier
        all_probas: list[np.ndarray] = []
        for name, clf in self._classifiers:
            try:
                proba = clf.predict_proba(x)[0]  # shape: (n_classes,)
                all_probas.append(proba)
            except Exception:
                logger.warning("classifier_predict_failed", name=name)

        if not all_probas:
            from causaganha.analysis.bayesian_fusion import uniform_prior  # noqa: PLC0415
            return uniform_prior()

        # Soft vote: average probabilities across classifiers
        avg_proba = np.mean(all_probas, axis=0)  # (n_classes,)

        # Map classifier classes back to OUTCOME_KEYS
        dist: dict[str, float] = {k: 0.0 for k in OUTCOME_KEYS}
        for i, cls_label in enumerate(self._classes):
            if cls_label in dist:
                dist[cls_label] = float(avg_proba[i])

        # Normalize to handle any floating point drift
        result = normalize(dist)

        logger.debug(
            "ensemble_prediction",
            top_outcome=max(result, key=result.__getitem__),
            top_prob=round(max(result.values()), 3),
            n_classifiers=len(all_probas),
        )

        return result

    def predict_proba_with_agreement(
        self,
        embedding: np.ndarray,
    ) -> tuple[OutcomeDistribution, float]:
        """Predict and return inter-classifier agreement as confidence bonus.

        Agreement is the fraction of classifiers that agree on the top outcome.
        High agreement (> 0.8) increases confidence in the prediction.

        Args:
            embedding: 1-D float32 array of shape (D,).

        Returns:
            Tuple of (OutcomeDistribution, agreement_score).
            agreement_score is in [0.0, 1.0].
        """
        if not self._is_trained or not self._classifiers:
            from causaganha.analysis.bayesian_fusion import uniform_prior  # noqa: PLC0415
            return uniform_prior(), 0.0

        x = embedding.reshape(1, -1)
        individual_tops = []
        all_probas = []

        for name, clf in self._classifiers:
            try:
                proba = clf.predict_proba(x)[0]
                all_probas.append(proba)
                top_class_idx = int(np.argmax(proba))
                individual_tops.append(self._classes[top_class_idx])
            except Exception:
                logger.warning("classifier_predict_failed", name=name)

        if not all_probas:
            from causaganha.analysis.bayesian_fusion import uniform_prior  # noqa: PLC0415
            return uniform_prior(), 0.0

        # Agreement: fraction of classifiers picking the same top outcome
        from collections import Counter  # noqa: PLC0415
        top_counter = Counter(individual_tops)
        majority_outcome, majority_count = top_counter.most_common(1)[0]
        agreement = majority_count / len(individual_tops)

        # Build averaged distribution
        avg_proba = np.mean(all_probas, axis=0)
        dist: dict[str, float] = {k: 0.0 for k in OUTCOME_KEYS}
        for i, cls_label in enumerate(self._classes):
            if cls_label in dist:
                dist[cls_label] = float(avg_proba[i])
        result = normalize(dist)

        logger.debug(
            "ensemble_agreement",
            majority_outcome=majority_outcome,
            agreement=round(agreement, 3),
            n_classifiers=len(all_probas),
        )

        return result, agreement

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path | str | None = None) -> None:
        """Serialize the trained ensemble to a joblib file.

        Args:
            path: Override save path. Defaults to self.ensemble_path.
        """
        import joblib  # noqa: PLC0415

        save_path = Path(path or self.ensemble_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "classifiers": self._classifiers,
            "classes": self._classes,
            "is_trained": self._is_trained,
        }
        joblib.dump(payload, save_path)
        logger.info("ensemble_saved", path=str(save_path), n_classifiers=len(self._classifiers))

    @classmethod
    def load(cls, path: Path | str = DEFAULT_ENSEMBLE_PATH) -> "EmbeddingEnsemble":
        """Load a previously trained ensemble from disk.

        Args:
            path: Path to the joblib file saved by save().

        Returns:
            Initialized and ready EmbeddingEnsemble.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        import joblib  # noqa: PLC0415

        load_path = Path(path)
        if not load_path.exists():
            msg = (
                f"Ensemble not found at {load_path}. "
                "Train with EmbeddingEnsemble().train() and save()."
            )
            raise FileNotFoundError(msg)

        payload = joblib.load(load_path)
        instance = cls(ensemble_path=load_path)
        instance._classifiers = payload["classifiers"]
        instance._classes = payload["classes"]
        instance._is_trained = payload["is_trained"]

        logger.info(
            "ensemble_loaded",
            path=str(load_path),
            n_classifiers=len(instance._classifiers),
            classes=instance._classes,
        )
        return instance

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_embeddings(df: "object") -> np.ndarray:
        """Parse embedding column from parquet DataFrame to float32 matrix."""
        import pandas as pd  # noqa: PLC0415

        rows = []
        for val in df["embedding"]:  # type: ignore[union-attr]
            if isinstance(val, bytes):
                rows.append(np.frombuffer(val, dtype=np.float32))
            else:
                rows.append(np.array(val, dtype=np.float32))
        return np.stack(rows, axis=0)

    @property
    def is_trained(self) -> bool:
        """Return True if the ensemble has been trained or loaded."""
        return self._is_trained

    @property
    def classifier_names(self) -> list[str]:
        """Return the names of the trained classifiers."""
        return [name for name, _ in self._classifiers]
