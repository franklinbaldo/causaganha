Feature: Incremental Reprocessing from Internet Archive
  As a data engineer
  I want to reprocess historical decisions with improved logic
  So that I can fix analysis errors without re-collecting from PJe API

  Background:
    Given historical parquet files are stored on Internet Archive
    And the system can filter decisions by quality metrics
    And reprocessing creates new versioned parquet files

  @reprocessing @incremental @quality-fix
  Scenario: Fix low-confidence analyses from January 2025
    Given I have decisions from January 2025 with average confidence 0.65
    And I improved the judge extraction logic
    When I run incremental reprocessing:
      ```bash
      causaganha reprocess \
        --filter "confidence_breakdown.judge_extraction < 0.50" \
        --date-range 2025-01-01:2025-01-31 \
        --strategy llm \
        --output-suffix "-v2"
      ```
    Then the system should:
      | step | action |
      | 1 | Download decisions parquet files for January |
      | 2 | Filter decisions with judge_extraction < 0.50 |
      | 3 | Reanalyze only filtered decisions with LLM |
      | 4 | Merge reanalyzed decisions with untouched ones |
      | 5 | Export new parquet files with "-v2" suffix |
      | 6 | Upload to IA: decisions-2025-01-15-TJRO-v2.parquet |
    And only 30% of decisions should be reanalyzed (not all)
    And new files should have improved average confidence > 0.80

  @reprocessing @incremental @cost-optimization
  Scenario: Reprocess only specific outcomes with errors
    Given I discovered that "parcialmente procedente" outcomes have 20% error rate
    And I have 10000 decisions from Q1 2025
    When I reprocess with filter:
      ```python
      filter = "outcome = 'parcialmente procedente' AND confidence_breakdown.outcome_classification < 0.70"
      ```
    Then only 2000 decisions should be reanalyzed (20% of 10K)
    And the cost should be $840 (2000 × $0.42 LLM) instead of $4200 for all
    And I save $3360 (80%) by being selective

  @reprocessing @incremental @version-tracking
  Scenario: Track multiple reprocessing versions
    Given I have original decisions: decisions-2025-01-15-TJRO.parquet
    When I reprocess with improved logic in February
    Then I should have: decisions-2025-01-15-TJRO-v2.parquet
    When I reprocess again with better model in March
    Then I should have: decisions-2025-01-15-TJRO-v3.parquet
    And all versions should coexist on Internet Archive
    And I can compare: SELECT * FROM v1 vs v2 vs v3

  @reprocessing @incremental @selective-fields
  Scenario: Reprocess only specific analysis fields
    Given I only need to fix judge_name extraction
    And other fields (outcome, winner, loser) are correct
    When I reprocess with --fields judge_name
    Then the system should:
      | action |
      | Keep existing outcome, winner_lawyer, loser_lawyer |
      | Extract only judge_name using improved logic |
      | Update confidence_breakdown.judge_extraction |
      | Preserve all other analysis results |
    And this should be faster than full reanalysis
    And cheaper (only $0.05 per decision instead of $0.42)

  @reprocessing @incremental @cross-tribunal
  Scenario: Reprocess multiple tribunals in parallel
    Given I need to fix analyses for 5 tribunals in January
    When I run parallel reprocessing:
      ```bash
      causaganha reprocess \
        --tribunals TJRO,TJSP,TJRJ,TJMG,TJAC \
        --date-range 2025-01-01:2025-01-31 \
        --filter "confidence_breakdown.overall < 0.70" \
        --parallel 5
      ```
    Then 5 workers should run concurrently
    And each worker should process one tribunal independently
    And total time should be 1/5 of sequential processing
    And all versioned parquet files should be uploaded to IA

  @reprocessing @incremental @dry-run
  Scenario: Preview reprocessing scope before execution
    Given I want to estimate cost before reprocessing
    When I run with --dry-run flag:
      ```bash
      causaganha reprocess \
        --filter "confidence_breakdown.winner_identification < 0.80" \
        --date-range 2025-01-01:2025-03-31 \
        --strategy llm \
        --dry-run
      ```
    Then the system should output:
      | metric | value |
      | Total decisions in range | 150000 |
      | Decisions matching filter | 35000 (23%) |
      | Estimated cost (LLM) | $14700 (35K × $0.42) |
      | Estimated duration | 12.5 hours |
      | Output files | 90 parquet files (31 days × 3 tribunals) |
    And no actual reprocessing should occur
    And I can decide: "Worth it? Yes/No"

  @reprocessing @incremental @duckdb-integration
  Scenario: Reprocess decisions identified via DuckDB query
    Given I run complex DuckDB query to find problematic decisions:
      ```sql
      SELECT intimation_id
      FROM 's3://ia/causaganha-decisions-2025-*.parquet' d
      JOIN 's3://ia/causaganha-lawyers-2025-*.parquet' w
        ON d.winner_lawyer_oab = w.oab_number
      WHERE w.global_rating < d.confidence_breakdown.winner_identification * 1000
        AND d.confidence_breakdown.overall < 0.75
      ```
    When I pass the result intimation_ids to reprocessing
    Then only those specific decisions should be reanalyzed
    And the system should handle cross-date, cross-tribunal IDs
    And all reprocessed decisions should be merged back correctly

  @reprocessing @incremental @quality-validation
  Scenario: Validate quality improvement after reprocessing
    Given I reprocessed January 2025 with improved logic
    When I compare v1 vs v2 quality metrics
    Then I should see report:
      | metric | v1 | v2 | improvement |
      | Average overall confidence | 0.68 | 0.82 | +21% |
      | Judge extraction confidence | 0.42 | 0.78 | +86% |
      | Decisions with conf > 0.80 | 35% | 72% | +106% |
      | Missing judge_name | 45% | 8% | -82% |
    And I can decide: "Keep v2, deprecate v1"

  @reprocessing @incremental @rollback
  Scenario: Rollback to previous version if reprocessing failed
    Given I reprocessed January with v2 but it introduced bugs
    And original v1 files are still on Internet Archive
    When I run: causaganha reprocess rollback --version v1
    Then the system should:
      | action |
      | Mark v2 files as deprecated in metadata |
      | Update analysis pipeline to use v1 files |
      | Keep v2 files for audit (not delete) |
      | Log rollback reason and timestamp |
    And all queries should use v1 files again
    And no data should be lost

  @reprocessing @incremental @metadata-tracking
  Scenario: Track reprocessing metadata in parquet files
    Given I reprocess decisions with improved logic
    When I inspect v2 parquet file metadata
    Then it should include:
      | metadata_key | value |
      | original_version | v1 |
      | reprocessing_date | 2025-02-15T14:30:00Z |
      | reprocessing_reason | "Improved judge extraction" |
      | decisions_reanalyzed | 3521 |
      | decisions_unchanged | 6479 |
      | filter_criteria | "judge_extraction < 0.50" |
      | software_version | causaganha-2.2.0 |
      | total_cost_usd | 1478.82 |
    And I can audit: "Why was this file reprocessed?"

  @reprocessing @incremental @cost-tracking
  Scenario: Track and alert on reprocessing costs
    Given I have monthly budget of $1000 for reprocessing
    When I run reprocessing that would cost $1500
    Then the system should:
      | action |
      | Calculate total cost before starting |
      | Alert: "Cost $1500 exceeds budget $1000" |
      | Ask for confirmation: "Proceed? Y/N" |
      | Track actual cost during execution |
      | Stop if cost exceeds budget + 10% tolerance |
    And I should never accidentally overspend

  @reprocessing @incremental @hybrid-reprocessing
  Scenario: Hybrid reprocessing - RAG for high conf, LLM for low conf
    Given I want to reprocess efficiently
    When I run hybrid reprocessing:
      ```bash
      causaganha reprocess \
        --strategy hybrid \
        --rag-threshold 0.75 \
        --date-range 2025-01-01:2025-01-31
      ```
    Then decisions with original conf > 0.75 should use RAG ($0.000008)
    And decisions with original conf < 0.75 should use LLM ($0.42)
    And total cost should be optimized vs LLM-only
    And quality should be maintained (RAG for easy cases, LLM for hard)

  @reprocessing @incremental @batch-reprocessing
  Scenario: Batch reprocessing with automatic resume
    Given I'm reprocessing 6 months of data (180 days)
    And the process crashes after 45 days
    When I rerun the same reprocessing command
    Then the system should:
      | action |
      | Detect 45 days already completed (files on IA) |
      | Skip completed days |
      | Resume from day 46 |
      | Complete remaining 135 days |
    And no duplicate work should be done
    And no duplicate costs should be incurred
