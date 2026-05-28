"""Ensemble of scikit-learn classifiers to predict document type and procedural class.

Similar to ml_ensemble.py, this uses a combination of scikit-learn models
(Logistic Regression, Random Forest, Gradient Boosting, SVM, MLP) trained on top of
decision embeddings to classify:
1. Document Type (sentença, acórdão, despacho, decisão interlocutória, decisão monocrática)
2. Procedural Stage/Class (cumprimento de sentença, apelação, agravo de instrumento, etc.)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import structlog


logger = structlog.get_logger()

# Default persistence paths
DEFAULT_DOC_TYPE_PATH = Path("data/ml_document_type.joblib")
DEFAULT_PROC_CLASS_PATH = Path("data/ml_procedural_class.joblib")

# Minimum samples per class needed to train
MIN_SAMPLES_PER_CLASS = 5

def _build_classifiers() -> list[tuple[str, object]]:
    """Build the standard list of classifiers."""
    from sklearn.calibration import CalibratedClassifierCV  # noqa: PLC0415
    from sklearn.ensemble import (  # noqa: PLC0415
        HistGradientBoostingClassifier,
        RandomForestClassifier,
    )
    from sklearn.linear_model import LogisticRegression  # noqa: PLC0415
    from sklearn.neural_network import MLPClassifier  # noqa: PLC0415
    from sklearn.svm import LinearSVC  # noqa: PLC0415

    return [
        (
            "logistic_regression",
            LogisticRegression(
                C=1.0,
                max_iter=1000,
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
            HistGradientBoostingClassifier(
                max_iter=100,
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
                method="sigmoid",
                cv=3,
            ),
        ),
        (
            "mlp",
            MLPClassifier(
                hidden_layer_sizes=(64, 32),
                max_iter=500,
                early_stopping=True,
                random_state=42,
            ),
        ),
    ]

class MLDocumentEnsemble:
    """Ensemble of scikit-learn classifiers for document type or procedural class classification."""

    def __init__(self, target_col: str, ensemble_path: Path | str) -> None:
        """Initialize ensemble.

        Args:
            target_col: Name of target column (e.g., 'document_type', 'procedural_class')
            ensemble_path: Joblib save/load path
        """
        self.target_col = target_col
        self.ensemble_path = Path(ensemble_path)
        self._classifiers: list[tuple[str, object]] = []
        self._classes: list[str] = []
        self._is_trained = False

    def train(self, df: object, embeddings: np.ndarray) -> dict:
        """Train all classifiers on the provided dataframe and embeddings matrix.

        Args:
            df: Pandas DataFrame containing the target column
            embeddings: NumPy array of shape (N, D) containing embeddings

        Returns:
            Dict with per-classifier cross-validation F1 macro scores.
        """
        from collections import Counter  # noqa: PLC0415

        from sklearn.model_selection import cross_val_score  # noqa: PLC0415
        from sklearn.preprocessing import LabelEncoder  # noqa: PLC0415

        y_raw = df[self.target_col].tolist()
        x_mat = embeddings.copy()

        # Filter out classes with too few samples to allow cross validation
        counts = Counter(y_raw)
        valid_classes = {cls for cls, cnt in counts.items() if cnt >= MIN_SAMPLES_PER_CLASS}
        valid_mask = [label in valid_classes for label in y_raw]

        x_mat = x_mat[valid_mask]
        y_raw = [y for y, m in zip(y_raw, valid_mask, strict=True) if m]
        # Recompute counts on filtered set so n_cv reflects actual class sizes
        counts = Counter(y_raw)

        logger.info(
            "training_document_ensemble_start",
            target=self.target_col,
            n_samples=len(x_mat),
            classes=dict(Counter(y_raw)),
            embedding_dim=x_mat.shape[1],
        )

        if len(x_mat) < MIN_SAMPLES_PER_CLASS * len(valid_classes):
            msg = f"Insufficient training data for {self.target_col} ensemble."
            raise ValueError(msg)

        # Encode labels
        le = LabelEncoder()
        y = le.fit_transform(y_raw)
        self._classes = [str(c) for c in le.classes_]
        self._label_encoder = le

        # Train each classifier + cross-validate
        classifiers = _build_classifiers()
        trained = []
        cv_results = {}

        for name, clf in classifiers:
            try:
                logger.info("training_document_classifier", target=self.target_col, name=name)
                clf.fit(x_mat, y)
                n_cv = min(5, *[counts[c] for c in valid_classes])
                n_cv = max(2, n_cv) # ensure at least 2 folds

                scores = cross_val_score(
                    clf, x_mat, y, cv=n_cv, scoring="f1_macro"
                )
                cv_results[name] = {
                    "cv_f1_macro_mean": round(float(scores.mean()), 3),
                    "cv_f1_macro_std": round(float(scores.std()), 3),
                }
                logger.info(
                    "document_classifier_trained",
                    target=self.target_col,
                    name=name,
                    cv_f1_mean=cv_results[name]["cv_f1_macro_mean"],
                )
                trained.append((name, clf))
            except (ValueError, RuntimeError) as exc:
                logger.warning(
                    "document_classifier_training_failed",
                    target=self.target_col,
                    name=name,
                    error=str(exc)
                )

        self._classifiers = trained
        self._is_trained = True

        logger.info(
            "document_ensemble_training_complete",
            target=self.target_col,
            n_classifiers=len(trained),
            cv_results=cv_results,
        )

        return cv_results

    def predict_proba(self, embedding: np.ndarray) -> dict[str, float]:
        """Predict probabilities of classes for a single embedding.

        Args:
            embedding: 1-D float32 array of shape (D,).

        Returns:
            Dict mapping class name to predicted probability.
        """
        if not self._is_trained or not self._classifiers:
            msg = f"Ensemble for {self.target_col} is not trained."
            raise RuntimeError(msg)

        x = embedding.reshape(1, -1)
        all_probas = []

        for name, clf in self._classifiers:
            try:
                proba = clf.predict_proba(x)[0]  # shape: (n_classes,)
                all_probas.append(proba)
            except (ValueError, AttributeError) as exc:
                logger.warning(
                    "document_classifier_predict_failed",
                    target=self.target_col,
                    name=name,
                    error=str(exc)
                )

        if not all_probas:
            # Fallback to uniform prior
            p = 1.0 / len(self._classes)
            return dict.fromkeys(self._classes, p)

        # Average probabilities
        avg_proba = np.mean(all_probas, axis=0)

        # Build distribution dict
        dist = {}
        for i, cls_label in enumerate(self._classes):
            dist[cls_label] = float(avg_proba[i])

        # Normalize
        total = sum(dist.values())
        if total > 0:
            dist = {k: v / total for k, v in dist.items()}

        return dist

    def predict(self, embedding: np.ndarray) -> str:
        """Predict the top label for a single embedding.

        Args:
            embedding: 1-D float32 array of shape (D,).

        Returns:
            Top predicted class label (string).
        """
        probas = self.predict_proba(embedding)
        return max(probas, key=probas.get) # type: ignore[arg-type]

    def save(self) -> None:
        """Save the trained ensemble to joblib."""
        import joblib  # noqa: PLC0415

        self.ensemble_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "target_col": self.target_col,
            "classifiers": self._classifiers,
            "classes": self._classes,
            "is_trained": self._is_trained,
            "label_encoder": getattr(self, "_label_encoder", None),
        }
        joblib.dump(payload, self.ensemble_path)
        logger.info("document_ensemble_saved", target=self.target_col, path=str(self.ensemble_path))

    @classmethod
    def load(cls, path: Path | str) -> MLDocumentEnsemble:
        """Load a trained ensemble from joblib."""
        import joblib  # noqa: PLC0415

        load_path = Path(path)
        if not load_path.exists():
            msg = f"Ensemble file not found at {load_path}"
            raise FileNotFoundError(msg)

        payload = joblib.load(load_path)
        instance = cls(target_col=payload["target_col"], ensemble_path=load_path)
        instance._classifiers = payload["classifiers"]
        instance._classes = payload["classes"]
        instance._is_trained = payload["is_trained"]
        if payload.get("label_encoder") is not None:
            instance._label_encoder = payload["label_encoder"]

        logger.info(
            "document_ensemble_loaded",
            target=instance.target_col,
            path=str(load_path),
            n_classifiers=len(instance._classifiers),
            classes=instance._classes,
        )
        return instance
