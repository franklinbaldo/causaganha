Feature: RAG-Based Decision Analysis (Zero-Shot)
  As a system administrator,
  I want to analyze judicial decisions using zero-shot RAG,
  So that I can classify decisions at 98% lower cost than LLM-only analysis without needing ground truth data.

  Background:
    Given the RAG analyzer is initialized with generic outcome phrases

  Scenario: Analyze a decision with high confidence using RAG
    Given I have a decision text about a clear win outcome
    When I analyze the decision using RAG
    Then the outcome should be classified as "WIN"
    And the confidence score should be greater than 0.80
    And the analysis method should be "rag"

  Scenario: Analyze a decision with medium confidence using RAG
    Given I have a decision text with mixed signals
    When I analyze the decision using RAG
    Then an outcome should be returned
    And the confidence score should be between 0.70 and 0.85
    And the analysis method should be "rag"

  Scenario: Analyze a decision with low confidence using RAG
    Given I have a decision text with unclear outcome
    When I analyze the decision using RAG
    Then an outcome should be returned
    And the confidence score should be less than 0.70
    And the analysis method should be "rag"

  Scenario: Chunk decision text for embedding
    Given I have a decision text of 2000 characters
    When I chunk the text with 500 character chunks and 100 character overlap
    Then I should get 5 chunks
    And each chunk should be approximately 500 characters
    And consecutive chunks should have overlapping content

  Scenario: Generate embeddings for decision chunks
    Given I have 3 decision text chunks
    When I generate embeddings for the chunks
    Then I should receive 3 embedding vectors
    And each embedding should have 768 dimensions

  Scenario: Classify chunk using zero-shot similarity
    Given I have a decision chunk embedding
    And the system has outcome phrases embedded
    When I classify the chunk using cosine similarity
    Then the chunk should be classified to the most similar outcome
    And the similarity score should be between 0.0 and 1.0

  Scenario: Track RAG analysis costs
    Given I analyze 100 decisions using RAG
    When I calculate the total cost
    Then the cost should be approximately $0.0004
    And the cost per decision should be $0.000004

  Scenario: Batch analysis with RAG
    Given I have 10 pending decisions to analyze
    When I run batch analysis using RAG
    Then all 10 decisions should be classified
    And the analysis method for all should be "rag"
    And the total processing time should be less than 60 seconds
