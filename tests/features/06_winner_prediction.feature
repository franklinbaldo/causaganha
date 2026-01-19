Feature: ML-Powered Winner Prediction
  As a product manager
  I want to predict case winners using machine learning
  So that I can reduce LLM costs and scale analysis to thousands of decisions

  Background:
    Given the CausaGanha database is initialized
    And the ML subsystem is available

  # ============================================================================
  # CORE ML MODES
  # ============================================================================

  Scenario: Default off mode - no ML processing
    Given the winner classifier is disabled (mode "off")
    When I run the analysis pipeline on a batch of decisions
    Then no embeddings are computed
    And no teacher LLM calls are made
    And no ML model training occurs
    And the analysis results do not contain ML prediction fields
    And the analysis uses only the standard LLM analyzer

  Scenario: Inference mode - predict without learning
    Given the winner classifier is set to "infer"
    And the learner model is untrained
    When I run the analysis pipeline on a decision
    Then the decision text is embedded into a vector
    And the learner predicts a result with low confidence
    And the analysis result contains "winner_ml_pred" field
    And the analysis result contains "winner_ml_confidence" field
    But the analysis result does not contain "winner_teacher_label"
    And the model is not updated

  Scenario: Teach mode - predict and learn from LLM teacher
    Given the winner classifier is set to "teach"
    And a teacher LLM is configured
    When I run the analysis pipeline on a decision
    Then the decision text is embedded
    And the learner predicts a result
    And the teacher LLM is called to label the decision
    And the learner is updated with the new labeled example
    And the analysis result contains "winner_teacher_label"
    And the analysis result contains "winner_model_version"
    And the model version number increments

  # ============================================================================
  # BOOTSTRAP SCENARIOS
  # ============================================================================

  Scenario: Bootstrap from historical labeled decisions (auto mode)
    Given the winner classifier is set to "teach" with bootstrap "auto"
    And the database contains 100 labeled decisions from prior analyses
    And the ML model is initially untrained
    When I run the analysis pipeline
    Then the model should be trained on the 100 historical decisions first
    And the model confidence should increase after bootstrap
    And then new decisions should be processed using the trained model
    And the model should make better predictions after bootstrap

  Scenario: Bootstrap respects maximum limit
    Given the winner classifier is set to "teach" with bootstrap "auto"
    And the database contains 1000 labeled decisions
    And the bootstrap limit is set to 50
    When I run the analysis pipeline
    Then the model is trained on exactly 50 historical decisions
    And the 50 decisions should be randomly sampled
    And the remaining 950 should not be used for bootstrap

  Scenario: Force bootstrap even with existing model
    Given the winner classifier is set to "teach" with bootstrap "force"
    And the model is already trained with 100 examples
    And the database contains 200 labeled decisions
    When I run the analysis pipeline
    Then the model should be reset and retrained from scratch
    And all 200 decisions should be used for bootstrap
    And the previous model state should be discarded

  Scenario: Bootstrap disabled when set to off
    Given the winner classifier is set to "teach" with bootstrap "off"
    And the database contains 500 labeled decisions
    When I run the analysis pipeline
    Then the model should start untrained
    And historical decisions should not be used
    And only new decisions should train the model incrementally

  # ============================================================================
  # EMBEDDING GENERATION
  # ============================================================================

  Scenario: Generate embeddings from decision text
    Given a decision text containing legal arguments
    When the embedding service is called
    Then the text should be converted to a numerical vector
    And the vector should have consistent dimensions
    And the embedding should capture semantic meaning

  Scenario: Cache embeddings to avoid recomputation
    Given a decision has been embedded once
    When the same decision is processed again
    Then the cached embedding should be used
    And no new embedding API call should be made

  Scenario: Handle large decision texts for embedding
    Given a decision text with 50,000 characters
    When the embedding service is called
    Then the text should be truncated or chunked appropriately
    And the embedding should be generated successfully
    And no errors should occur due to text length

  # ============================================================================
  # ONLINE LEARNING
  # ============================================================================

  Scenario: Model improves with each labeled example
    Given the winner classifier is in "teach" mode
    And the model starts with 0 labeled examples
    When I process 100 decisions with teacher labels
    Then the model accuracy should improve over time
    And later predictions should have higher confidence
    And the model version should increment to 100

  Scenario: SGD classifier updates weights incrementally
    Given the winner classifier is in "teach" mode
    And a decision is predicted as "PLAINTIFF_WON" with confidence 0.4
    And the teacher labels it as "PLAINTIFF_WON" (correct prediction)
    When the model is updated with this example
    Then the weights should be adjusted to reinforce the correct prediction
    And future similar decisions should have higher confidence

  Scenario: Model corrects from incorrect predictions
    Given the winner classifier is in "teach" mode
    And a decision is predicted as "DEFENDANT_WON" with confidence 0.7
    And the teacher labels it as "PLAINTIFF_WON" (incorrect prediction)
    When the model is updated with this example
    Then the weights should be adjusted to correct the mistake
    And the model should learn from the error

  # ============================================================================
  # PREDICTION LABELS
  # ============================================================================

  Scenario Outline: Predict different winner labels
    Given the winner classifier is in "infer" mode
    And the model is trained on labeled examples
    When I process a decision with text "<decision_text>"
    Then the ML prediction should be "<expected_label>"

    Examples:
      | decision_text                                      | expected_label     |
      | Julgo procedente o pedido do autor                 | PLAINTIFF_WON      |
      | Julgo improcedente a ação                          | DEFENDANT_WON      |
      | Extingo o processo sem resolução de mérito         | UNCLEAR            |
      | Decision text is ambiguous and incomplete          | UNCLEAR            |

  # ============================================================================
  # CONFIDENCE SCORING
  # ============================================================================

  Scenario: High confidence predictions from trained model
    Given the winner classifier is in "infer" mode
    And the model is trained on 1000 labeled examples
    When I process a clear, typical decision
    Then the ML confidence should be above 0.8
    And the prediction should align with the model's training data

  Scenario: Low confidence predictions from untrained model
    Given the winner classifier is in "infer" mode
    And the model has seen only 5 labeled examples
    When I process a decision
    Then the ML confidence should be below 0.3
    And the prediction should be conservative

  Scenario: Medium confidence for edge cases
    Given the winner classifier is in "infer" mode
    And the model is moderately trained
    When I process an unusual decision not well-represented in training data
    Then the ML confidence should be between 0.4 and 0.6
    And the prediction should indicate uncertainty

  # ============================================================================
  # TEACHER LLM INTEGRATION
  # ============================================================================

  Scenario: Teacher LLM labels decision for training
    Given the winner classifier is in "teach" mode
    And a decision needs labeling
    When the teacher LLM is invoked
    Then the teacher should analyze the decision
    And the teacher should return a WinnerLabel (PLAINTIFF_WON, DEFENDANT_WON, or UNCLEAR)
    And the teacher label should be stored in the analysis result

  Scenario: Handle teacher LLM failures gracefully
    Given the winner classifier is in "teach" mode
    And the teacher LLM API is temporarily unavailable
    When I process a decision
    Then the ML prediction should still be made
    And the decision should be marked for later teacher labeling
    And the model should not be updated for this example

  Scenario: Validate teacher LLM responses
    Given the winner classifier is in "teach" mode
    And the teacher LLM returns an invalid label
    When the response is validated
    Then the invalid label should be rejected
    And a warning should be logged
    And the model should not be updated with invalid data

  # ============================================================================
  # COST OPTIMIZATION
  # ============================================================================

  Scenario: ML predictions reduce LLM costs in production
    Given the winner classifier is in "infer" mode
    And the model is trained with 5000 examples
    And model confidence threshold for skipping LLM is 0.85
    When I process 100 new decisions
    And 80 of them have ML confidence > 0.85
    Then only 20 decisions should trigger LLM analysis
    And 80 decisions should use ML predictions only
    And LLM API costs should be reduced by 80%

  Scenario: Teach mode balances learning and cost
    Given the winner classifier is in "teach" mode
    And the model is moderately trained
    When I process 100 decisions
    Then all 100 should trigger teacher LLM calls for labeling
    And the model should improve with each labeled example
    And the cost should be offset by future inference savings

  # ============================================================================
  # MODEL PERSISTENCE
  # ============================================================================

  Scenario: Save trained model for future use
    Given the winner classifier is in "teach" mode
    When I process 500 decisions
    And the pipeline completes
    Then the trained model should be persisted to disk
    And the model file should include version number
    And the model should be loadable in future runs

  Scenario: Load existing model on startup
    Given a trained model exists from a previous run
    And the winner classifier is in "infer" mode
    When the pipeline starts
    Then the existing model should be loaded automatically
    And the model version should match the saved version
    And predictions should use the loaded model

  Scenario: Track model version across runs
    Given the winner classifier is in "teach" mode
    And the current model version is 250
    When I process 50 more decisions
    Then the model version should increment to 300
    And the version should be recorded in analysis results
    And the version should persist across restarts

  # ============================================================================
  # INTEGRATION WITH STANDARD ANALYSIS
  # ============================================================================

  Scenario: ML prediction complements LLM analysis
    Given the winner classifier is in "infer" mode
    And the standard LLM analyzer is enabled
    When I process a decision
    Then both ML prediction and LLM analysis should be performed
    And the analysis result should contain both predictions
    And discrepancies should be flagged for review

  Scenario: Use ML prediction as validation for LLM
    Given the winner classifier is in "infer" mode with high confidence
    And the LLM analyzer returns a decision
    When the ML prediction conflicts with LLM analysis
    Then a warning should be logged
    And the discrepancy should be marked for manual review
    And both predictions should be stored for comparison

  # ============================================================================
  # ERROR HANDLING
  # ============================================================================

  Scenario: Handle embedding service failures
    Given the winner classifier is in "infer" mode
    And the embedding API is unavailable
    When I process a decision
    Then the system should retry the embedding request
    And if retries fail, the decision should be processed without ML
    And the standard LLM analysis should continue
    And the error should be logged

  Scenario: Handle corrupted model files
    Given a trained model file is corrupted
    And the winner classifier is in "infer" mode
    When the pipeline starts
    Then the system should detect the corruption
    And the model should be reinitialized from scratch
    And a warning should be logged about model reset

  # ============================================================================
  # PERFORMANCE
  # ============================================================================

  Scenario: ML inference is fast compared to LLM
    Given the winner classifier is in "infer" mode
    And the model is trained
    When I process 100 decisions
    Then ML predictions should complete in seconds
    And ML should be at least 50x faster than LLM analysis
    And the speed improvement should be measurable

  Scenario: Batch embedding for efficiency
    Given the winner classifier is in "infer" mode
    And there are 50 decisions to process
    When the pipeline runs
    Then embeddings should be computed in batches
    And batch processing should be faster than sequential
    And API rate limits should be respected

  # ============================================================================
  # MONITORING & OBSERVABILITY
  # ============================================================================

  Scenario: Track ML prediction accuracy over time
    Given the winner classifier is in "teach" mode
    When I process 1000 decisions with teacher labels
    Then the system should track prediction accuracy
    And accuracy metrics should be logged
    And accuracy should improve over time
    And metrics should be available for monitoring

  Scenario: Compare ML vs LLM agreement rates
    Given both ML and LLM analyzers are enabled
    When I process 500 decisions
    Then the system should track agreement rate between ML and LLM
    And the agreement rate should be above 80% for trained models
    And disagreements should be logged for analysis

  Scenario: Monitor model drift and degradation
    Given a model trained on old decisions
    When I process recent decisions with different patterns
    Then the system should detect if confidence decreases
    And a warning should be raised if model drift is detected
    And retraining should be suggested
