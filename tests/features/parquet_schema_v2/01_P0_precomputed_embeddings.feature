Feature: Pre-computed Embeddings in Parquet (P0 - Critical)
  As a data analyst
  I want parquet files to include pre-computed embeddings
  So that RAG analysis is 3-5x faster and costs $8K/year less

  Background:
    Given the system is configured with Jina v3 embeddings
    And the embedding dimension is 1024 floats

  @p0 @embeddings @export
  Scenario: Export parquet with pre-computed embeddings
    Given I have 100 analyzed decisions in the database
    And each decision has a "texto" field with full decision text
    When I export to parquet with schema version "v2"
    Then the parquet file should contain a "texto_embedding" column
    And each embedding should be a list of 1024 floats
    And the parquet file should contain an "embedding_model" column with value "jina-embeddings-v3"
    And the parquet file should contain an "embedding_generated_at" timestamp column
    And the file size should be approximately 80% larger than schema v1

  @p0 @embeddings @analysis
  Scenario: RAG analysis using cached embeddings from parquet
    Given I have a parquet file with pre-computed embeddings
    And I have a RAG analyzer configured
    When I analyze 100 decisions from the parquet file
    Then the RAG analyzer should use cached embeddings
    And the RAG analyzer should NOT call the embedding API
    And the analysis should complete in less than 30 seconds
    And the cost should be $0.0008 (100 × $0.000008)

  @p0 @embeddings @performance
  Scenario: Performance comparison - cached vs generated embeddings
    Given I have a parquet file with 1000 decisions
    And the parquet file includes pre-computed embeddings
    When I measure RAG analysis time with cached embeddings
    And I measure RAG analysis time with fresh embedding generation
    Then cached embedding analysis should be 3-5x faster
    And cached embedding analysis should save $8 in API costs

  @p0 @embeddings @validation
  Scenario: Validate embedding quality in parquet
    Given I have a parquet file with pre-computed embeddings
    When I read the embeddings from the parquet file
    Then each embedding should have exactly 1024 dimensions
    And each embedding value should be a float32
    And no embeddings should be null or empty
    And embeddings should be normalized (L2 norm ≈ 1.0)

  @p0 @embeddings @backward-compatibility
  Scenario: Schema v1 parquet files still work without embeddings
    Given I have a schema v1 parquet file without embeddings
    When I analyze decisions from the v1 parquet file
    Then the system should generate embeddings on-the-fly
    And the analysis should complete successfully
    And a warning should be logged about missing cached embeddings

  @p0 @embeddings @migration
  Scenario: Re-export schema v1 files to v2 with embeddings
    Given I have a schema v1 parquet file from date "2025-01-15" for tribunal "TJRO"
    When I run the migration command to re-export as schema v2
    Then a new parquet file should be created with embeddings
    And the new file should be uploaded to Internet Archive
    And the old schema v1 file should remain accessible
    And the parquet_exports table should track both versions

  @p0 @embeddings @cost-tracking
  Scenario: Track embedding generation costs during export
    Given I have 10000 unanalyzed decisions to export
    And none have pre-computed embeddings
    When I export to parquet with schema v2
    Then embeddings should be generated for all decisions
    And the embedding generation cost should be approximately $0.08
    And the cost should be logged in the export statistics
    And the "embedding_generated_at" timestamp should be recorded

  @p0 @embeddings @similarity-search
  Scenario: Enable similarity search directly on parquet
    Given I have a parquet file with pre-computed embeddings
    And I have a query text "sentença de primeira instância procedente"
    When I compute the query embedding
    And I calculate cosine similarity with all embeddings in parquet
    Then I should find the top 10 most similar decisions
    And the results should be ranked by similarity score
    And the search should complete in less than 5 seconds

  @p0 @embeddings @distributed-analysis
  Scenario: Analyze parquet file on a different machine without embedding API
    Given I download a schema v2 parquet file from Internet Archive
    And I do NOT have access to the Jina embedding API
    When I run RAG analysis on the downloaded parquet file
    Then the analysis should use cached embeddings from the parquet
    And the analysis should complete successfully without API calls
    And the analysis accuracy should match the original system
