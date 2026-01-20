Feature: Multi-Court Tribunal Coverage
  As a national legal analyst
  I want to analyze decisions from all 90+ Brazilian tribunals
  So that I can provide comprehensive nationwide lawyer ratings

  Background:
    Given the CausaGanha database is initialized
    And the PJe API supports multiple tribunals

  # ============================================================================
  # TRIBUNAL CONFIGURATION
  # ============================================================================

  Scenario: Configure monitored tribunals in database
    Given the monitored_courts table is empty
    When I add tribunals "TJRO", "TJAC", "TJAP", "TJAM", "TJRR"
    Then the monitored_courts table should contain 5 entries
    And each tribunal should have a unique code
    And each tribunal should have configuration settings

  Scenario: Each tribunal has specific configuration
    Given tribunal "TJSP" is configured with:
      | Setting           | Value |
      | lookback_days     | 14    |
      | batch_size        | 100   |
      | enabled           | true  |
    And tribunal "TJRO" is configured with:
      | Setting           | Value |
      | lookback_days     | 7     |
      | batch_size        | 50    |
      | enabled           | true  |
    When I query tribunal configurations
    Then "TJSP" should have lookback_days = 14
    And "TJRO" should have lookback_days = 7

  Scenario: Disable specific tribunals temporarily
    Given tribunal "TJMG" is configured and enabled
    When I disable tribunal "TJMG"
    Then the tribunal should be marked as disabled
    And collection should skip "TJMG"
    And the configuration should persist

  # ============================================================================
  # COLLECTING FROM MULTIPLE TRIBUNALS
  # ============================================================================

  Scenario: Collect from all enabled tribunals
    Given tribunals "TJRO", "TJAC", "TJAP" are enabled
    And each tribunal has available decisions
    When I run the collect command without specifying tribunals
    Then intimations should be collected from all 3 tribunals
    And each intimation should be tagged with its tribunal code

  Scenario: Collect from specific subset of tribunals
    Given tribunals "TJRO", "TJAC", "TJAP", "TJAM" are enabled
    When I run the collect command for tribunals "TJRO,TJAC"
    Then intimations should only be collected from "TJRO" and "TJAC"
    And "TJAP" and "TJAM" should be skipped

  Scenario: Process tribunals in parallel for speed
    Given tribunals "TJRO", "TJAC", "TJAP", "TJAM", "TJRR" are enabled
    When I run the collect command with parallel processing
    Then all 5 tribunals should be queried concurrently
    And the total time should be close to the slowest single tribunal
    And all intimations should be collected successfully

  # ============================================================================
  # TRIBUNAL-SPECIFIC DATA ISOLATION
  # ============================================================================

  Scenario: Intimations are tagged with tribunal code
    Given intimations are collected from "TJRO" and "TJAC"
    When I query intimations from "TJRO"
    Then all results should have sigla_tribunal = "TJRO"
    And no "TJAC" intimations should be returned

  Scenario: Lawyer ratings are calculated per tribunal
    Given lawyer "123456/SP" has matches in:
      | Tribunal | Wins | Losses |
      | TJSP     | 15   | 5      |
      | TJRO     | 3    | 2      |
      | TJMG     | 8    | 1      |
    When I query the lawyer's rating for "TJSP"
    Then the rating should reflect only "TJSP" matches (15 wins, 5 losses)
    And "TJRO" and "TJMG" matches should not affect "TJSP" rating

  Scenario: Global ratings aggregate across all tribunals
    Given lawyer "234567/RJ" has ratings in tribunals:
      | Tribunal | Rating | Matches |
      | TJRJ     | 32.5   | 50      |
      | TJSP     | 28.0   | 20      |
      | TJMG     | 30.2   | 15      |
    When I query the global rating for lawyer "234567/RJ"
    Then the global rating should combine all 85 matches
    And the global rating should reflect overall performance

  # ============================================================================
  # HANDLING TRIBUNAL DIFFERENCES
  # ============================================================================

  Scenario: Adapt to tribunal-specific PJe API variations
    Given tribunal "TJSP" has API endpoint "https://pje.tjsp.jus.br/api/v1"
    And tribunal "TJRO" has API endpoint "https://pje.tjro.jus.br/api/v1"
    When I run the collect command for both tribunals
    Then each tribunal should be queried at its specific endpoint
    And API responses should be parsed correctly for each tribunal

  Scenario: Handle tribunals with different data volumes
    Given tribunal "TJSP" produces 5000 intimations per day
    And tribunal "TJRO" produces 50 intimations per day
    When I run the collect command for both tribunals
    Then "TJSP" should be processed with large batch sizes
    And "TJRO" should be processed efficiently despite low volume
    And both should complete successfully

  Scenario: Adapt to tribunal-specific date formats
    Given different tribunals may use different date formats
    When intimations are collected from multiple tribunals
    Then all dates should be normalized to ISO 8601 format
    And date parsing should handle tribunal variations

  # ============================================================================
  # REGIONAL COVERAGE
  # ============================================================================

  Scenario: Cover all state tribunals (TJs)
    Given there are 27 state tribunals (TJxx)
    When I configure all state tribunals
    Then the system should support all 27 TJ codes
    And each state should be represented

  Scenario: Support federal tribunals (TRFs)
    Given there are 5 federal regional tribunals (TRF1-TRF5)
    When I configure federal tribunals
    Then the system should support all 5 TRF codes
    And federal cases should be processed correctly

  Scenario: Support labor tribunals (TRTs)
    Given there are 24 labor regional tribunals (TRT1-TRT24)
    When I configure labor tribunals
    Then the system should support all 24 TRT codes
    And labor cases should be processed correctly

  Scenario: Support specialized tribunals
    Given specialized tribunals like "TST", "TSE", "STJ", "STF" exist
    When I configure these tribunals
    Then the system should handle specialized court decisions
    And analysis should adapt to appellate court structure

  # ============================================================================
  # INCREMENTAL TRIBUNAL ADDITION
  # ============================================================================

  Scenario: Add new tribunal to monitoring
    Given the system currently monitors 10 tribunals
    When I add tribunal "TJBA" to the configuration
    Then "TJBA" should be included in future collection runs
    And historical data collection should be triggered for "TJBA"
    And the new tribunal should integrate seamlessly

  Scenario: Backfill historical data for new tribunal
    Given tribunal "TJCE" is newly added
    And the tribunal has 2 years of historical decisions available
    When I run the backfill command for "TJCE"
    Then the system should collect historical intimations
    And the backfill should respect date range limits
    And all historical data should be processed through the pipeline

  # ============================================================================
  # TRIBUNAL HEALTH & MONITORING
  # ============================================================================

  Scenario: Monitor API health per tribunal
    Given 20 tribunals are being monitored
    When I run the health check command
    Then each tribunal's API should be queried
    And response times should be recorded
    And failing tribunals should be flagged

  Scenario: Track collection success rate per tribunal
    Given the system has been running for 30 days
    When I query collection statistics
    Then success rates should be shown per tribunal
    And tribunals with low success rates should be highlighted
    And error patterns should be identified

  Scenario: Alert on tribunal API failures
    Given tribunal "TJPE" API has been failing for 24 hours
    When the monitoring system checks
    Then an alert should be raised
    And the alert should specify the failing tribunal
    And suggested remediation should be provided

  # ============================================================================
  # CROSS-TRIBUNAL ANALYTICS
  # ============================================================================

  Scenario: Compare lawyer performance across tribunals
    Given lawyer "345678/SP" practices in "TJSP", "TJRO", and "TJMG"
    When I query cross-tribunal analytics for the lawyer
    Then performance should be shown for each tribunal
    And the tribunals should be ranked by lawyer's win rate
    And insights should be provided about regional performance

  Scenario: Identify lawyers practicing in multiple states
    Given lawyer "456789/RJ" has cases in 5 different tribunals
    When I query multi-jurisdictional lawyers
    Then lawyer "456789/RJ" should be identified
    And the tribunals should be listed
    And the lawyer should be marked as "multi-jurisdictional"

  Scenario: Aggregate national statistics
    When I query national statistics
    Then total intimations should be summed across all tribunals
    And total analyses should be summed across all tribunals
    And total unique lawyers should be counted globally
    And per-tribunal breakdowns should be available

  # ============================================================================
  # TRIBUNAL-SPECIFIC FAILURE HANDLING
  # ============================================================================

  Scenario: Continue processing when one tribunal fails
    Given tribunals "TJRO", "TJAC", "TJAP", "TJAM" are being collected
    And tribunal "TJAC" API returns 500 errors
    When I run the collect command
    Then "TJRO", "TJAP", and "TJAM" should complete successfully
    And "TJAC" should be logged as failed
    And the pipeline should continue for other tribunals

  Scenario: Retry failed tribunals on next run
    Given tribunal "TJRR" failed on the last collection run
    And the failure was marked in the sync log
    When I run the collect command again
    Then "TJRR" should be retried
    And if successful, the failure should be cleared
    And normal collection should resume for "TJRR"

  Scenario: Disable tribunal after repeated failures
    Given tribunal "TJMS" has failed for 7 consecutive days
    When the monitoring system evaluates tribunal health
    Then "TJMS" should be automatically disabled
    And an alert should be sent to administrators
    And manual intervention should be required to re-enable

  # ============================================================================
  # SCALING TO 90+ TRIBUNALS
  # ============================================================================

  Scenario: Handle high concurrency for 90+ tribunals
    Given all 90+ Brazilian tribunals are configured
    When I run the collect command for all tribunals
    Then the system should process tribunals in batches
    And concurrency should be limited to avoid overwhelming resources
    And all tribunals should eventually be processed
    And total execution time should remain reasonable

  Scenario: Efficient database queries with multi-tribunal data
    Given the intimations table contains 1 million records from 90 tribunals
    When I query intimations for a specific tribunal
    Then the query should use tribunal index
    And the query should complete quickly (< 100ms)
    And only relevant tribunal data should be scanned

  Scenario: Storage efficiency for multi-tribunal data
    Given 90 tribunals are producing daily data
    When the database size is measured after 1 year
    Then storage should be optimized with compression
    And old data should be archived appropriately
    And database performance should remain acceptable

  # ============================================================================
  # TRIBUNAL METADATA
  # ============================================================================

  Scenario: Store tribunal metadata for enrichment
    Given tribunal "TJSP" is configured
    When I query tribunal metadata
    Then the full name should be "Tribunal de Justiça de São Paulo"
    And the state should be "São Paulo"
    And the state code should be "SP"
    And the jurisdiction type should be "State"

  Scenario: Use tribunal metadata in reports
    Given intimations from multiple tribunals
    When I generate a summary report
    Then tribunal full names should be displayed
    And tribunals should be grouped by region
    And metadata should enhance readability

  # ============================================================================
  # TEMPORAL COVERAGE
  # ============================================================================

  Scenario: Different tribunals have different data availability dates
    Given tribunal "TJSP" has data since 2020-01-01
    And tribunal "TJRO" has data since 2022-06-01
    When I query the earliest available date per tribunal
    Then "TJSP" should show 2020-01-01
    And "TJRO" should show 2022-06-01
    And collection should respect these boundaries

  Scenario: Track when each tribunal was added to monitoring
    Given tribunals were added on different dates:
      | Tribunal | Added Date  |
      | TJRO     | 2024-01-01  |
      | TJAC     | 2024-06-15  |
      | TJAP     | 2024-12-01  |
    When I query tribunal coverage history
    Then each tribunal should show its start date
    And data completeness should be calculated from start date

  # ============================================================================
  # TRIBUNAL-SPECIFIC FEATURES
  # ============================================================================

  Scenario: Some tribunals support additional metadata
    Given tribunal "TJSP" provides lawyer experience level
    And tribunal "TJRO" does not provide this field
    When intimations are collected from both
    Then "TJSP" intimations should include experience level if available
    And "TJRO" intimations should have NULL for that field
    And the schema should accommodate optional tribunal-specific fields

  Scenario: Handle tribunal-specific document types
    Given different tribunals may have different decision types
    When analyzing decisions from multiple tribunals
    Then decision type classification should adapt per tribunal
    And tribunal-specific types should be normalized to standard categories
