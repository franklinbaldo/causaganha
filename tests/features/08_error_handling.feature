Feature: Error Handling and System Resilience
  As a system operator
  I want the system to handle errors gracefully
  So that partial failures don't halt the entire pipeline

  Background:
    Given the CausaGanha database is initialized
    And error handling is configured with retry policies

  # ============================================================================
  # NETWORK & API FAILURES
  # ============================================================================

  Scenario: Retry transient network errors with exponential backoff
    Given the PJe API is experiencing intermittent network errors
    And the retry policy is configured for 3 attempts with exponential backoff
    When I run the collect command
    And the first request fails with connection timeout
    Then the system should wait 2 seconds and retry
    And if the second request fails, wait 4 seconds and retry
    And if the third request succeeds, the collection should complete
    And all retries should be logged

  Scenario: Permanent API errors are not retried indefinitely
    Given the PJe API returns 404 for a specific intimation
    When I run the collect command
    Then the system should retry up to 3 times
    And after 3 failures, the error should be logged as permanent
    And the intimation should be marked as failed
    And the pipeline should continue with other intimations

  Scenario: Handle API rate limiting gracefully
    Given the PJe API returns 429 "Too Many Requests"
    And the response includes "Retry-After: 60" header
    When I run the collect command
    Then the system should wait 60 seconds before retrying
    And the wait should be logged
    And the request should succeed after waiting

  Scenario: Handle API authentication failures
    Given the PJe API credentials have expired
    And the API returns 401 "Unauthorized"
    When I run the collect command
    Then the system should log an authentication error
    And the system should attempt to refresh credentials if possible
    And if refresh fails, the error should be escalated
    And no data corruption should occur

  # ============================================================================
  # DATABASE FAILURES
  # ============================================================================

  Scenario: Recover from temporary database connection loss
    Given a collection is in progress
    And the database connection is lost mid-operation
    When the connection is restored
    Then the system should reconnect automatically
    And the operation should be retried
    And no data should be lost
    And the pipeline should continue

  Scenario: Rollback transaction on database write failure
    Given 10 intimations are being inserted in a transaction
    And intimation #7 violates a database constraint
    When the transaction fails
    Then all 10 intimations should be rolled back
    And the database should remain in a consistent state
    And the error should be logged with details
    And the failed intimation should be identified

  Scenario: Handle database disk space exhaustion
    Given the database disk is 98% full
    When I run the pipeline command
    Then the system should detect low disk space
    And a critical alert should be raised
    And the pipeline should exit gracefully
    And no partial writes should corrupt the database

  # ============================================================================
  # LLM & AI SERVICE FAILURES
  # ============================================================================

  Scenario: Retry LLM timeouts with backoff
    Given the Gemini API is slow and timing out
    And a decision analysis request times out after 30 seconds
    When I run the analyze command
    Then the system should retry the request
    And the retry should have an increased timeout
    And if retries fail, the intimation should remain unanalyzed
    And the error should be logged with decision ID

  Scenario: Handle LLM quota exhaustion
    Given the Gemini API quota is exceeded
    And the API returns 429 "Quota exceeded"
    When I run the analyze command
    Then the system should log a quota error
    And analysis should be paused until quota resets
    And the system should wait for quota reset time
    And the pipeline should resume automatically when quota available

  Scenario: Validate and reject malformed LLM responses
    Given the Gemini API returns invalid JSON
    When I run the analyze command
    And the response is parsed
    Then the system should detect the malformed response
    And the response should be rejected
    And the intimation should remain unanalyzed
    And a validation error should be logged

  Scenario: Handle LLM confidence too low
    Given the Gemini API returns analysis with confidence 0.15
    And the minimum confidence threshold is 0.30
    When I run the analyze command
    Then the analysis should be rejected
    And the intimation should remain unanalyzed
    And the low confidence should be logged
    And the intimation should be flagged for manual review

  # ============================================================================
  # FILE & PDF HANDLING ERRORS
  # ============================================================================

  Scenario: Handle corrupted PDF files gracefully
    Given an intimation has a PDF URL
    And the PDF file is corrupted or malformed
    When I run the archive command
    Then the system should detect the invalid PDF
    And the PDF should not be uploaded to Internet Archive
    And the error should be logged with intimation ID
    And the process should continue with other intimations

  Scenario: Handle PDF download failures
    Given an intimation has a PDF URL
    And the PDF server returns 503 "Service Unavailable"
    When I run the archive command
    Then the system should retry the download 3 times
    And if all retries fail, the intimation should remain unarchived
    And the error should be logged
    And the pipeline should continue

  Scenario: Handle extremely large PDF files
    Given an intimation has a PDF file that is 500MB
    And the system has a size limit of 100MB
    When I run the archive command
    Then the system should detect the oversized file
    And the file should be skipped with a warning
    And the intimation should be marked as "PDF too large"
    And the pipeline should continue

  Scenario: Handle missing PDF files (404)
    Given an intimation has a PDF URL
    And the URL returns 404 "Not Found"
    When I run the archive command
    Then the system should log the missing PDF
    And the intimation should be marked as "PDF not found"
    And no retry should occur for 404 errors
    And the pipeline should continue

  # ============================================================================
  # INTERNET ARCHIVE FAILURES
  # ============================================================================

  Scenario: Retry Internet Archive upload failures
    Given a PDF is ready for upload to Internet Archive
    And the Internet Archive API returns a 503 error
    When I run the archive command
    Then the system should retry the upload 3 times with backoff
    And if retries succeed, the ia_url should be stored
    And if retries fail, the intimation should remain unarchived

  Scenario: Handle Internet Archive authentication errors
    Given Internet Archive credentials are invalid
    When I run the archive command
    Then the system should detect the authentication failure
    And the error should be logged clearly
    And the pipeline should exit with an error
    And no intimations should be marked as archived

  Scenario: Verify Internet Archive upload success
    Given a PDF is uploaded to Internet Archive
    When the upload completes
    Then the system should verify the item exists on archive.org
    And if verification fails, the upload should be retried
    And only verified uploads should update ia_url in database

  # ============================================================================
  # CONCURRENT PROCESSING ERRORS
  # ============================================================================

  Scenario: Handle race conditions in concurrent processing
    Given two processes are updating lawyer "123456/SP" rating simultaneously
    When both processes commit their updates
    Then the database should handle the conflict
    And one process should retry with updated data
    And the final rating should be consistent
    And no rating updates should be lost

  Scenario: Prevent deadlocks in batch processing
    Given multiple pipeline stages are running concurrently
    And they access overlapping database records
    When a potential deadlock situation arises
    Then the database should detect the deadlock
    And one transaction should be rolled back and retried
    And the pipeline should complete successfully

  # ============================================================================
  # DATA VALIDATION ERRORS
  # ============================================================================

  Scenario: Reject intimations with invalid case numbers
    Given an intimation has case number "INVALID-123"
    When the intimation is validated
    Then the system should detect the invalid format
    And the intimation should be rejected
    And a validation error should be logged
    And the pipeline should continue with valid intimations

  Scenario: Reject analyses with missing required fields
    Given an LLM analysis is missing the "outcome" field
    When the analysis is validated
    Then the system should detect the missing field
    And the analysis should be rejected
    And the intimation should remain unanalyzed
    And a validation error should be logged

  Scenario: Handle invalid OAB numbers gracefully
    Given an analysis contains OAB number "INVALID"
    When the analysis is processed
    Then the system should detect the invalid OAB
    And the analysis should be marked for manual review
    And the scoring should skip this analysis
    And a validation warning should be logged

  # ============================================================================
  # CONFIGURATION ERRORS
  # ============================================================================

  Scenario: Detect missing configuration at startup
    Given the Gemini API key is not configured
    When I run the analyze command
    Then the system should detect the missing configuration
    And a clear error message should be displayed
    And the pipeline should exit without processing
    And no partial state should be saved

  Scenario: Validate configuration before execution
    Given an invalid court code "TJXX" is specified
    When I run the collect command for "TJXX"
    Then the system should validate the court code
    And an error should be raised about invalid court
    And the command should exit before API calls
    And helpful suggestions should be provided

  # ============================================================================
  # RESOURCE EXHAUSTION
  # ============================================================================

  Scenario: Handle memory exhaustion gracefully
    Given the system is processing 10,000 intimations
    And available memory is limited
    When memory usage approaches the limit
    Then the system should process in smaller batches
    And memory should be freed between batches
    And the pipeline should complete without crashing

  Scenario: Handle thread pool exhaustion
    Given the system is processing 100 concurrent requests
    And the thread pool has 20 threads
    When all threads are busy
    Then new requests should be queued
    And the queue should have a maximum size
    And the system should process all requests eventually

  # ============================================================================
  # PARTIAL FAILURE RECOVERY
  # ============================================================================

  Scenario: Continue pipeline after partial batch failure
    Given there are 100 intimations to analyze
    And intimations #20, #45, and #78 fail with LLM errors
    When I run the analyze command
    Then intimations 1-19, 21-44, 46-77, 79-100 should be analyzed
    And 3 intimations should be logged as failed
    And the pipeline should complete with 97 successes
    And the summary should clearly show partial failures

  Scenario: Isolate failures to prevent cascading
    Given an analysis failure occurs for intimation "int-001"
    When the failure is handled
    Then the failure should not affect other intimations
    And the error should be contained to that intimation
    And the pipeline should continue uninterrupted
    And no database corruption should occur

  # ============================================================================
  # LOGGING & OBSERVABILITY
  # ============================================================================

  Scenario: Log errors with sufficient context
    Given a PDF download fails for intimation "int-456"
    When the error is logged
    Then the log should include the intimation ID
    And the log should include the PDF URL
    And the log should include the error message
    And the log should include the timestamp
    And the log should include the stack trace

  Scenario: Structured error logging for monitoring
    Given errors occur during pipeline execution
    When errors are logged
    Then logs should be in JSON format
    And logs should include severity level
    And logs should include error category
    And logs should be parseable by log aggregation tools

  Scenario: Track error metrics for monitoring
    Given the pipeline processes 1000 intimations
    And 50 errors occur across different stages
    When the pipeline completes
    Then error counts should be tracked per stage
    And error rates should be calculated
    And metrics should be available for monitoring systems
    And alerts should be triggered for high error rates

  # ============================================================================
  # CIRCUIT BREAKER PATTERN
  # ============================================================================

  Scenario: Open circuit breaker after repeated failures
    Given the PJe API for "TJRO" has failed 10 times in 5 minutes
    When the 11th request is about to be made
    Then the circuit breaker should open
    And the request should be rejected immediately
    And a circuit open error should be logged
    And the system should wait before trying again

  Scenario: Close circuit breaker after recovery period
    Given the circuit breaker for "TJRO" is open
    And 60 seconds have passed
    When a test request succeeds
    Then the circuit breaker should close
    And normal processing should resume
    And the recovery should be logged

  # ============================================================================
  # GRACEFUL DEGRADATION
  # ============================================================================

  Scenario: Degrade to essential operations on high error rate
    Given 30% of LLM requests are failing
    When the error rate exceeds threshold
    Then the system should reduce batch sizes
    And the system should increase retry delays
    And the system should prioritize high-confidence items
    And the degradation should be logged

  Scenario: Continue with reduced functionality on service failure
    Given the Internet Archive service is unavailable
    When I run the pipeline command
    Then collection and analysis should continue
    And archival should be skipped with warnings
    And intimations should be marked for later archival
    And the pipeline should complete essential operations

  # ============================================================================
  # ERROR REPORTING
  # ============================================================================

  Scenario: Generate error summary report
    Given the pipeline completed with errors
    When I request an error summary
    Then the report should list all errors by type
    And the report should show error counts per stage
    And the report should identify affected intimations
    And the report should suggest remediation steps

  Scenario: Alert administrators on critical errors
    Given a critical error occurs (database failure)
    When the error is detected
    Then an alert should be sent to administrators
    And the alert should include error details
    And the alert should include system state
    And the alert should suggest immediate actions
