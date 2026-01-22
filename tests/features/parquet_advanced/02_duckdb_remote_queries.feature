Feature: DuckDB Remote Queries on Internet Archive
  As a data analyst
  I want to query parquet files directly on Internet Archive
  So that I can analyze massive datasets without downloading anything

  Background:
    Given parquet files are publicly accessible on Internet Archive
    And DuckDB supports reading from HTTP/S3 URLs
    And queries use partition pruning for performance

  @duckdb @remote @cross-date
  Scenario: Query one month of decisions across all tribunals
    Given I have decisions parquet files for January 2025 (27 tribunals × 31 days = 837 files)
    When I run DuckDB query without downloading:
      ```sql
      SELECT
        sigla_tribunal,
        COUNT(*) AS total_decisions,
        AVG(confidence_breakdown.overall) AS avg_confidence,
        SUM(CASE WHEN outcome = 'procedente' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS procedente_rate
      FROM 'https://archive.org/download/causaganha-decisions-2025-01-*/causaganha-decisions-*.parquet'
      WHERE data_disponibilizacao BETWEEN '2025-01-01' AND '2025-01-31'
      GROUP BY sigla_tribunal
      ORDER BY total_decisions DESC
      ```
    Then DuckDB should stream data from Internet Archive
    And the query should complete in less than 60 seconds
    And I should get aggregated results for all 27 tribunals
    And no local storage should be used (except DuckDB cache)
    And total data scanned should be ~2-3 GB (compressed parquet)

  @duckdb @remote @partition-pruning
  Scenario: Query specific tribunal with partition pruning
    Given parquet files are partitioned by date and tribunal
    And I only need TJRO decisions from January 15-20, 2025
    When I run:
      ```sql
      SELECT numero_processo, outcome, confidence_breakdown
      FROM 'https://archive.org/download/causaganha-decisions-*/causaganha-decisions-*.parquet'
      WHERE sigla_tribunal = 'TJRO'
        AND data_disponibilizacao BETWEEN '2025-01-15' AND '2025-01-20'
      ```
    Then DuckDB should only read files matching: *-2025-01-1[5-9]-TJRO.parquet, *-2025-01-20-TJRO.parquet
    And should skip 831 other parquet files (partition pruning)
    And query should be 10-50x faster than full scan
    And data transferred should be ~300 MB instead of 3 GB

  @duckdb @remote @join-multiple-parquets
  Scenario: Join decisions with lawyers and embeddings remotely
    Given I have decisions, lawyers, and embeddings on Internet Archive
    When I run complex join query:
      ```sql
      SELECT
        d.numero_processo,
        d.outcome,
        w.lawyer_name AS winner_name,
        w.global_rating AS winner_rating,
        l.lawyer_name AS loser_name,
        l.global_rating AS loser_rating,
        e.embedding_model
      FROM 'https://archive.org/download/causaganha-decisions-2025-01-15-TJRO/decisions-*.parquet' d
      LEFT JOIN 'https://archive.org/download/causaganha-lawyers-2025-01-15/lawyers-*.parquet' w
        ON d.winner_lawyer_oab = w.oab_number AND d.winner_lawyer_state = w.oab_state
      LEFT JOIN 'https://archive.org/download/causaganha-lawyers-2025-01-15/lawyers-*.parquet' l
        ON d.loser_lawyer_oab = l.oab_number AND d.loser_lawyer_state = l.oab_state
      LEFT JOIN 'https://archive.org/download/causaganha-embeddings-2025-01-15-TJRO/embeddings-*.parquet' e
        ON d.intimation_id = e.intimation_id
      WHERE w.global_rating < l.global_rating - 100
      LIMIT 100
      ```
    Then DuckDB should join 4 different parquet types remotely
    And find all upset victories (lower-rated lawyer won)
    And include full lawyer context without local database
    And query should complete in less than 10 seconds

  @duckdb @remote @time-series-analysis
  Scenario: Analyze confidence trends over 3 months
    Given I have decisions from January to March 2025
    When I run time-series query:
      ```sql
      SELECT
        DATE_TRUNC('week', data_disponibilizacao) AS week,
        sigla_tribunal,
        AVG(confidence_breakdown.overall) AS avg_confidence,
        AVG(confidence_breakdown.judge_extraction) AS avg_judge_conf,
        COUNT(*) AS decisions_count
      FROM 'https://archive.org/download/causaganha-decisions-2025-*/causaganha-decisions-*.parquet'
      WHERE data_disponibilizacao BETWEEN '2025-01-01' AND '2025-03-31'
      GROUP BY week, sigla_tribunal
      ORDER BY week, sigla_tribunal
      ```
    Then I should see weekly confidence trends for all tribunals
    And identify weeks with quality drops
    And total query time should be less than 90 seconds
    And I can visualize: "Did new model improve confidence?"

  @duckdb @remote @window-functions
  Scenario: Find top lawyers by rating change using window functions
    Given I have daily lawyer snapshots for January 2025
    When I run window function query:
      ```sql
      WITH lawyer_ratings AS (
        SELECT
          oab_number,
          oab_state,
          DATE(file_date) AS date,
          global_rating,
          LAG(global_rating) OVER (PARTITION BY oab_number, oab_state ORDER BY date) AS prev_rating
        FROM 'https://archive.org/download/causaganha-lawyers-2025-01-*/lawyers-*.parquet'
      )
      SELECT
        oab_number,
        oab_state,
        MAX(global_rating) - MIN(global_rating) AS total_change,
        COUNT(DISTINCT date) AS days_tracked
      FROM lawyer_ratings
      WHERE prev_rating IS NOT NULL
      GROUP BY oab_number, oab_state
      HAVING total_change > 50
      ORDER BY total_change DESC
      LIMIT 100
      ```
    Then I should find top 100 lawyers with biggest rating jumps
    And query should work across 31 lawyer snapshot files
    And no local database needed

  @duckdb @remote @aggregations
  Scenario: Calculate tribunal performance metrics
    Given I need quarterly report for Q1 2025
    When I run aggregation query:
      ```sql
      SELECT
        sigla_tribunal,
        COUNT(*) AS total_decisions,
        SUM(CASE WHEN outcome = 'procedente' THEN 1 ELSE 0 END) AS procedente_count,
        SUM(CASE WHEN outcome = 'improcedente' THEN 1 ELSE 0 END) AS improcedente_count,
        SUM(CASE WHEN outcome = 'parcialmente procedente' THEN 1 ELSE 0 END) AS parcial_count,
        AVG(confidence_breakdown.overall) AS avg_confidence,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY confidence_breakdown.overall) AS median_confidence,
        COUNT(DISTINCT winner_lawyer_oab) AS unique_lawyers
      FROM 'https://archive.org/download/causaganha-decisions-2025-0[1-3]-*/causaganha-decisions-*.parquet'
      GROUP BY sigla_tribunal
      ORDER BY total_decisions DESC
      ```
    Then I should get comprehensive tribunal statistics
    And query should scan ~9 GB of data (3 months)
    And complete in less than 2 minutes
    And all calculations done server-side (DuckDB streaming)

  @duckdb @remote @filtering
  Scenario: Complex filtering without downloading data
    Given I need to find specific decision patterns
    When I run filtered query:
      ```sql
      SELECT
        numero_processo,
        data_disponibilizacao,
        sigla_tribunal,
        outcome,
        confidence_breakdown.overall AS confidence
      FROM 'https://archive.org/download/causaganha-decisions-*/causaganha-decisions-*.parquet'
      WHERE confidence_breakdown.overall > 0.90
        AND confidence_breakdown.judge_extraction < 0.60
        AND outcome IN ('procedente', 'parcialmente procedente')
        AND sigla_tribunal IN ('TJRO', 'TJSP', 'TJRJ')
      ORDER BY confidence_breakdown.overall DESC
      LIMIT 1000
      ```
    Then DuckDB should push filters down to parquet level
    And only read relevant row groups (columnar format)
    And skip tribunals not in filter (partition pruning)
    And return top 1000 matching decisions
    And use minimal bandwidth (filter at source)

  @duckdb @remote @schema-evolution
  Scenario: Query across schema versions (v1 and v2)
    Given I have v1 parquet files (January) and v2 files (February+)
    And v2 has additional columns (texto_sections, confidence_breakdown)
    When I run query spanning both versions:
      ```sql
      SELECT
        numero_processo,
        outcome,
        confidence_score,  -- v1 field
        confidence_breakdown.overall AS confidence_v2  -- v2 field (null in v1)
      FROM 'https://archive.org/download/causaganha-decisions-*/causaganha-decisions-*.parquet'
      WHERE data_disponibilizacao BETWEEN '2025-01-15' AND '2025-02-15'
      ```
    Then DuckDB should handle schema differences gracefully
    And v1 files should have null for confidence_breakdown
    And v2 files should populate both fields
    And query should succeed across schema versions

  @duckdb @remote @export-results
  Scenario: Export query results to local parquet
    Given I run complex analysis query on remote parquet
    When I want to save results locally:
      ```sql
      COPY (
        SELECT d.*, w.lawyer_name, w.global_rating
        FROM 'https://archive.org/download/causaganha-decisions-2025-01-*/decisions-*.parquet' d
        JOIN 'https://archive.org/download/causaganha-lawyers-2025-01-*/lawyers-*.parquet' w
          ON d.winner_lawyer_oab = w.oab_number
        WHERE w.global_rating > 1500
      ) TO 'high_rated_lawyers_decisions.parquet' (FORMAT PARQUET)
      ```
    Then DuckDB should stream results directly to local file
    And only download result set (not all source data)
    And local parquet should be ready for further analysis

  @duckdb @remote @materialized-views
  Scenario: Create materialized view from remote parquet
    Given I frequently query the same aggregation
    When I create materialized view:
      ```sql
      CREATE TABLE tribunal_daily_stats AS
      SELECT
        sigla_tribunal,
        data_disponibilizacao,
        COUNT(*) AS decisions,
        AVG(confidence_breakdown.overall) AS avg_conf
      FROM 'https://archive.org/download/causaganha-decisions-2025-*/decisions-*.parquet'
      GROUP BY sigla_tribunal, data_disponibilizacao
      ```
    Then DuckDB should download and cache aggregated data
    And subsequent queries should use cached table
    And cache should be much smaller than original parquet files
    And I can refresh: REPLACE TABLE tribunal_daily_stats AS ...

  @duckdb @remote @cost-analysis
  Scenario: Analyze costs by comparing query approaches
    Given I need to analyze 100 GB of decisions (1 year)
    When I compare approaches:
      | approach | data_transfer | storage_needed | query_time |
      | Download all parquet files | 100 GB | 100 GB | Fast (local) |
      | DuckDB remote queries | ~1-5 GB | 0 GB | Medium (streaming) |
      | Load into local DuckDB | 100 GB | 50 GB | Fast (local) |
    Then remote queries should win on:
      | metric |
      | Zero local storage |
      | Minimal bandwidth (only results) |
      | No ETL pipeline needed |
      | Always up-to-date (reads from IA) |
    And local approach should win on:
      | metric |
      | Faster repeated queries |
      | No internet dependency |

  @duckdb @remote @performance-tuning
  Scenario: Optimize remote query performance
    Given I have slow remote query
    When I apply optimizations:
      | optimization | technique |
      | Partition pruning | Add WHERE clause on partition columns (date, tribunal) |
      | Column pruning | SELECT only needed columns, not * |
      | Filter pushdown | WHERE clauses pushed to parquet reader |
      | Parallel reads | DuckDB reads multiple files concurrently |
      | HTTP caching | Browser-like HTTP cache for repeated reads |
    Then query performance should improve 10-100x
    And bandwidth usage should drop 50-90%

  @duckdb @remote @monitoring
  Scenario: Monitor remote query performance
    Given I run remote DuckDB queries
    When I enable query profiling:
      ```sql
      PRAGMA enable_profiling;
      PRAGMA profiling_output = 'query_profile.json';

      SELECT ... FROM 'https://archive.org/download/...'
      ```
    Then I should see metrics:
      | metric | example_value |
      | Files scanned | 45 / 837 (partition pruning!) |
      | Data transferred | 1.2 GB |
      | Rows scanned | 150000 |
      | Rows returned | 5000 |
      | Query time | 12.3 seconds |
      | Time in HTTP reads | 8.1 seconds (66%) |
      | Time in processing | 4.2 seconds (34%) |
    And I can optimize based on bottlenecks
