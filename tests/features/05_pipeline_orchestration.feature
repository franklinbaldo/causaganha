Feature: End-to-End Pipeline Orchestration
  As a CausaGanha operator
  I want to run the complete analysis pipeline seamlessly
  So that data flows from collection through scoring automatically

  Background:
    Given the CausaGanha database is initialized
    And all external services are accessible
    And the pipeline is configured with default settings

  # ============================================================================
  # FULL PIPELINE EXECUTION
  # ============================================================================

  Scenario: Execute complete pipeline from collection to scoring
    Given there are new decisions available in PJe for "TJRO"
    When I run the pipeline command for court "TJRO"
    Then the collect stage should fetch intimations
    And the archive stage should preserve PDFs to Internet Archive
    And the analyze stage should extract decision information with LLM
    And the score stage should update lawyer ratings
    And all stages should complete successfully
    And a summary should show results from each stage

  Scenario: Pipeline processes data through all four stages sequentially
    Given the monitored court "TJAC" has 10 new decisions
    When I run the pipeline command
    Then intimations should be collected first
    And collected intimations should be archived second
    And archived intimations should be analyzed third
    And analyzed decisions should be scored fourth
    And the execution order should be strictly maintained

  Scenario: Pipeline handles fresh database with no existing data
    Given the database has no existing intimations
    And there are 50 decisions available in PJe
    When I run the pipeline command
    Then all 50 decisions should progress through all stages
    And the final lawyer_ratings table should contain calculated ratings
    And the pipeline should complete without errors

  # ============================================================================
  # STAGE SKIPPING & SELECTIVE EXECUTION
  # ============================================================================

  Scenario: Skip collection stage when intimations already exist
    Given the intimations table already contains 100 intimations
    And 50 of them are unarchived
    When I run the pipeline command with --skip-collect flag
    Then the collect stage should be skipped
    And the archive stage should process the 50 unarchived intimations
    And the analyze and score stages should continue normally

  Scenario: Skip archival stage for faster development
    Given there are 20 unanalyzed intimations
    When I run the pipeline command with --skip-archive flag
    Then the collect stage should run
    And the archive stage should be skipped
    And the analyze stage should process unanalyzed intimations
    And the score stage should update ratings

  Scenario: Skip analysis stage when analyses already exist
    Given there are 30 unrated analyses in the database
    When I run the pipeline command with --skip-analyze flag
    Then only the score stage should run
    And the 30 analyses should be scored
    And no new LLM calls should be made

  Scenario: Skip multiple stages in one command
    Given the database has unrated analyses ready for scoring
    When I run the pipeline command with --skip-collect --skip-archive --skip-analyze flags
    Then only the score stage should execute
    And all other stages should be bypassed
    And the scoring should complete successfully

  # ============================================================================
  # MULTI-COURT PIPELINE
  # ============================================================================

  Scenario: Process multiple courts in a single pipeline run
    Given courts "TJRO", "TJAC", "TJAP" are configured
    And each court has available decisions
    When I run the pipeline command for courts "TJRO,TJAC,TJAP"
    Then intimations should be collected from all 3 courts
    And all intimations should be archived, analyzed, and scored
    And results should be reported per court

  Scenario: Pipeline continues after failure in one court
    Given courts "TJRO", "TJAC", "TJAP" are configured
    And the PJe API for "TJAC" is unavailable
    When I run the pipeline command for all courts
    Then "TJRO" and "TJAP" should be processed successfully
    And "TJAC" should be logged as failed
    And the pipeline should complete with warnings

  # ============================================================================
  # INCREMENTAL PROCESSING
  # ============================================================================

  Scenario: Pipeline processes only new data incrementally
    Given the database contains:
      | Intimations | Archived | Analyzed | Rated |
      | 100         | 80       | 50       | 50    |
    And there are 20 new intimations from PJe
    When I run the pipeline command
    Then 20 new intimations should be collected (total 120)
    And 40 intimations should be archived (20 new + 20 old unarchived)
    And 70 intimations should be analyzed (50 new unanalyzed)
    And 70 analyses should be scored (20 new unrated)
    And the pipeline should process efficiently

  Scenario: Pipeline handles partial stage completion
    Given the last pipeline run completed collection and archival
    And analysis and scoring were not yet performed
    When I run the pipeline command
    Then collection should find and add only new intimations
    And archival should process remaining unarchived items
    And analysis should process all unanalyzed items
    And scoring should process all unrated analyses

  # ============================================================================
  # LIMITS & BATCH CONTROL
  # ============================================================================

  Scenario: Apply global limit across all stages
    Given there are 200 new decisions available
    When I run the pipeline command with limit 50
    Then the collect stage should fetch 50 intimations
    And subsequent stages should process those 50
    And the pipeline should stop after processing 50 items

  Scenario: Apply different limits per stage
    Given the pipeline is configured with:
      | Stage    | Limit |
      | collect  | 100   |
      | archive  | 50    |
      | analyze  | 20    |
      | score    | 100   |
    When I run the pipeline command
    Then each stage should respect its individual limit
    And the pipeline should process items according to stage limits

  # ============================================================================
  # ERROR HANDLING & RESILIENCE
  # ============================================================================

  Scenario: Pipeline continues after non-critical errors
    Given there are 100 intimations to process
    And intimation #50 has a corrupted PDF
    When I run the pipeline command
    Then intimations 1-49 should be processed successfully
    And intimation #50 should be logged as failed
    And intimations 51-100 should continue processing
    And the pipeline should complete with warnings

  Scenario: Pipeline fails gracefully on critical errors
    Given the database connection is lost during execution
    When I run the pipeline command
    Then the pipeline should detect the connection failure
    And the pipeline should log a critical error
    And the pipeline should exit with error code
    And partial results should not corrupt the database

  Scenario: Pipeline recovery after interruption
    Given a pipeline run was interrupted mid-execution
    And some intimations were collected but not archived
    When I run the pipeline command again
    Then the pipeline should resume from the last successful state
    And no duplicate processing should occur
    And all stages should eventually complete

  # ============================================================================
  # PERFORMANCE & MONITORING
  # ============================================================================

  Scenario: Pipeline displays progress for each stage
    Given there are 100 intimations to process through all stages
    When I run the pipeline command
    Then progress should be displayed for the collect stage
    And progress should be displayed for the archive stage
    And progress should be displayed for the analyze stage
    And progress should be displayed for the score stage
    And each stage should show percentage completion

  Scenario: Pipeline provides timing information per stage
    When I run the pipeline command
    Then the summary should include time taken for collect stage
    And the summary should include time taken for archive stage
    And the summary should include time taken for analyze stage
    And the summary should include time taken for score stage
    And the summary should include total pipeline duration

  Scenario: Pipeline logs detailed execution information
    When I run the pipeline command
    Then structured logs should be emitted for each stage
    And logs should include timestamps
    And logs should include success/failure counts
    And logs should be parseable for monitoring tools

  # ============================================================================
  # DATA CONSISTENCY
  # ============================================================================

  Scenario: Pipeline maintains referential integrity across stages
    Given there are 50 new intimations
    When I run the pipeline command
    Then each archived intimation should reference a valid intimation ID
    And each analysis should reference a valid intimation ID
    And each rating update should reference a valid analysis ID
    And no orphaned records should exist

  Scenario: Pipeline handles concurrent executions safely
    Given a pipeline is currently running
    When I attempt to start another pipeline run
    Then the system should detect the concurrent execution
    And the second pipeline should either queue or fail gracefully
    And database locks should prevent data corruption

  # ============================================================================
  # CONFIGURATION & FLEXIBILITY
  # ============================================================================

  Scenario: Pipeline respects court-specific configuration
    Given court "TJRO" is configured with lookback 14 days
    And court "TJAC" is configured with lookback 7 days
    When I run the pipeline command for both courts
    Then "TJRO" should query 14 days of data
    And "TJAC" should query 7 days of data
    And each court should be processed with its specific configuration

  Scenario: Pipeline uses environment-specific settings
    Given the pipeline is running in production environment
    When I run the pipeline command
    Then production batch sizes should be used
    And production API rate limits should be respected
    And production logging level should be applied

  # ============================================================================
  # DRY RUN MODE
  # ============================================================================

  Scenario: Dry run mode simulates pipeline without side effects
    Given there are 20 new decisions available
    When I run the pipeline command with --dry-run flag
    Then the pipeline should simulate all stages
    And no data should be written to the database
    And no uploads should be made to Internet Archive
    And no LLM calls should be made
    And a summary should show what would have been processed

  Scenario: Dry run mode validates configuration
    Given the LLM API credentials are misconfigured
    When I run the pipeline command with --dry-run flag
    Then the configuration error should be detected
    And the pipeline should exit with error
    And the error message should explain the misconfiguration

  # ============================================================================
  # STAGE DEPENDENCIES
  # ============================================================================

  Scenario: Analysis stage depends on archival completion
    Given there are 10 unarchived intimations
    When I run the pipeline command
    Then the analyze stage should only process archived intimations
    And unarchived intimations should be skipped in analysis
    And a warning should indicate unarchived items were skipped

  Scenario: Scoring stage depends on analysis completion
    Given there are 15 unanalyzed intimations
    When I run the pipeline command
    Then the score stage should only process analyzed intimations
    And unanalyzed intimations should be skipped in scoring
    And a warning should indicate unanalyzed items were skipped

  # ============================================================================
  # SCHEDULING & AUTOMATION
  # ============================================================================

  Scenario: Pipeline runs successfully via scheduled job
    Given the pipeline is configured to run via GitHub Actions
    When the scheduled job triggers at 2 AM UTC
    Then the pipeline should execute all stages automatically
    And results should be logged for monitoring
    And failures should trigger notifications

  Scenario: Pipeline adapts to available data volume
    Given there are only 5 new decisions available
    When the scheduled pipeline runs
    Then the pipeline should process the 5 decisions efficiently
    And the pipeline should complete quickly
    And no errors should occur due to low volume

  Scenario: Pipeline handles high-volume days efficiently
    Given there are 5000 new decisions available
    When the scheduled pipeline runs
    Then the pipeline should process in manageable batches
    And resource usage should remain within limits
    And the pipeline should complete all data within timeout

  # ============================================================================
  # SUMMARY & REPORTING
  # ============================================================================

  Scenario: Pipeline provides comprehensive execution summary
    Given the pipeline processes 100 intimations
    When the pipeline completes
    Then the summary should include:
      | Metric                    | Example Value |
      | Total intimations collected | 100         |
      | Intimations archived        | 95          |
      | Intimations analyzed        | 90          |
      | Analyses scored             | 85          |
      | Unique lawyers rated        | 150         |
      | Total execution time        | 15m 30s     |
      | Errors encountered          | 5           |

  Scenario: Pipeline summary highlights failures and warnings
    Given the pipeline encounters 3 PDF download failures
    And the pipeline encounters 2 LLM timeout errors
    When the pipeline completes
    Then the summary should list the 3 PDF failures
    And the summary should list the 2 LLM timeouts
    And the summary should provide failure details
    And the summary should suggest remediation actions

  # ============================================================================
  # ROLLBACK & SAFETY
  # ============================================================================

  Scenario: Pipeline supports rollback of last run
    Given a pipeline run completed with questionable results
    When I run the pipeline rollback command
    Then the last run's database changes should be reverted
    And intimations should be marked as unprocessed
    And ratings should be restored to previous values
    And a rollback log should be created

  Scenario: Pipeline validates data quality before committing
    Given the analyze stage produces 50% low-confidence results
    When the pipeline quality check runs
    Then a warning should be raised about data quality
    And the user should be prompted to review before proceeding
    And the pipeline should optionally abort if quality is too low
