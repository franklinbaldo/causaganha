Feature: Winner Prediction using Online Learning

  As a user, I want to use an online learning model to predict the winner of a judicial decision,
  with the option to use an LLM as a teacher to continuously improve the model.

  Scenario: Winner classifier is disabled by default
    Given the application is run without the winner classifier flag
    When the analysis pipeline is executed
    Then the winner classifier should not be loaded
    And no embeddings should be generated

  Scenario: Running inference with the winner classifier
    Given a pre-trained winner predictor model exists
    And the application is run with "--winner-classifier=infer"
    And a judicial decision to be analyzed
    When the analysis pipeline is executed
    Then embeddings should be generated for the decision
    And the winner classifier should predict the outcome
    And the prediction should be stored in the analysis results

  Scenario: Running the teacher-LLM for labeling and model update
    Given a winner predictor model exists
    And the application is run with "--winner-classifier=teach"
    And a judicial decision to be analyzed
    When the analysis pipeline is executed
    Then embeddings should be generated for the decision
    And the winner classifier should predict the outcome
    And the teacher LLM should provide a ground truth label for the decision
    And the winner classifier should be updated with the new label
    And the prediction and teacher label should be stored in the analysis results

  Scenario: Handling multiple decisions in parallel
    Given a winner predictor model exists
    And the application is run with "--winner-classifier=teach" and "--jobs=4"
    And there are 10 judicial decisions to be analyzed
    When the analysis pipeline is executed
    Then the decisions should be processed in parallel
    And for each decision, embeddings, prediction, and teaching should happen
    And the winner classifier should be updated online