Feature: Separate Embeddings Parquet (P0 - Critical, Revised Architecture)
  As a data architect
  I want embeddings in a separate parquet file with the same key as decisions
  So that I can hydrate vector stores, regenerate embeddings, and query selectively

  Background:
    Given the system uses multi-parquet architecture
    And embeddings are stored separately from decisions
    And both use intimation_id as the join key

  @p0 @embeddings @separate-file @export
  Scenario: Export embeddings to separate parquet file
    Given I have 1000 analyzed decisions for date "2025-01-15" tribunal "TJRO"
    And each decision has a texto field
    When I export embeddings with schema v2
    Then a separate file "causaganha-embeddings-2025-01-15-TJRO.parquet" should be created
    And it should contain columns: intimation_id, texto_embedding, embedding_model, embedding_version, embedding_generated_at, texto_hash
    And the intimation_id should match decisions parquet
    And the file size should be approximately 40 MB (1000 × 1024 floats × 4 bytes)
    And the decisions parquet should NOT contain embedding columns

  @p0 @embeddings @separate-file @join-key
  Scenario: Embeddings and decisions share the same key
    Given I have decisions parquet with intimation_ids: [1, 2, 3, 4, 5]
    And I have embeddings parquet with intimation_ids: [1, 2, 3, 4, 5]
    When I join using DuckDB:
      ```sql
      SELECT d.*, e.texto_embedding
      FROM decisions d
      INNER JOIN embeddings e ON d.intimation_id = e.intimation_id
      ```
    Then all 5 rows should match
    And each row should have decision data + embedding

  @p0 @embeddings @separate-file @schema
  Scenario: Embeddings parquet schema definition
    Given I export embeddings to separate parquet
    When I inspect the schema
    Then it should have the following columns:
      | column                  | type              | description                           |
      | intimation_id           | int64             | Primary key, matches decisions        |
      | texto_embedding         | list<float32>[1024] | Jina v3 embedding vector            |
      | embedding_model         | string            | Model name (e.g., "jina-embeddings-v3") |
      | embedding_version       | string            | Schema version (e.g., "v1")          |
      | embedding_generated_at  | timestamp         | When embedding was generated         |
      | texto_hash              | string            | SHA256 hash of texto for validation  |
    And the primary key should be intimation_id
    And the file should be partitioned by date + tribunal

  @p0 @embeddings @separate-file @vector-store-hydration
  Scenario: Hydrate vector store from Internet Archive embeddings parquet
    Given I need to hydrate a vector store for similarity search
    And I do NOT have local embeddings cached
    When I download embeddings parquet from Internet Archive
    And I load embeddings into vector store:
      ```python
      embeddings_df = pq.read_table("s3://ia/causaganha-embeddings-2025-01-15-TJRO.parquet")
      for batch in embeddings_df.iter_batches(batch_size=100):
          vector_store.add(
              ids=batch['intimation_id'].to_pylist(),
              embeddings=batch['texto_embedding'].to_numpy()
          )
      ```
    Then the vector store should contain 1000 embeddings
    And I should be able to perform similarity search
    And I did NOT need to download decisions parquet (saved bandwidth!)

  @p0 @embeddings @separate-file @rag-analysis
  Scenario: RAG analysis using separate embeddings parquet
    Given I have decisions parquet on Internet Archive
    And I have embeddings parquet on Internet Archive
    When I run RAG analysis:
      ```python
      # Download both files (or use DuckDB on IA directly)
      decisions = pq.read_table("s3://ia/decisions-2025-01-15-TJRO.parquet")
      embeddings = pq.read_table("s3://ia/embeddings-2025-01-15-TJRO.parquet")

      # Join in memory or via DuckDB
      joined = decisions.join(embeddings, keys='intimation_id')

      # Use cached embeddings for RAG
      for row in joined.to_pandas().itertuples():
          result = rag_analyzer.analyze_with_embedding(
              texto=row.texto,
              cached_embedding=row.texto_embedding
          )
      ```
    Then RAG analysis should use cached embeddings
    And no embedding API calls should be made
    And analysis should be 3-5x faster than generating embeddings

  @p0 @embeddings @separate-file @regeneration
  Scenario: Regenerate embeddings without touching decisions
    Given I have decisions parquet from 2025-01-15
    And I have embeddings parquet using jina-v3
    And a new model jina-v4 is released with better quality
    When I regenerate embeddings:
      ```bash
      causaganha embeddings regenerate \
        --source decisions-2025-01-15-TJRO.parquet \
        --model jina-v4 \
        --output embeddings-jina-v4-2025-01-15-TJRO.parquet
      ```
    Then a new embeddings file should be created
    And the embedding_model field should be "jina-embeddings-v4"
    And the embedding_version field should be "v2"
    And the decisions parquet should remain unchanged
    And I can compare jina-v3 vs jina-v4 performance

  @p0 @embeddings @separate-file @model-versions
  Scenario: Store multiple embedding versions for same decisions
    Given I have decisions parquet for 2025-01-15
    When I generate embeddings with different models:
      | model           | output_file                                   |
      | jina-v3         | embeddings-jina-v3-2025-01-15-TJRO.parquet   |
      | jina-v4         | embeddings-jina-v4-2025-01-15-TJRO.parquet   |
      | openai-ada-002  | embeddings-openai-2025-01-15-TJRO.parquet    |
    Then I should have 3 different embeddings files
    And all should use the same intimation_id as decisions
    And I can A/B test different embedding models
    And I can query: "Which model gives better RAG accuracy?"

  @p0 @embeddings @separate-file @selective-download
  Scenario: Selective download - decisions only or with embeddings
    Given I have both decisions and embeddings on Internet Archive
    When I only need decision text and analysis results
    Then I download only decisions parquet (50 MB)
    And I save 40 MB bandwidth (embeddings not needed)
    When I need RAG analysis
    Then I download both decisions and embeddings (90 MB total)
    And I can join them locally or via DuckDB

  @p0 @embeddings @separate-file @duckdb-query
  Scenario: DuckDB query joining decisions and embeddings
    Given I have decisions parquet at "s3://ia/decisions-2025-01-15-TJRO.parquet"
    And I have embeddings parquet at "s3://ia/embeddings-2025-01-15-TJRO.parquet"
    When I run DuckDB query:
      ```sql
      SELECT
        d.intimation_id,
        d.numero_processo,
        d.texto,
        d.outcome,
        e.texto_embedding,
        e.embedding_model
      FROM 's3://ia/decisions-2025-01-15-TJRO.parquet' d
      INNER JOIN 's3://ia/embeddings-2025-01-15-TJRO.parquet' e
        ON d.intimation_id = e.intimation_id
      WHERE d.confidence_breakdown.overall > 0.80
      LIMIT 100
      ```
    Then DuckDB should return 100 rows with both decision and embedding data
    And the query should complete in less than 5 seconds
    And DuckDB should use efficient columnar join

  @p0 @embeddings @separate-file @validation
  Scenario: Validate embeddings match decisions using texto_hash
    Given I have decisions parquet with texto field
    And I have embeddings parquet with texto_hash field
    When I calculate SHA256 hash of texto in decisions
    And I compare with texto_hash in embeddings
    Then all hashes should match
    And this confirms embeddings are for the correct texto
    And I can detect if texto was modified after embedding generation

  @p0 @embeddings @separate-file @storage-efficiency
  Scenario: Compare storage efficiency - monolithic vs separate
    Given I have 10000 decisions
    When I calculate storage for monolithic approach (embeddings in decisions):
      | component   | size      |
      | Decisions   | 50 MB     |
      | Embeddings  | 40 MB     |
      | Total       | 90 MB     |
    And I calculate storage for separate files approach:
      | file                | size      | can_skip |
      | Decisions parquet   | 50 MB     | No       |
      | Embeddings parquet  | 40 MB     | Yes      |
      | Total               | 90 MB     | -        |
    Then total storage is the same (90 MB)
    But separate approach allows selective download
    And I can regenerate embeddings without touching decisions
    And I can version embedding models independently

  @p0 @embeddings @separate-file @export-workflow
  Scenario: Export workflow with separate embeddings file
    Given I have 1000 analyzed decisions to export
    When I run: causaganha export parquet --date 2025-01-15 --tribunal TJRO --schema v2
    Then the system should:
      | step | action                                             |
      | 1    | Export decisions to decisions-2025-01-15-TJRO.parquet |
      | 2    | Generate embeddings for all texto fields           |
      | 3    | Export embeddings to embeddings-2025-01-15-TJRO.parquet |
      | 4    | Upload both files to Internet Archive             |
      | 5    | Record both files in parquet_exports table        |
    And both files should be accessible on Internet Archive
    And both files should use the same intimation_id as join key

  @p0 @embeddings @separate-file @cost-tracking
  Scenario: Track embedding generation costs separately
    Given I export 10000 decisions with embeddings
    When I generate embeddings for all texto fields
    Then the embedding cost should be approximately $0.80 (10000 × $0.00008)
    And this cost should be logged separately in export statistics
    And I can track: "How much do we spend on embeddings per month?"
    And the cost should be associated with the embeddings parquet file

  @p0 @embeddings @separate-file @missing-embeddings
  Scenario: Handle missing embeddings gracefully
    Given I have decisions parquet with 1000 rows
    And I have embeddings parquet with only 800 rows (200 missing)
    When I join decisions with embeddings using LEFT JOIN
    Then 800 rows should have embeddings
    And 200 rows should have null embeddings
    And the system should log a warning about missing embeddings
    And I can filter: WHERE texto_embedding IS NOT NULL

  @p0 @embeddings @separate-file @incremental-generation
  Scenario: Incrementally generate missing embeddings
    Given I have decisions parquet with 1000 rows
    And I have embeddings parquet with only 800 rows
    When I run: causaganha embeddings generate --missing-only --date 2025-01-15
    Then the system should identify 200 missing embeddings
    And generate embeddings only for those 200 decisions
    And append to the embeddings parquet file
    And the cost should be $0.016 (200 × $0.00008) instead of $0.80 for all
