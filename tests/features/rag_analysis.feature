Feature: RAG-Based Decision Analysis
  As a system administrator,
  I want to analyze judicial decisions using RAG (Retrieval-Augmented Generation),
  So that I can classify decisions at 98% lower cost than LLM-only analysis.

  Background:
    Given the system has a vector store initialized
    And the vector store contains ground truth decisions

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
    And the confidence score should be between 0.60 and 0.80
    And the analysis method should be "rag"

  Scenario: Analyze a decision with low confidence using RAG
    Given I have a decision text with unclear outcome
    When I analyze the decision using RAG
    Then an outcome should be returned
    And the confidence score should be less than 0.60
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

  Scenario: Classify using k-NN voting
    Given I have decision embeddings
    And the vector store has 5 similar WIN decisions and 2 LOSS decisions
    When I classify using k=7 nearest neighbors
    Then the outcome should be "WIN"
    And the confidence should be approximately 0.71
    And the vote distribution should show 5 WIN and 2 LOSS

  Scenario: Track RAG analysis costs
    Given I analyze 100 decisions using RAG
    When I calculate the total cost
    Then the cost should be approximately $0.0008
    And the cost per decision should be $0.000008

  Scenario: Batch analysis with RAG
    Given I have 10 pending decisions to analyze
    When I run batch analysis using RAG
    Then all 10 decisions should be classified
    And the analysis method for all should be "rag"
    And the total processing time should be less than 60 seconds
