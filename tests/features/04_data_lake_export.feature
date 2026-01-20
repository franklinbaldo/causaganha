Feature: Parquet Data Lake on Internet Archive
  As a data engineer and transparency advocate
  I want analyzed decisions exported as Parquet files to Internet Archive
  So that we have free distributed storage and public data verification

  Background:
    Given the CausaGanha database is initialized
    And the Internet Archive API is accessible
    And Internet Archive credentials are configured

  # ============================================================================
  # ARCHITECTURE: Internet Archive as FREE Data Lake
  # - Parquet format: 10x compression, columnar storage
  # - Partitioned by tribunal + date for efficient queries
  # - $0 cost vs $1,500+/year on AWS S3
  # - Public download for verification and reproducibility
  # ============================================================================

  # ============================================================================
  # PARQUET EXPORT FROM DUCKDB
  # ============================================================================

  Scenario: Export single month partition to Parquet
    Given it is the end of January 2025
    And there are 3,000 analyzed intimations for "TJRO" in January 2025
    When I run the export command for tribunal "TJRO" and month "2025-01"
    Then a Parquet file should be created named "causaganha-TJRO-2025-01.parquet"
    And the file should contain exactly 3,000 rows
    And the file should be compressed with snappy codec
    And the file size should be approximately 1.5 MB

  Scenario: Export multiple tribunals for same month
    Given there are analyzed intimations for multiple tribunals in January 2025:
      | Tribunal | Count |
      | TJRO     | 3,000 |
      | TJAC     | 2,000 |
      | TJAP     | 1,500 |
    When I run the export command for month "2025-01"
    Then 3 Parquet files should be created:
      | Filename                        | Rows  | Size  |
      | causaganha-TJRO-2025-01.parquet | 3,000 | ~1.5MB|
      | causaganha-TJAC-2025-01.parquet | 2,000 | ~1.0MB|
      | causaganha-TJAP-2025-01.parquet | 1,500 | ~750KB|

  Scenario: Parquet schema includes all necessary fields
    Given intimations are being exported to Parquet
    When the Parquet file is created
    Then the schema should include:
      | Column Name             | Type      | Required |
      | intimation_id           | INT64     | Yes      |
      | numero_processo         | STRING    | Yes      |
      | sigla_tribunal          | STRING    | Yes      |
      | data_disponibilizacao   | DATE      | Yes      |
      | texto                   | STRING    | Yes      |
      | winner_lawyer_oab       | STRING    | No       |
      | winner_lawyer_state     | STRING    | No       |
      | loser_lawyer_oab        | STRING    | No       |
      | loser_lawyer_state      | STRING    | No       |
      | decision_type           | STRING    | No       |
      | outcome                 | STRING    | No       |
      | confidence_score        | DOUBLE    | No       |
      | analyzed_at             | TIMESTAMP | Yes      |
      | year                    | INT32     | Yes      |
      | month                   | INT32     | Yes      |

  Scenario: Parquet includes denormalized lawyer data
    Given an intimation has multiple lawyers on each side
    When the intimation is exported to Parquet
    Then the Parquet row should include:
      | Field                 | Type                          |
      | plaintiff_lawyers     | ARRAY<STRUCT(oab, state, name)> |
      | defendant_lawyers     | ARRAY<STRUCT(oab, state, name)> |
    And lawyer data should be denormalized (no joins required)

  Scenario: Export validates data completeness
    Given intimations are ready for export
    When the export process runs
    Then it should validate:
      | Validation Rule                          |
      | All analyzed intimations have texto      |
      | All have winner/loser or marked unclear  |
      | All have confidence scores               |
      | All timestamps are valid                 |
    And invalid rows should be logged and skipped

  # ============================================================================
  # INTERNET ARCHIVE UPLOAD
  # ============================================================================

  Scenario: Upload Parquet file to Internet Archive
    Given a Parquet file "causaganha-TJRO-2025-01.parquet" exists locally
    And it contains 3,000 analyzed decisions
    When I run the archive upload command
    Then the file should be uploaded to Internet Archive
    And the item identifier should be "causaganha-TJRO-2025-01"
    And the item URL should be "https://archive.org/details/causaganha-TJRO-2025-01"

  Scenario: Generate comprehensive metadata for IA item
    Given a Parquet file for "TJRO" in "2025-01" is being uploaded
    When the upload occurs
    Then the Internet Archive metadata should include:
      | Field           | Value                                           |
      | title           | CausaGanha - TJRO - January 2025                |
      | collection      | causaganha                                      |
      | mediatype       | data                                            |
      | subject         | judicial decisions; brazil; TJRO; 2025-01       |
      | description     | Tabulated judicial decision data from TJRO      |
      | format          | Parquet                                         |
      | coverage        | TJRO                                            |
      | date            | 2025-01                                         |
      | language        | por (Portuguese)                                |
      | creator         | CausaGanha Project                              |
      | rights          | CC0 1.0 Universal (Public Domain)               |

  Scenario: Store Internet Archive URL in database
    Given a Parquet file has been uploaded to IA
    And the upload was successful
    When the upload completes
    Then the database should record:
      | Field              | Value                                          |
      | ia_item_id         | causaganha-TJRO-2025-01                        |
      | ia_url             | https://archive.org/details/causaganha-TJRO-2025-01 |
      | parquet_filename   | causaganha-TJRO-2025-01.parquet                |
      | tribunal           | TJRO                                           |
      | year_month         | 2025-01                                        |
      | row_count          | 3,000                                          |
      | file_size_mb       | 1.5                                            |
      | uploaded_at        | 2025-01-31 23:59:59 UTC                        |

  Scenario: Verify successful upload
    Given a Parquet file was uploaded to IA
    When the upload completes
    Then the system should verify the item exists on archive.org
    And the system should confirm the file is downloadable
    And the system should validate file size matches
    And only after verification should the upload be marked successful

  # ============================================================================
  # PARTITIONING STRATEGY
  # ============================================================================

  Scenario: Partition by tribunal and month (recommended strategy)
    Given decisions span multiple tribunals and months
    When partitions are created
    Then files should follow naming convention: "causaganha-{TRIBUNAL}-{YYYY}-{MM}.parquet"
    And each file should contain decisions for exactly one tribunal and one month
    And this enables efficient selective downloads

  Scenario: Monthly partition boundary handling
    Given today is January 31, 2025
    And there are decisions from January and February
    When the export runs
    Then January decisions should be in causaganha-TJRO-2025-01.parquet
    And February decisions should be in causaganha-TJRO-2025-02.parquet
    And no decisions should be in the wrong partition

  Scenario: Handle incomplete months
    Given it is January 15, 2025 (mid-month)
    When the export command runs
    Then it should export only complete months (December 2024 and earlier)
    And January 2025 should not be exported yet
    And a warning should indicate "January 2025 is incomplete"

  # ============================================================================
  # INCREMENTAL UPDATES
  # ============================================================================

  Scenario: Monthly export workflow
    Given it is the first day of February 2025
    And January 2025 is now complete
    When the monthly export runs
    Then all tribunals' January data should be exported
    And each should be uploaded to Internet Archive
    And local DuckDB should mark January data as archived
    And older data (> 6 months) should be purged from DuckDB

  Scenario: Backfill historical months
    Given historical data exists from June 2024 to December 2024
    And no Parquet exports have been created yet
    When the backfill export command runs
    Then 7 months × 5 tribunals = 35 Parquet files should be created
    And all should be uploaded to Internet Archive
    And the process should be resumable if interrupted

  Scenario: Avoid duplicate exports
    Given "causaganha-TJRO-2025-01.parquet" already exists on IA
    When the export command runs for "TJRO" and "2025-01"
    Then the system should check if the file already exists
    And if exists, skip the upload
    And log "Already archived: TJRO 2025-01"

  # ============================================================================
  # COMPRESSION & OPTIMIZATION
  # ============================================================================

  Scenario: Parquet compression is effective
    Given 3,000 intimations with avg texto length of 5,000 characters
    And raw JSON would be approximately 15 MB
    When the data is exported to Parquet with snappy compression
    Then the Parquet file should be approximately 1.5 MB
    And the compression ratio should be 10:1

  Scenario: Row group size optimization
    Given a large partition with 100,000 rows
    When the Parquet file is created
    Then row groups should be sized at 10,000-50,000 rows
    And this enables efficient partial reads
    And memory usage during writes should remain bounded

  Scenario: Column statistics for query optimization
    When a Parquet file is created
    Then it should include column statistics (min, max, null count)
    And these statistics enable predicate pushdown
    And queries can skip irrelevant row groups

  # ============================================================================
  # QUERY VERIFICATION
  # ============================================================================

  Scenario: Query exported Parquet locally with DuckDB
    Given a Parquet file "causaganha-TJRO-2025-01.parquet" has been downloaded
    When I query it with DuckDB:
      """
      SELECT COUNT(*) FROM 'causaganha-TJRO-2025-01.parquet'
      WHERE sigla_tribunal = 'TJRO'
      """
    Then the query should return 3,000
    And the query should complete in < 100ms (columnar efficiency)

  Scenario: Filter by date range efficiently
    Given multiple months of Parquet files exist
    When I query for decisions in Q1 2025:
      """
      SELECT * FROM 'causaganha-TJRO-2025-*.parquet'
      WHERE year = 2025 AND month IN (1, 2, 3)
      """
    Then only Q1 files should be scanned (partition pruning)
    And the query should be fast despite large dataset

  Scenario: Download only needed tribunals
    Given a researcher only needs TJSP data
    When they download "causaganha-TJSP-*.parquet" files
    Then they should only download TJSP files (~50 MB per month)
    And they should not need to download other tribunals' data
    And this selective download saves bandwidth

  # ============================================================================
  # ERROR HANDLING
  # ============================================================================

  Scenario: Handle Parquet export failures
    Given intimations are ready for export
    And disk space is insufficient
    When the export command runs
    Then the system should detect the disk space issue
    And the export should fail gracefully
    And no partial Parquet files should be uploaded to IA

  Scenario: Handle Internet Archive upload failures
    Given a Parquet file is ready for upload
    And Internet Archive returns a 503 error
    When the upload is attempted
    Then the system should retry 3 times with exponential backoff
    And if retries fail, the error should be logged
    And the file should remain locally for next attempt

  Scenario: Handle corrupted Parquet files
    Given a Parquet export produces a corrupted file
    When validation runs
    Then the corruption should be detected (file read test)
    And the corrupted file should not be uploaded
    And an error should be logged with details

  # ============================================================================
  # DATA INTEGRITY
  # ============================================================================

  Scenario: Verify exported data matches source
    Given 3,000 intimations are exported to Parquet
    When the export completes
    Then a random sample of 100 rows should be validated
    And each row in Parquet should match DuckDB source
    And mismatches should trigger an alert

  Scenario: Maintain referential integrity in denormalized data
    Given an intimation has lawyers and ratings
    When exported to Parquet
    Then all foreign key relationships should be preserved as nested data
    And queries should not require joins
    And data consistency should be maintained

  # ============================================================================
  # MONITORING & METRICS
  # ============================================================================

  Scenario: Track export metrics
    When the export process completes
    Then the following metrics should be logged:
      | Metric                      | Example Value    |
      | Tribunals exported          | 5                |
      | Total rows exported         | 15,000           |
      | Total Parquet size          | 7.5 MB           |
      | Compression ratio           | 10.2:1           |
      | Export duration             | 3m 45s           |
      | Upload duration             | 2m 10s           |
      | Files uploaded to IA        | 5                |
      | Storage cost                | $0               |

  Scenario: Alert on export failures
    Given the export process runs daily
    And the export fails for any tribunal
    When the failure is detected
    Then an alert should be sent to administrators
    And the alert should include tribunal, month, and error details
    And the alert should suggest remediation steps

  # ============================================================================
  # PUBLIC ACCESS & TRANSPARENCY
  # ============================================================================

  Scenario: Public can download Parquet files
    Given Parquet files are uploaded to Internet Archive
    When a user visits https://archive.org/details/causaganha-TJRO-2025-01
    Then they should see the Parquet file available for download
    And they should see metadata explaining the data
    And they should be able to download without authentication

  Scenario: Provide query examples for users
    Given Parquet files are public on IA
    When users access the causaganha collection
    Then they should find documentation on how to query the data
    And examples should be provided for DuckDB, Pandas, Spark
    And the documentation should explain the schema

  # ============================================================================
  # COST TRACKING
  # ============================================================================

  Scenario: Calculate storage cost savings
    Given 50,000 decisions are stored in Parquet on IA
    And the total size is 25 MB
    When compared to AWS S3 alternative
    Then IA cost should be $0
    And AWS S3 cost would be ~$5/month (storage + bandwidth)
    And annual savings should be ~$60 for MVP
    And savings should scale to $1,500-20,000/year at scale

  Scenario: Track bandwidth savings
    Given researchers download 1 GB of Parquet data per month
    When served from Internet Archive
    Then bandwidth cost is $0 (IA provides free bandwidth)
    And AWS CloudFront would cost ~$100/month
    And annual savings: ~$1,200 in bandwidth alone
