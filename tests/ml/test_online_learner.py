"""Unit tests for the WinnerPredictor online learning model."""

import os
import joblib
import numpy as np
import pytest
from causaganha.ml.online_learner import WinnerPredictor

@pytest.fixture
def model_paths():
    """Provides paths for a temporary model and scaler for testing."""
    model_path = "test_winner_predictor.joblib"
    scaler_path = "test_winner_predictor_scaler.joblib"
    yield model_path, scaler_path
    # Teardown: clean up created files
    if os.path.exists(model_path):
        os.remove(model_path)
    if os.path.exists(scaler_path):
        os.remove(scaler_path)

def test_winner_predictor_initialization(model_paths):
    """Tests that the WinnerPredictor initializes correctly, creating a new model."""
    model_path, scaler_path = model_paths
    predictor = WinnerPredictor(model_path=model_path, scaler_path=scaler_path)
    assert predictor.model is not None
    assert predictor.scaler is not None
    assert not predictor._is_fitted

def test_winner_predictor_save_and_load(model_paths):
    """Tests that the model and scaler can be saved and reloaded."""
    model_path, scaler_path = model_paths
    
    # Create and save a dummy model
    predictor1 = WinnerPredictor(model_path=model_path, scaler_path=scaler_path)
    # Give it some dummy data to fit
    X = np.random.rand(2, 10)
    y = np.array([0, 1])
    predictor1.update(X[0].tolist(), y[0])
    predictor1.update(X[1].tolist(), y[1])
    predictor1.save()

    assert os.path.exists(model_path)
    assert os.path.exists(scaler_path)

    # Load the model
    predictor2 = WinnerPredictor(model_path=model_path, scaler_path=scaler_path)
    assert predictor2._is_fitted
    assert predictor2.get_feature_dimension() == 10

def test_winner_predictor_predict_and_update(model_paths):
    """Tests the predict and update cycle."""
    model_path, scaler_path = model_paths
    predictor = WinnerPredictor(model_path=model_path, scaler_path=scaler_path)

    # Dummy data
    embedding_dim = 128
    X_train = np.random.rand(10, embedding_dim)
    y_train = np.random.randint(0, 2, 10)

    # Update the model with some data
    for i in range(len(X_train)):
        predictor.update(X_train[i].tolist(), y_train[i])

    # Test prediction
    X_test = np.random.rand(1, embedding_dim)
    prediction, confidence = predictor.predict(X_test[0].tolist())

    assert prediction in [0, 1]
    assert 0.0 <= confidence <= 1.0

def test_unfitted_model_prediction(model_paths):
    """Tests that an unfitted model returns a default prediction."""
    model_path, scaler_path = model_paths
    predictor = WinnerPredictor(model_path=model_path, scaler_path=scaler_path)
    
    embedding_dim = 128
    X_test = np.random.rand(1, embedding_dim)
    
    prediction, confidence = predictor.predict(X_test[0].tolist())
    
    assert prediction == 0
    assert confidence == 0.5