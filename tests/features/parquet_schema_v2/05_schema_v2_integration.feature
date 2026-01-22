Feature: Schema v2 Integration and Migration
  As a platform maintainer
  I want smooth migration from schema v1 to v2
  So that we can deploy improvements without breaking existing workflows

  Background:
    Given the system supports both schema v1 and v2
    And schema version is stored in parquet metadata

  @integration @schema-version @export
  Scenario: Export with explicit schema version
    Given I have 1000 analyzed decisions
    When I export with --schema-version v2
    Then the parquet file should have schema version "v2" in metadata
    And the file should include embeddings, sections, enrichment, and confidence breakdown
    And the file should be valid according to schema v2 specification

  @integration @schema-version @auto-detect
  Scenario: Automatically detect schema version when reading parquet
    Given I have parquet files with different schema versions
    When I read a schema v1 file
    Then the system should detect version "v1" from metadata
    And the system should handle missing v2 fields gracefully
    When I read a schema v2 file
    Then the system should detect version "v2" from metadata
    And the system should use all v2 enhanced features

  @integration @migration @parallel-deployment
  Scenario: Run v1 and v2 exports in parallel for validation
    Given I configure the system to export both v1 and v2
    When I export decisions for date "2025-01-20"
    Then two parquet files should be created:
      | filename                            | schema  |
      | causaganha-2025-01-20-TJRO-v1.parquet | v1    |
      | causaganha-2025-01-20-TJRO-v2.parquet | v2    |
    And both files should be uploaded to Internet Archive
    And I can compare analysis results between versions

  @integration @migration @re-export
  Scenario: Re-export historical data from v1 to v2
    Given I have historical parquet files in schema v1 for date range "2025-01-01" to "2025-01-31"
    When I run: causaganha parquet re-export --start-date 2025-01-01 --end-date 2025-01-31 --schema v2
    Then the system should download each v1 file
    And generate embeddings for all decisions
    And extract sections from texto
    And enrich with current lawyer ratings (historical snapshot)
    And export as schema v2 with new filename suffix "-v2"
    And upload all v2 files to Internet Archive

  @integration @migration @batch-migration
  Scenario: Re-export large date ranges efficiently
    Given I have 365 days of v1 parquet files to migrate
    When I run batch migration with --parallel 4
    Then the system should process 4 dates concurrently
    And the migration should complete in approximately 1/4 the sequential time
    And a progress report should show: processed, succeeded, failed

  @integration @backward-compatibility @analysis
  Scenario: Analyze mixed v1 and v2 parquet files in same workflow
    Given I have parquet files with mixed schemas:
      | date       | tribunal | schema |
      | 2025-01-10 | TJRO     | v1     |
      | 2025-01-15 | TJRO     | v2     |
      | 2025-01-20 | TJRO     | v2     |
    When I analyze all files using RAG
    Then v1 files should generate embeddings on-the-fly
    And v2 files should use cached embeddings
    And all analyses should complete successfully
    And v2 analyses should be faster than v1

  @integration @file-size @comparison
  Scenario: Compare file sizes between v1 and v2
    Given I export the same 10000 decisions in both v1 and v2
    When I measure file sizes
    Then v2 file should be approximately 2x the size of v1
    And the breakdown should be:
      | component         | size_increase |
      | Base data         | 0%            |
      | Embeddings        | +100%         |
      | Sections          | +5%           |
      | Lawyer enrichment | +3%           |
      | Confidence breakdown | +0.5%      |
    And the size increase should be acceptable for Internet Archive

  @integration @cost-benefit @roi
  Scenario: Calculate ROI for schema v2 deployment
    Given I have cost data for 1 million decisions per year
    When I calculate annual costs and savings for v2
    Then embedding generation cost should be $100/year
    And section extraction cost should be $100/year (hybrid mode)
    And avoided re-embedding savings should be $8000/year
    And reduced LLM processing savings should be $1200/year
    And developer time savings should be $5000/year
    And total net benefit should be approximately $14000/year

  @integration @duckdb @query-performance
  Scenario: Query performance with DuckDB on v2 parquet
    Given I have v2 parquet files with enriched data
    When I query with DuckDB: SELECT winner_lawyer.name WHERE winner_lawyer.rating > 1500
    Then the query should use parquet column pruning
    And the query should complete in less than 2 seconds
    And no external joins should be needed

  @integration @ia-bandwidth @optimization
  Scenario: Optimize Internet Archive bandwidth with v2 files
    Given v2 files are 2x larger than v1
    And Internet Archive has unlimited storage but limited bandwidth
    When I download a v2 file from IA
    Then I should use cached embeddings (no re-download needed)
    And the one-time download cost is offset by analysis speed
    And total bandwidth over 100 analyses is lower than v1 (no repeated downloads)

  @integration @versioning @metadata
  Scenario: Store comprehensive version metadata in parquet
    Given I export a schema v2 file
    When I read the parquet metadata
    Then I should see:
      | metadata_key            | example_value                |
      | schema_version          | v2                           |
      | export_date             | 2025-01-20T10:30:00Z        |
      | embedding_model         | jina-embeddings-v3           |
      | embedding_dimension     | 1024                         |
      | section_extraction_method | hybrid                      |
      | software_version        | causaganha-2.0.3             |
    And I can track which software version created the file

  @integration @migration @rollback
  Scenario: Rollback to v1 if v2 deployment fails
    Given I deployed v2 exports but encountered critical issues
    When I rollback to v1 export configuration
    Then the system should immediately resume v1 exports
    And existing v2 files should remain accessible on IA
    And analysis should continue working with v1 files
    And no data should be lost

  @integration @analytics @reporting
  Scenario: Generate schema v2 deployment report
    Given I have been running v2 exports for 30 days
    When I generate a deployment report
    Then the report should include:
      | metric                           | value   |
      | Total v2 files exported          | 930     |
      | Average file size increase       | +107%   |
      | RAG analysis speed improvement   | 4.2x    |
      | LLM analysis cost reduction      | -35%    |
      | Total storage used               | 12.5 GB |
      | Embedding API cost (30 days)     | $8.33   |
      | Net cost savings (30 days)       | $1150   |

  @integration @feature-flags @gradual-rollout
  Scenario: Gradual rollout of v2 features using feature flags
    Given I configure v2 rollout as gradual
    When I set feature flags:
      | feature               | enabled_percentage |
      | embeddings            | 100%               |
      | sections              | 50%                |
      | lawyer_enrichment     | 25%                |
      | confidence_breakdown  | 100%               |
    Then 100% of exports should include embeddings and confidence breakdown
    And 50% should include structured sections
    And 25% should include lawyer enrichment
    And I can monitor impact before full rollout
