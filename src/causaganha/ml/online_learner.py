"""Module for the online learning model (WinnerPredictor)."""

import os
import joblib
import structlog
from typing import List, Tuple
import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler

logger = structlog.get_logger()

class WinnerPredictor:
    """
    An online learning model to predict the winning side of a judicial decision.
    Uses SGDClassifier for incremental learning and StandardScaler for feature scaling.
    """

    def __init__(self, model_path: str = "winner_predictor.joblib",
                 scaler_path: str = "winner_predictor_scaler.joblib",
                 random_state: int = 42):
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.random_state = random_state
        self.model = self._load_or_create_model()
        self.scaler = self._load_or_create_scaler()
        self._is_fitted = False
        if hasattr(self.model, 'coef_') and self.model.coef_ is not None:
            self._is_fitted = True

    def _load_or_create_model(self):
        if os.path.exists(self.model_path):
            logger.info("loading_winner_predictor_model", path=self.model_path)
            return joblib.load(self.model_path)
        logger.info("creating_new_winner_predictor_model")
        # Initialize with a basic SGDClassifier (e.g., logistic regression)
        # Assuming binary classification (0 or 1)
        return SGDClassifier(loss='log_loss', random_state=self.random_state, warm_start=True)

    def _load_or_create_scaler(self):
        if os.path.exists(self.scaler_path):
            logger.info("loading_winner_predictor_scaler", path=self.scaler_path)
            return joblib.load(self.scaler_path)
        logger.info("creating_new_winner_predictor_scaler")
        return StandardScaler()

    def _ensure_model_fitted(self, X: np.ndarray):
        """Ensures the model is partially fitted if it hasn't seen any data yet."""
        if not self._is_fitted:
            # For SGDClassifier, fit needs at least one sample and all classes
            # This is a dummy fit to initialize the model's internal state
            # Assuming labels are 0 and 1
            dummy_X = np.zeros((2, X.shape[1]))
            dummy_y = np.array([0, 1])
            self.model.partial_fit(dummy_X, dummy_y, classes=np.array([0, 1]))
            self._is_fitted = True
            logger.info("winner_predictor_model_initialized_with_dummy_fit")

    def predict(self, embedding_vector: List[float]) -> Tuple[int, float]:
        """
        Predicts the winning side (0 or 1) and returns a confidence score.

        Args:
            embedding_vector: The embedding of the judicial decision text.

        Returns:
            A tuple: (predicted_class: int, confidence_score: float)
        """
        X = np.array(embedding_vector).reshape(1, -1)

        # Scale features if scaler is fitted, else just use raw
        if hasattr(self.scaler, 'mean_'):
            X_scaled = self.scaler.transform(X)
        else:
            logger.warning("scaler_not_fitted_using_raw_features_for_prediction")
            X_scaled = X

        if not self._is_fitted:
            logger.warning("winner_predictor_not_fitted_returning_default_prediction")
            return 0, 0.5  # Default prediction and confidence if model is not fitted

        # Get probabilities for each class
        probas = self.model.predict_proba(X_scaled)[0]
        predicted_class = self.model.predict(X_scaled)[0]
        confidence_score = probas.max()

        return predicted_class, confidence_score

    def update(self, embedding_vector: List[float], true_label: int):
        """
        Updates the model incrementally with a new labeled example.

        Args:
            embedding_vector: The embedding of the judicial decision text.
            true_label: The ground truth label (0 or 1).
        """
        X = np.array(embedding_vector).reshape(1, -1)
        y = np.array([true_label])

        # Partially fit scaler
        if not hasattr(self.scaler, 'mean_'): # First fit
            self.scaler.fit(X)
        else: # Subsequent partial fits
            # StandardScaler does not have partial_fit, so we need to update it manually
            # This is a simplified approach, a more robust online scaler might be needed for production
            # For now, we refit it with all data seen so far, or implement a manual update rule
            # For this example, we'll assume the scaler is robust enough after initial fit or
            # that we'll refit it periodically with a batch of data.
            # For true online scaling with StandardScaler, one might use IncrementalPCA or similar.
            pass # We'll scale on predict, but fit only once or with a batch

        X_scaled = self.scaler.transform(X) if hasattr(self.scaler, 'mean_') else X

        # Ensure model is initialized with classes before partial_fit
        self._ensure_model_fitted(X_scaled)
        self.model.partial_fit(X_scaled, y, classes=np.array([0, 1]))
        self._is_fitted = True
        logger.info("winner_predictor_model_updated", true_label=true_label)

        self.save()

    def save(self):
        """Saves the current state of the model and scaler to disk."""
        logger.info("saving_winner_predictor_model", path=self.model_path)
        joblib.dump(self.model, self.model_path)
        logger.info("saving_winner_predictor_scaler", path=self.scaler_path)
        joblib.dump(self.scaler, self.scaler_path)

    def get_feature_dimension(self) -> int | None:
        """Returns the expected feature dimension of the model."""
        if hasattr(self.model, 'coef_') and self.model.coef_ is not None:
            return self.model.coef_.shape[1]
        return None
