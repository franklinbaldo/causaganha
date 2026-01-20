Feature: Hybrid RAG + LLM Analysis Strategy
  As a system administrator,
  I want to use a hybrid approach combining RAG and LLM,
  So that I can optimize for both cost and accuracy.

  Background:
    Given the system has both RAG and LLM analyzers configured
    And the confidence threshold is set to 0.70

  Scenario: High confidence RAG result does not trigger LLM fallback
    Given I have a decision text with clear outcome signals
    When I analyze using hybrid strategy
    Then the RAG analyzer should be used
    And the LLM analyzer should not be called
    And the confidence score should be greater than 0.70
    And the analysis method should be "rag"
    And the cost should be $0.000008

  Scenario: Low confidence RAG result triggers LLM fallback
    Given I have a decision text with ambiguous outcome
    When I analyze using hybrid strategy
    Then the RAG analyzer should be tried first
    And the LLM analyzer should be called as fallback
    And the confidence score from LLM should be used
    And the analysis method should be "hybrid"
    And the cost should be $0.000420

  Scenario: Hybrid strategy with custom confidence threshold
    Given the confidence threshold is set to 0.80
    And I have a decision with RAG confidence of 0.75
    When I analyze using hybrid strategy
    Then the LLM fallback should be triggered
    And the analysis method should be "hybrid"

  Scenario: Batch analysis with hybrid strategy cost savings
    Given I have 100 decisions to analyze
    And 70 decisions have clear outcomes (high confidence)
    And 30 decisions have ambiguous outcomes (low confidence)
    When I run batch analysis using hybrid strategy
    Then 70 decisions should be analyzed with RAG
    And 30 decisions should use LLM fallback
    And the total cost should be approximately $0.0132
    And the cost savings compared to LLM-only should be 68%

  Scenario: Track method usage statistics
    Given I have analyzed 50 decisions using hybrid strategy
    And 35 used RAG and 15 used LLM fallback
    When I check the analysis statistics
    Then the RAG usage rate should be 70%
    And the LLM fallback rate should be 30%
    And the average cost per decision should be approximately $0.000132

  Scenario: Hybrid strategy without PDF URL falls back gracefully
    Given I have a decision text with low RAG confidence
    And no PDF URL is available
    When I analyze using hybrid strategy
    Then the RAG result should be returned
    And the analysis method should be "rag_low_confidence"
    And a warning should be logged about missing PDF URL

  Scenario: Strategy selection via configuration
    Given the analysis strategy is set to "llm"
    When I analyze a decision
    Then only the LLM analyzer should be used
    And the analysis method should be "llm"
    And the cost should be $0.000420

  Scenario: Strategy selection for RAG only
    Given the analysis strategy is set to "rag"
    When I analyze a decision with low confidence outcome
    Then only the RAG analyzer should be used
    And no LLM fallback should occur
    And the analysis method should be "rag"
    And the cost should be $0.000008

  Scenario: Default strategy is hybrid
    Given no analysis strategy is explicitly configured
    When I analyze a decision
    Then the hybrid strategy should be used automatically

  Scenario: Store RAG confidence even when using LLM fallback
    Given I have a decision with RAG confidence of 0.55
    When I analyze using hybrid strategy with LLM fallback
    Then the final result should include the LLM outcome
    And the rag_confidence field should be 0.55
    And the rag_votes should be preserved
    And the analysis method should be "hybrid"
