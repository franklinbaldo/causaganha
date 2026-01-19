Feature: Judicial Decision Data Collection
  As a CausaGanha operator
  I want to automatically collect judicial decisions from Brazilian tribunals
  So that I can build a comprehensive database for lawyer performance analysis

  Background:
    Given the CausaGanha database is initialized
    And the PJe API is accessible

  # ============================================================================
  # CORE COLLECTION SCENARIOS
  # ============================================================================

  Scenario: Collect intimations from a single court for a date range
    Given the monitored court "TJRO" is configured
    And there are 50 intimations available in PJe for "TJRO" between "2025-01-01" and "2025-01-07"
    When I run the collect command for court "TJRO" with date range "2025-01-01" to "2025-01-07"
    Then the intimations table should contain 50 new records
    And each intimation should have a valid case number
    And each intimation should have a tribunal code "TJRO"
    And each intimation should have a PDF link
    And each intimation should have a unique hash

  Scenario: Extract lawyer associations from intimations
    Given the monitored court "TJSP" is configured
    And an intimation contains the following lawyers:
      | OAB      | State | Name              | Pole        |
      | 123456   | SP    | João Silva        | AUTOR       |
      | 234567   | SP    | Maria Santos      | REU         |
    When I run the collect command for court "TJSP"
    Then the intimation_lawyers table should contain 2 new records
    And the lawyer "123456/SP" should be associated with pole "AUTOR"
    And the lawyer "234567/SP" should be associated with pole "REU"

  Scenario: Handle pagination for large result sets
    Given the monitored court "TJMG" is configured
    And there are 250 intimations available in PJe for "TJMG"
    And the PJe API returns results in pages of 100 records
    When I run the collect command for court "TJMG"
    Then the system should make 3 API requests
    And the intimations table should contain 250 new records
    And no records should be duplicated

  Scenario: Detect and skip duplicate intimations
    Given the intimations table contains an intimation with hash "abc123def456"
    And the PJe API returns an intimation with the same hash "abc123def456"
    When I run the collect command
    Then the system should skip the duplicate intimation
    And the intimations table should not contain duplicate hashes
    And the log should indicate "duplicate skipped"

  # ============================================================================
  # DATE RANGE HANDLING
  # ============================================================================

  Scenario: Collect with default 7-day lookback period
    Given today is "2025-01-15"
    And I do not specify a date range
    When I run the collect command for court "TJAC"
    Then the system should query PJe from "2025-01-08" to "2025-01-15"

  Scenario: Collect with custom date range
    Given the monitored court "TJAL" is configured
    When I run the collect command with start date "2024-12-01" and end date "2024-12-31"
    Then the system should query PJe from "2024-12-01" to "2024-12-31"
    And only intimations within that date range should be stored

  # ============================================================================
  # DATA QUALITY & VALIDATION
  # ============================================================================

  Scenario: Validate intimation data structure
    Given an intimation is received from PJe API
    When the intimation is processed
    Then the intimation must have a valid case number format
    And the intimation must have a non-empty tribunal code
    And the intimation must have a valid PDF URL
    And the intimation must have a publication date

  Scenario: Handle intimations with missing lawyer information
    Given an intimation from PJe has no "destinatarioadvogados" field
    When the intimation is processed
    Then the intimation should be stored in the intimations table
    And the intimation_lawyers table should have 0 entries for that intimation
    And the intimation should be marked as "no lawyers associated"

  Scenario: Normalize OAB numbers with different formats
    Given an intimation contains lawyers with OAB numbers:
      | Raw OAB         | Expected OAB | State |
      | 123456          | 123456       | SP    |
      | OAB/SP 123.456  | 123456       | SP    |
      | 123456/SP       | 123456       | SP    |
    When the intimation is processed
    Then all OAB numbers should be stored in normalized format "123456"
    And the state "SP" should be stored separately

  # ============================================================================
  # MULTI-COURT COLLECTION
  # ============================================================================

  Scenario: Collect from multiple courts in a single command
    Given the following courts are configured:
      | Court | Expected Intimations |
      | TJRO  | 30                   |
      | TJAC  | 20                   |
      | TJAP  | 15                   |
    When I run the collect command for courts "TJRO,TJAC,TJAP"
    Then the intimations table should contain 65 new records
    And records should be properly tagged with their respective tribunal codes

  Scenario: Continue collection after partial court failure
    Given courts "TJRO,TJAC,TJAP" are configured
    And the PJe API for "TJAC" returns a 500 error
    When I run the collect command for all courts
    Then intimations from "TJRO" should be collected successfully
    And intimations from "TJAP" should be collected successfully
    And the error for "TJAC" should be logged
    And the command should complete with a warning

  # ============================================================================
  # LIMITS & BATCH CONTROL
  # ============================================================================

  Scenario: Respect collection limit parameter
    Given there are 1000 intimations available in PJe for "TJRJ"
    When I run the collect command with limit 50
    Then the intimations table should contain exactly 50 new records
    And the collection should stop after reaching the limit

  Scenario: Collect all available intimations without limit
    Given there are 200 intimations available in PJe for "TJRR"
    When I run the collect command without a limit
    Then the intimations table should contain all 200 records

  # ============================================================================
  # METADATA & TRACKING
  # ============================================================================

  Scenario: Record collection metadata in sync log
    Given the monitored court "TJSE" is configured
    When I run the collect command for court "TJSE"
    Then the sync_log table should have a new entry
    And the log entry should record the collection timestamp
    And the log entry should record the number of intimations collected
    And the log entry should record the court code
    And the log entry should record the date range used

  Scenario: Track collection progress for monitoring
    Given there are 100 intimations to collect
    When I run the collect command
    Then the system should display progress updates
    And the progress should show items collected per second
    And the final progress should show total intimations collected

  # ============================================================================
  # ERROR RECOVERY
  # ============================================================================

  Scenario: Retry failed API requests
    Given the PJe API intermittently returns network errors
    And the retry policy is configured for 3 attempts
    When I run the collect command
    And the first API request fails with a connection error
    Then the system should retry the request
    And the collection should succeed after retry
    And the retry should be logged

  Scenario: Handle API rate limiting gracefully
    Given the PJe API returns a 429 "Too Many Requests" response
    When I run the collect command
    Then the system should wait before retrying
    And the system should respect the "Retry-After" header
    And the collection should complete successfully after the wait

  # ============================================================================
  # INCREMENTAL UPDATES
  # ============================================================================

  Scenario: Incremental collection for daily updates
    Given intimations were last collected on "2025-01-10"
    And today is "2025-01-17"
    When I run the collect command with incremental mode
    Then the system should only query from "2025-01-10" to "2025-01-17"
    And only new intimations should be added
    And existing intimations should not be updated

  Scenario: Full refresh collection
    Given the intimations table contains 500 existing records
    When I run the collect command with refresh mode
    Then the system should query the full date range
    And duplicate intimations should be skipped
    And new intimations should be added
    And the total count should reflect all available intimations
