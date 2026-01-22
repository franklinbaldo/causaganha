Feature: Vector Store Hydration from Internet Archive
  As a RAG system operator
  I want to hydrate vector stores directly from Internet Archive embeddings parquet
  So that I can build search systems without local embedding generation

  Background:
    Given embeddings are stored separately on Internet Archive
    And embeddings parquet contains: intimation_id, texto_embedding, embedding_model, texto_hash
    And vector stores need embeddings for similarity search
    And I can download embeddings without downloading decisions

  @hydration @vector-store @on-demand
  Scenario: Hydrate vector store from IA embeddings parquet
    Given I need to build a similarity search for tribunal "TJRO"
    And I do NOT have embeddings generated locally
    When I run: causaganha vector-store hydrate --tribunal TJRO --date 2025-01-15
    Then the system should:
      | step | action |
      | 1 | Download embeddings-2025-01-15-TJRO.parquet from IA (40 MB) |
      | 2 | Read embeddings in batches of 1000 |
      | 3 | Insert into vector store (ChromaDB/Weaviate/Pinecone) |
      | 4 | Track progress: "Inserted 10000/10000 embeddings" |
      | 5 | Verify all embeddings loaded successfully |
    And I did NOT download decisions parquet (saved 50 MB bandwidth!)
    And the vector store should be ready for similarity search

  @hydration @vector-store @incremental
  Scenario: Incrementally update vector store with new embeddings
    Given I have a vector store with embeddings through 2025-01-14
    When new embeddings are exported for 2025-01-15
    And I run: causaganha vector-store update --since 2025-01-15
    Then the system should:
      | step | action |
      | 1 | Detect new embeddings files on IA |
      | 2 | Download only new embeddings (40 MB) |
      | 3 | Check which intimation_ids are new |
      | 4 | Insert only new embeddings (skip duplicates) |
      | 5 | Log: "Added 10000 new embeddings, skipped 0 duplicates" |
    And the vector store should be up-to-date

  @hydration @vector-store @selective-tribunals
  Scenario: Hydrate vector store for specific tribunals only
    Given I only care about 5 tribunals: TJRO, TJSP, TJRJ, TJMG, TJRS
    When I run: causaganha vector-store hydrate --tribunals TJRO,TJSP,TJRJ,TJMG,TJRS --date 2025-01-15
    Then the system should download embeddings for 5 tribunals only
    And skip the other 22 tribunals
    And save bandwidth: 22 × 40 MB = 880 MB saved!
    And the vector store should contain only selected tribunals

  @hydration @vector-store @date-range
  Scenario: Hydrate vector store for a date range
    Given I want to build a search covering January 2025
    When I run: causaganha vector-store hydrate --start 2025-01-01 --end 2025-01-31 --tribunal TJRO
    Then the system should:
      | step | action |
      | 1 | List all embeddings files for TJRO in January (31 files) |
      | 2 | Download each file sequentially or in parallel |
      | 3 | Insert embeddings maintaining temporal order |
      | 4 | Handle missing days gracefully (skip if not uploaded) |
      | 5 | Report: "Loaded 310000 embeddings from 31 days" |
    And I can search across the entire month

  @hydration @vector-store @validation
  Scenario: Validate embeddings during hydration
    Given I download embeddings from IA
    When I hydrate the vector store
    Then the system should validate:
      | check | validation |
      | Dimension | All vectors have 1024 dimensions |
      | Normalization | L2 norm ≈ 1.0 |
      | No nulls | No null vectors |
      | No duplicates | No duplicate intimation_ids |
      | Model consistency | All use same embedding_model |
    And reject invalid embeddings with error log
    And continue with valid embeddings

  @hydration @vector-store @metadata
  Scenario: Store metadata alongside embeddings
    Given I hydrate embeddings into vector store
    When I insert each embedding
    Then I should also store metadata:
      | metadata_field | source |
      | intimation_id | embeddings.intimation_id |
      | embedding_model | embeddings.embedding_model |
      | embedding_generated_at | embeddings.embedding_generated_at |
      | texto_hash | embeddings.texto_hash |
      | partition_date | embeddings.partition_date |
      | tribunal | Extracted from filename |
    And I can filter searches by metadata (e.g., tribunal, date)

  @hydration @vector-store @similarity-search
  Scenario: Perform similarity search after hydration
    Given I hydrated embeddings for TJRO 2025-01-15
    When I query: "decisão sobre rescisão contratual indenização"
    Then the system should:
      | step | action |
      | 1 | Generate embedding for query text |
      | 2 | Perform cosine similarity search |
      | 3 | Return top 10 similar decisions with intimation_ids |
      | 4 | Fetch full decision text from decisions parquet if needed |
    And results should be ranked by similarity score
    And I can use intimation_id to join with decisions parquet

  @hydration @vector-store @multi-model
  Scenario: Hydrate vector store with multiple embedding models
    Given I have embeddings from multiple models:
      | model | file |
      | jina-v3 | embeddings-jina-v3-2025-01-15-TJRO.parquet |
      | jina-v4 | embeddings-jina-v4-2025-01-15-TJRO.parquet |
      | openai | embeddings-openai-2025-01-15-TJRO.parquet |
    When I hydrate vector stores for each model:
      ```bash
      causaganha vector-store hydrate --model jina-v3 --collection jina_v3
      causaganha vector-store hydrate --model jina-v4 --collection jina_v4
      causaganha vector-store hydrate --model openai --collection openai
      ```
    Then I should have 3 separate collections
    And I can A/B test which model gives better search results
    And compare: "jina-v4 has 15% better recall than jina-v3"

  @hydration @vector-store @cost-comparison
  Scenario: Compare cost of hydration vs local generation
    Given I need embeddings for 100000 decisions
    When I calculate local generation cost:
      | item | cost |
      | Jina API calls | 100000 × $0.00008 = $8 |
      | Time | 2 hours |
    And I calculate hydration cost:
      | item | cost |
      | Download bandwidth | 400 MB @ free (IA) |
      | Time | 10 minutes |
    Then hydration is:
      | metric | savings |
      | Cost | $8 saved |
      | Time | 12x faster |
      | API calls | 0 (no quota used) |
    And hydration is the better approach! ✅

  @hydration @vector-store @cache-strategy
  Scenario: Cache embeddings locally after hydration
    Given I hydrate embeddings from IA
    When I configure local caching:
      ```yaml
      cache:
        enabled: true
        path: ~/.causaganha/embeddings_cache
        ttl: 7 days  # Keep for 1 week
      ```
    Then the system should:
      | step | action |
      | 1 | Download embeddings from IA |
      | 2 | Store in local cache |
      | 3 | Use cached embeddings for subsequent hydrations |
      | 4 | Re-download if cache expired (> 7 days) |
    And I avoid re-downloading the same embeddings repeatedly

  @hydration @vector-store @failure-recovery
  Scenario: Recover from interrupted hydration
    Given I start hydrating 100000 embeddings
    And the process fails after inserting 60000
    When I restart the hydration
    Then the system should:
      | step | action |
      | 1 | Check which intimation_ids are already in vector store |
      | 2 | Skip already-inserted embeddings |
      | 3 | Resume from embedding 60001 |
      | 4 | Complete the remaining 40000 |
      | 5 | Log: "Resumed from 60000, inserted 40000 more" |
    And avoid re-inserting duplicates
    And complete successfully

  @hydration @vector-store @monitoring
  Scenario: Monitor hydration progress and performance
    Given I hydrate a large dataset (1M embeddings)
    When hydration runs
    Then the system should report:
      | metric | example |
      | Progress | "Inserted 250000/1000000 (25%)" |
      | Speed | "10000 embeddings/second" |
      | ETA | "ETA: 75 seconds" |
      | Memory | "Memory usage: 2.5 GB" |
      | Errors | "Errors: 12 invalid vectors skipped" |
    And I can track hydration in real-time
    And identify bottlenecks (download vs insert)

  @hydration @vector-store @multi-source
  Scenario: Hydrate from multiple sources (IA + local)
    Given I have some embeddings on IA
    And some embeddings only in local parquet files
    When I run: causaganha vector-store hydrate --sources ia,local
    Then the system should:
      | step | action |
      | 1 | Scan IA for available embeddings |
      | 2 | Scan local paths for additional embeddings |
      | 3 | Deduplicate by intimation_id |
      | 4 | Hydrate from both sources |
      | 5 | Prioritize IA (canonical) over local |
    And I can combine embeddings from multiple sources

  @hydration @vector-store @backfill
  Scenario: Backfill historical embeddings
    Given I have decisions parquet for 2024 (historical)
    And I did NOT generate embeddings at that time
    When I run: causaganha vector-store backfill --year 2024
    Then the system should:
      | step | action |
      | 1 | Check if historical embeddings exist on IA |
      | 2 | If yes: Download and hydrate |
      | 3 | If no: Generate embeddings from decisions texto |
      | 4 | Upload new embeddings to IA |
      | 5 | Hydrate vector store |
    And historical data becomes searchable
    And future backfills can reuse uploaded embeddings

  @hydration @vector-store @distributed
  Scenario: Distributed hydration across multiple workers
    Given I have 27 tribunals × 365 days = 9855 embeddings files
    And I want to hydrate all of them
    When I run with multiple workers:
      ```bash
      causaganha vector-store hydrate --workers 10 --year 2025
      ```
    Then the system should:
      | step | action |
      | 1 | Distribute files across 10 workers |
      | 2 | Each worker downloads and inserts independently |
      | 3 | Workers coordinate to avoid duplicates |
      | 4 | Aggregate progress: "Worker 3: 150000/394200 (38%)" |
      | 5 | Complete 10x faster than single worker |
    And all embeddings should be loaded correctly
