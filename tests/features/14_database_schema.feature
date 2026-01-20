Feature: Database Schema Management
  As a database administrator
  I want database migrations to be tracked and verifiable
  So that schema changes are applied correctly and consistently

  Background:
    Given the CausaGanha database exists

  # ============================================================================
  # PARQUET EXPORT TRACKING
  # ============================================================================

  Scenario: Parquet export tracking table exists
    When I check the database schema
    Then a table "parquet_exports" should exist
    And it should have the following columns:
      | Column Name      | Type      | Nullable | Description                           |
      | id               | INTEGER   | No       | Primary key                           |
      | tribunal         | VARCHAR   | No       | Tribunal code (e.g., TJRO)            |
      | partition_date   | DATE      | No       | Date of partition (YYYY-MM-DD)        |
      | ia_item_id       | VARCHAR   | No       | Internet Archive item ID              |
      | ia_url           | VARCHAR   | No       | Full URL to IA item                   |
      | parquet_filename | VARCHAR   | No       | Filename of Parquet file              |
      | row_count        | INTEGER   | No       | Number of rows exported               |
      | file_size_mb     | FLOAT     | No       | File size in megabytes                |
      | uploaded_at      | TIMESTAMP | No       | When upload completed                 |
      | status           | VARCHAR   | No       | Export status (pending/completed/failed) |
      | error_message    | TEXT      | Yes      | Error details if failed               |

  Scenario: Parquet exports table has appropriate indexes
    Given the "parquet_exports" table exists
    When I check the table indexes
    Then it should have an index on "partition_date"
    And it should have an index on "tribunal"
    And it should have an index on "status"
    And it should have a unique constraint on ("tribunal", "partition_date")

  Scenario: Record successful Parquet export
    Given the "parquet_exports" table exists
    When I insert an export record:
      | Field            | Value                                          |
      | tribunal         | TJRO                                           |
      | partition_date   | 2025-01-15                                     |
      | ia_item_id       | causaganha-2025-01-15-TJRO                     |
      | ia_url           | https://archive.org/details/causaganha-2025-01-15-TJRO |
      | parquet_filename | causaganha-2025-01-15-TJRO.parquet             |
      | row_count        | 3000                                           |
      | file_size_mb     | 1.5                                            |
      | uploaded_at      | 2025-01-16 02:15:30                            |
      | status           | completed                                      |
    Then the record should be inserted successfully
    And I should be able to query it by tribunal and date

  Scenario: Prevent duplicate export records
    Given the "parquet_exports" table exists
    And an export exists for tribunal "TJRO" on date "2025-01-15"
    When I try to insert another export for "TJRO" on "2025-01-15"
    Then the insert should fail with a unique constraint violation
    And the error should indicate duplicate key on ("tribunal", "partition_date")

  Scenario: Query export status by date range
    Given the "parquet_exports" table exists
    And exports exist for dates 2025-01-01 through 2025-01-31
    When I query exports for dates between "2025-01-01" and "2025-01-15"
    Then I should get 15 days × 90 tribunals = 1,350 records
    And all records should have status "completed"

  Scenario: Query export status by tribunal
    Given the "parquet_exports" table exists
    And exports exist for all tribunals on date "2025-01-15"
    When I query exports for tribunal "TJRO"
    Then I should get records only for "TJRO"
    And I should not get records for other tribunals

  Scenario: Identify failed exports
    Given the "parquet_exports" table exists
    And 90 exports exist for date "2025-01-15"
    And 3 exports have status "failed"
    When I query for failed exports
    Then I should get exactly 3 records
    And each should have an error_message populated
    And each should have status "failed"

  Scenario: Calculate export completeness percentage
    Given the "parquet_exports" table exists
    And 90 tribunals are active
    And 87 exports are "completed" for date "2025-01-15"
    And 3 exports are "failed" for date "2025-01-15"
    When I calculate the export success rate for "2025-01-15"
    Then the success rate should be 96.7% (87/90)
    And I should know which 3 tribunals failed

  # ============================================================================
  # MIGRATION TRACKING
  # ============================================================================

  Scenario: Migration tracking table exists
    When I check the database schema
    Then a table "schema_migrations" should exist
    And it should track applied migration versions
    And it should record when each migration was applied

  Scenario: Apply migration for parquet_exports table
    Given no migrations have been applied
    When I run migration "002_add_parquet_exports"
    Then the "parquet_exports" table should be created
    And the migration should be recorded in "schema_migrations"
    And the migration version should be "002"

  Scenario: Prevent duplicate migration application
    Given migration "002_add_parquet_exports" has been applied
    When I try to run migration "002_add_parquet_exports" again
    Then the migration should be skipped
    And a message should indicate it was already applied

  # ============================================================================
  # DATA INTEGRITY
  # ============================================================================

  Scenario: Parquet filename matches naming convention
    Given the "parquet_exports" table exists
    When I insert an export with filename "invalid-format.parquet"
    Then a validation check should warn about incorrect naming
    And the correct format should be "causaganha-{YYYY}-{MM}-{DD}-{TRIBUNAL}.parquet"

  Scenario: File size should be reasonable
    Given the "parquet_exports" table exists
    When I insert an export with file_size_mb "0.001"
    Then a validation check should warn about suspiciously small file
    And I should verify the export didn't fail partially

  Scenario: Row count should match partition
    Given the "parquet_exports" table exists
    And tribunal "TJRO" typically has ~3,000 decisions per day
    When I insert an export with row_count "10"
    Then a validation check should warn about low row count
    And I should investigate if collection failed

  # ============================================================================
  # CLEANUP OPERATIONS
  # ============================================================================

  Scenario: Purge old intimations after export
    Given the "parquet_exports" table exists
    And an export is completed for date "2024-07-01" (>6 months old)
    And intimations exist in the database for "2024-07-01"
    When I run the data purge operation
    Then intimations for "2024-07-01" should be deleted
    But the export record in "parquet_exports" should remain
    And I can still find the data on Internet Archive

  Scenario: Identify data ready for purge
    Given today is "2025-01-15"
    And exports exist for dates older than 6 months
    When I query for purgeable data
    Then I should get dates before "2024-07-15"
    And each date should have status "completed"
    And I should get a list of intimation_ids to delete

  # ============================================================================
  # MONITORING & REPORTING
  # ============================================================================

  Scenario: Generate daily export report
    Given the "parquet_exports" table exists
    When I generate a report for "2025-01-15"
    Then the report should show:
      | Metric                  | Value |
      | Total tribunals         | 90    |
      | Successful exports      | 87    |
      | Failed exports          | 3     |
      | Success rate            | 96.7% |
      | Total rows exported     | 267K  |
      | Total file size         | 133 MB|
      | Upload duration         | 8m 45s|

  Scenario: Identify tribunals with consistent failures
    Given the "parquet_exports" table exists
    And tribunal "TJXX" has failed exports for the last 7 days
    When I query for problematic tribunals
    Then "TJXX" should be flagged
    And I should see the recurring error message
    And I should be alerted to investigate

  Scenario: Track storage growth over time
    Given the "parquet_exports" table exists
    And exports exist for the past 30 days
    When I query total storage on Internet Archive
    Then I should see cumulative file size by month
    And I should see storage growth rate
    And I can project future storage needs
