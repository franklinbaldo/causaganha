Feature: Winner Prediction Subsystem

  As a data scientist or engineer
  I want to optionally predict who won judicial decisions using embeddings and an online learner
  So that I can scale analysis without always invoking an expensive LLM, and improve predictions over time

  Scenario: Default off behavior
    Given the winner classifier is disabled
    When I run the analysis pipeline on a batch of decisions
    Then no embeddings are computed
    And no teacher LLM calls are made
    And the persisted analysis results do not contain ML prediction fields

  Scenario: Inference mode
    Given the winner classifier is set to "infer"
    And the learner is untrained
    When I run the analysis pipeline on a decision
    Then the decision text is embedded
    And the learner predicts a result with low confidence
    And the analysis result contains "winner_ml_pred" and "winner_ml_confidence"
    But the analysis result does not contain "winner_teacher_label"

  Scenario: Teach mode with model update
    Given the winner classifier is set to "teach"
    And a fake teacher that returns "plaintiff_won"
    When I run the analysis pipeline on a decision
    Then the decision text is embedded
    And the learner predicts a result
    And the teacher is called to label the decision
    And the learner is updated with the new example
    And the analysis result contains "winner_teacher_label" and "winner_model_version"

  Scenario: Bootstrap from DB
    Given the winner classifier is set to "teach" with bootstrap "auto"
    And the database contains 10 labeled decisions
    And the model is initially untrained
    When I run the analysis pipeline
    Then the model is trained on the 10 historical decisions first
    And then the new decisions are processed using the trained model

  Scenario: Bootstrap limit
    Given the winner classifier is set to "teach" with bootstrap "auto"
    And the database contains 1000 labeled decisions
    And the bootstrap limit is set to 50
    When I run the analysis pipeline
    Then the model is trained on at most 50 historical decisions
