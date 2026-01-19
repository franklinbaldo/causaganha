Feature: Document Preservation to Internet Archive
  As a transparency advocate
  I want all judicial decisions permanently archived
  So that they remain accessible for future research and accountability

  Background:
    Given the CausaGanha database is initialized
    And the Internet Archive API is accessible
    And Internet Archive credentials are configured

  # ============================================================================
  # CORE ARCHIVAL SCENARIOS
  # ============================================================================

  Scenario: Archive a single intimation to Internet Archive
    Given an intimation "int-001" with PDF URL "https://pje.tjro.jus.br/docs/decision-001.pdf"
    And the intimation has not been archived (ia_url is NULL)
    When I run the archive command
    Then the PDF should be downloaded from PJe
    And the PDF should be uploaded to Internet Archive
    And the intimation should be updated with the Internet Archive URL
    And the ia_url should match pattern "https://archive.org/details/causaganha-*"

  Scenario: Generate appropriate metadata for archived item
    Given an intimation with the following data:
      | Field              | Value                           |
      | numero_processo    | 0001234-56.2024.8.22.0001      |
      | sigla_tribunal     | TJRO                            |
      | data_disponib      | 2025-01-15                      |
    When I run the archive command
    Then the Internet Archive item should have metadata:
      | Metadata Field     | Expected Value                   |
      | title              | Decision 0001234-56.2024.8.22.0001 - TJRO |
      | collection         | causaganha                       |
      | mediatype          | texts                            |
      | subject            | judicial decisions; brazil; TJRO |
      | date               | 2025-01-15                       |

  Scenario: Create unique item identifier for each decision
    Given intimations with case numbers:
      | Case Number                  |
      | 0001234-56.2024.8.22.0001   |
      | 0007890-12.2024.8.22.0002   |
    When I run the archive command
    Then each intimation should have a unique Internet Archive identifier
    And identifiers should include the tribunal code
    And identifiers should include a sanitized version of the case number

  # ============================================================================
  # PDF DOWNLOAD & HANDLING
  # ============================================================================

  Scenario: Download PDF from PJe successfully
    Given an intimation with PDF URL "https://pje.tjac.jus.br/docs/decision-123.pdf"
    When I run the archive command
    Then the system should make an HTTP request to the PDF URL
    And the PDF content should be retrieved as bytes
    And the PDF should be validated as a valid PDF file

  Scenario: Retry PDF download on transient failures
    Given an intimation with PDF URL that fails on first attempt
    And the retry policy is configured for 3 attempts
    When I run the archive command
    Then the system should retry the download
    And the archive should succeed after retry

  Scenario: Skip archival for invalid PDF URLs
    Given an intimation with invalid PDF URL "https://example.com/not-a-pdf"
    When I run the archive command
    Then the system should log an error about invalid URL
    And the intimation should remain unarchived
    And the process should continue with other intimations

  Scenario: Handle large PDF files efficiently
    Given an intimation with a 50MB PDF file
    When I run the archive command
    Then the system should download the file in chunks
    And memory usage should remain bounded
    And the upload to Internet Archive should succeed

  # ============================================================================
  # INTERNET ARCHIVE INTEGRATION
  # ============================================================================

  Scenario: Upload PDF to Internet Archive successfully
    Given a valid PDF has been downloaded
    When the system uploads to Internet Archive
    Then the upload should use the configured S3 credentials
    And the item should be created in the "causaganha" collection
    And the upload should return a valid Internet Archive URL

  Scenario: Handle Internet Archive rate limits
    Given there are 100 intimations to archive
    And Internet Archive has rate limits
    When I run the archive command
    Then the system should respect rate limits
    And the system should use backoff strategies when rate limited
    And all intimations should eventually be archived

  Scenario: Verify successful upload with Internet Archive
    Given an intimation has been uploaded to Internet Archive
    When the upload completes
    Then the system should verify the item exists on archive.org
    And the system should confirm the PDF is accessible
    And only then should the ia_url be stored in the database

  Scenario: Retry upload on transient Internet Archive failures
    Given an intimation ready for upload
    And Internet Archive returns a 503 error on first attempt
    When I run the archive command
    Then the system should retry the upload
    And the archive should succeed after retry

  # ============================================================================
  # DRY RUN MODE
  # ============================================================================

  Scenario: Dry run mode downloads but does not upload
    Given there are 5 unarchived intimations
    When I run the archive command with --dry-run flag
    Then PDFs should be downloaded
    And PDFs should be validated
    And no uploads to Internet Archive should occur
    And no ia_url should be stored in the database
    And a summary should show what would have been archived

  Scenario: Dry run mode helps validate configuration
    Given Internet Archive credentials are misconfigured
    When I run the archive command with --dry-run flag
    Then PDF downloads should still work
    And the system should warn about missing credentials
    And the command should complete without errors

  # ============================================================================
  # BATCH PROCESSING
  # ============================================================================

  Scenario: Archive multiple intimations in batch
    Given there are 20 unarchived intimations
    When I run the archive command with limit 20
    Then all 20 intimations should be archived
    And each should have a unique Internet Archive URL
    And all PDFs should be successfully uploaded

  Scenario: Respect archival limit parameter
    Given there are 100 unarchived intimations
    When I run the archive command with limit 10
    Then exactly 10 intimations should be archived
    And 90 should remain unarchived
    And the archived ones should be marked first

  Scenario: Process archives concurrently for efficiency
    Given there are 10 unarchived intimations
    When I run the archive command
    Then multiple downloads should occur concurrently
    And multiple uploads should occur concurrently
    And the total time should be less than sequential processing

  # ============================================================================
  # INCREMENTAL ARCHIVAL
  # ============================================================================

  Scenario: Only archive intimations not yet archived
    Given the intimations table contains:
      | ID    | ia_url                                    |
      | int-1 | https://archive.org/details/causaganha-1  |
      | int-2 | NULL                                      |
      | int-3 | NULL                                      |
    When I run the archive command
    Then only intimations "int-2" and "int-3" should be processed
    And intimation "int-1" should be skipped

  Scenario: Mark intimation as archived after successful upload
    Given an unarchived intimation with ID "int-mark"
    When I run the archive command
    And the upload succeeds
    Then the intimation "int-mark" should have ia_url populated
    And subsequent archive commands should skip it

  # ============================================================================
  # ERROR HANDLING & RECOVERY
  # ============================================================================

  Scenario: Continue archival after individual failures
    Given there are 10 unarchived intimations
    And intimation #5 has an invalid PDF URL
    When I run the archive command
    Then intimations 1-4 should be archived successfully
    And intimation #5 should be logged as failed
    And intimations 6-10 should be archived successfully
    And the command should complete with warnings

  Scenario: Preserve error information for failed archives
    Given an intimation fails to archive due to network error
    When the archive attempt completes
    Then the error should be logged in the database
    And the intimation should remain unarchived (ia_url NULL)
    And the error message should be available for debugging

  Scenario: Retry failed archives on subsequent runs
    Given an intimation failed to archive on first attempt
    And the error was transient (network timeout)
    When I run the archive command again
    Then the intimation should be retried
    And the archive should succeed on the second attempt

  # ============================================================================
  # DATA INTEGRITY
  # ============================================================================

  Scenario: Prevent duplicate archives for same intimation
    Given an intimation "int-dup" has already been archived
    And the ia_url is "https://archive.org/details/causaganha-dup"
    When I run the archive command
    Then intimation "int-dup" should be skipped
    And no duplicate item should be created on Internet Archive

  Scenario: Validate PDF before upload
    Given an intimation with a corrupted PDF file
    When I run the archive command
    Then the system should detect the invalid PDF
    And the upload should not be attempted
    And an error should be logged about PDF corruption

  Scenario: Ensure PDF matches intimation metadata
    Given an intimation with case number "0001234-56.2024.8.22.0001"
    And the downloaded PDF is for a different case
    When I run the archive command
    Then the system should detect the mismatch
    And the upload should be aborted
    And a warning should be logged

  # ============================================================================
  # METADATA ENRICHMENT
  # ============================================================================

  Scenario: Include tribunal information in archive metadata
    Given an intimation from tribunal "TJSP"
    When I run the archive command
    Then the Internet Archive metadata should include tribunal "TJSP"
    And the metadata should include tribunal full name "Tribunal de Justiça de São Paulo"

  Scenario: Include parties information if available
    Given an intimation with plaintiff "João Silva" and defendant "Maria Santos"
    When I run the archive command
    Then the Internet Archive metadata should include party names
    And the metadata should be searchable by party names

  Scenario: Tag archived items for discoverability
    Given an intimation is being archived
    When I run the archive command
    Then the Internet Archive item should have tags:
      | Tag                  |
      | judicial-decisions   |
      | brazil               |
      | transparency         |
      | causaganha           |

  # ============================================================================
  # PROGRESS & MONITORING
  # ============================================================================

  Scenario: Display progress during batch archival
    Given there are 50 unarchived intimations
    When I run the archive command
    Then the system should display progress updates
    And progress should show number of items archived
    And progress should show current item being processed
    And progress should show estimated time remaining

  Scenario: Provide summary after archival completion
    Given there are 30 unarchived intimations
    When I run the archive command
    Then the summary should show total intimations processed
    And the summary should show successful archives
    And the summary should show failed archives
    And the summary should show total PDFs uploaded

  # ============================================================================
  # SPECIAL CASES
  # ============================================================================

  Scenario: Handle intimations with missing PDF URLs
    Given an intimation has no PDF URL (link field is NULL)
    When I run the archive command
    Then the intimation should be skipped
    And a warning should be logged about missing PDF URL
    And the process should continue with other intimations

  Scenario: Archive decisions from different tribunals
    Given unarchived intimations from tribunals "TJRO", "TJAC", "TJAP"
    When I run the archive command
    Then each should be archived with tribunal-specific metadata
    And Internet Archive items should be tagged with their respective tribunals
    And items should be organized in the causaganha collection

  Scenario: Preserve original PDF without modification
    Given an intimation with a PDF file
    When I run the archive command
    Then the uploaded PDF should be byte-for-byte identical to the original
    And no compression or conversion should be applied
    And the PDF should be permanently preserved
