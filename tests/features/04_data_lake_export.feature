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
  # - Partitioned by DATE (daily, all tribunals combined)
  # - ~150 MB per day (270K-450K decisions across 90 tribunals)
  # - $0 cost vs $1,500+/year on AWS S3
  # - Public download for verification and reproducibility
  # ============================================================================

  # ============================================================================
  # PARQUET EXPORT FROM DUCKDB
  # ============================================================================

  Scenario: Export single day partition to Parquet
    Given it is the end of January 15, 2025
    And there are 270,000 analyzed intimations across all tribunals on 2025-01-15
    When I run the export command for date "2025-01-15"
    Then a Parquet file should be created named "causaganha-2025-01-15.parquet"
    And the file should contain exactly 270,000 rows
    And the file should be compressed with snappy codec
    And the file size should be approximately 135 MB

  Scenario: Export includes all tribunals in single daily file
    Given there are analyzed intimations from multiple tribunals on 2025-01-15:
      | Tribunal | Count   |
      | TJSP     | 50,000  |
      | TJRJ     | 30,000  |
      | TJMG     | 25,000  |
      | TJRO     | 3,000   |
      | TJAC     | 2,000   |
    When I run the export command for date "2025-01-15"
    Then 1 Parquet file should be created: "causaganha-2025-01-15.parquet"
    And the file should contain 110,000 rows total
    And the file should include decisions from all 5 tribunals
    And users can filter by tribunal in DuckDB queries

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
      | partition_date          | DATE      | Yes      |
      | year                    | INT32     | Yes      |
      | month                   | INT32     | Yes      |
      | day                     | INT32     | Yes      |

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
    Given a Parquet file "causaganha-2025-01-15.parquet" exists locally
    And it contains 270,000 analyzed decisions from all tribunals
    When I run the archive upload command
    Then the file should be uploaded to Internet Archive
    And the item identifier should be "causaganha-2025-01-15"
    And the item URL should be "https://archive.org/details/causaganha-2025-01-15"

  Scenario: Generate comprehensive metadata for IA item
    Given a Parquet file for "2025-01-15" is being uploaded
    When the upload occurs
    Then the Internet Archive metadata should include:
      | Field           | Value                                           |
      | title           | CausaGanha - Brazilian Court Decisions - 2025-01-15 |
      | collection      | causaganha                                      |
      | mediatype       | data                                            |
      | subject         | judicial decisions; brazil; 2025-01-15          |
      | description     | Daily tabulated judicial decision data from 90 Brazilian tribunals |
      | format          | Parquet                                         |
      | coverage        | Brazil - All Tribunals                          |
      | date            | 2025-01-15                                      |
      | language        | por (Portuguese)                                |
      | creator         | CausaGanha Project                              |
      | rights          | CC0 1.0 Universal (Public Domain)               |

  Scenario: Store Internet Archive URL in database
    Given a Parquet file has been uploaded to IA
    And the upload was successful
    When the upload completes
    Then the database should record:
      | Field              | Value                                          |
      | ia_item_id         | causaganha-2025-01-15                          |
      | ia_url             | https://archive.org/details/causaganha-2025-01-15 |
      | parquet_filename   | causaganha-2025-01-15.parquet                  |
      | partition_date     | 2025-01-15                                     |
      | row_count          | 270,000                                        |
      | file_size_mb       | 135                                            |
      | uploaded_at        | 2025-01-16 01:00:00 UTC                        |

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

  Scenario: Partition by date - all tribunals combined (recommended strategy)
    Given decisions span multiple tribunals and dates
    When partitions are created
    Then files should follow naming convention: "causaganha-{YYYY}-{MM}-{DD}.parquet"
    And each file should contain decisions from ALL tribunals for that single date
    And file size should be approximately 135-150 MB per day
    And this enables daily incremental exports and manageable file sizes

  Scenario: Daily partition boundary handling
    Given decisions are collected on January 15 and January 16, 2025
    When the export runs
    Then January 15 decisions should be in causaganha-2025-01-15.parquet
    And January 16 decisions should be in causaganha-2025-01-16.parquet
    And each file should include all tribunals for that date
    And no decisions should be in the wrong partition

  Scenario: Export only complete days
    Given it is January 15, 2025 at 14:00 UTC (mid-day)
    When the export command runs
    Then it should export only complete days (January 14, 2025 and earlier)
    And January 15, 2025 should not be exported yet (day incomplete)
    And a warning should indicate "January 15, 2025 is incomplete"

  # ============================================================================
  # INCREMENTAL UPDATES
  # ============================================================================

  Scenario: Daily export workflow
    Given it is January 16, 2025 at 02:00 UTC (after midnight)
    And January 15, 2025 is now complete
    When the daily export runs
    Then all tribunals' data for 2025-01-15 should be exported
    And the file "causaganha-2025-01-15.parquet" should be uploaded to Internet Archive
    And local DuckDB should mark 2025-01-15 data as archived
    And older data (> 6 months) should be purged from DuckDB

  Scenario: Backfill historical days
    Given historical data exists from 2024-12-01 to 2024-12-31 (31 days)
    And no Parquet exports have been created yet
    When the backfill export command runs
    Then 31 Parquet files should be created (one per day)
    And all should be uploaded to Internet Archive
    And the process should be resumable if interrupted

  Scenario: Avoid duplicate exports
    Given "causaganha-2025-01-15.parquet" already exists on IA
    When the export command runs for date "2025-01-15"
    Then the system should check if the file already exists
    And if exists, skip the upload
    And log "Already archived: 2025-01-15"

  # ============================================================================
  # COMPRESSION & OPTIMIZATION
  # ============================================================================

  Scenario: Parquet compression is effective
    Given 270,000 intimations with avg texto length of 5,000 characters
    And raw JSON would be approximately 1.35 GB
    When the data is exported to Parquet with snappy compression
    Then the Parquet file should be approximately 135 MB
    And the compression ratio should be 10:1

  Scenario: Row group size optimization
    Given a daily partition with 270,000 rows
    When the Parquet file is created
    Then row groups should be sized at 50,000 rows
    And this enables efficient partial reads
    And memory usage during writes should remain bounded at ~200 MB

  Scenario: Column statistics for query optimization
    When a Parquet file is created
    Then it should include column statistics (min, max, null count)
    And these statistics enable predicate pushdown
    And queries can skip irrelevant row groups

  # ============================================================================
  # QUERY VERIFICATION
  # ============================================================================

  Scenario: Query exported Parquet locally with DuckDB
    Given a Parquet file "causaganha-2025-01-15.parquet" has been downloaded
    When I query it with DuckDB:
      """
      SELECT COUNT(*) FROM 'causaganha-2025-01-15.parquet'
      WHERE sigla_tribunal = 'TJRO'
      """
    Then the query should return ~3,000 (TJRO decisions for that day)
    And the query should complete in < 200ms (columnar efficiency with 270K rows)

  Scenario: Filter by date range efficiently
    Given daily Parquet files exist for January 2025
    When I query for decisions from Jan 1-15:
      """
      SELECT * FROM 'causaganha-2025-01-*.parquet'
      WHERE partition_date BETWEEN '2025-01-01' AND '2025-01-15'
      """
    Then only Jan 1-15 files should be scanned (partition pruning)
    And approximately 4 million rows should be returned (15 days × 270K/day)
    And the query should leverage predicate pushdown

  Scenario: Filter by specific tribunal across multiple days
    Given a researcher needs only TJSP data for January 2025
    When they download all January files and query:
      """
      SELECT * FROM 'causaganha-2025-01-*.parquet'
      WHERE sigla_tribunal = 'TJSP'
      """
    Then they need to download ~31 files × 135 MB = ~4.2 GB
    But only TJSP rows are returned (~1.5M decisions)
    And columnar format reads only needed columns efficiently

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
      | Date exported               | 2025-01-15       |
      | Tribunals included          | 90               |
      | Total rows exported         | 270,000          |
      | Total Parquet size          | 135 MB           |
      | Compression ratio           | 10.0:1           |
      | Export duration             | 8m 30s           |
      | Upload duration             | 12m 15s          |
      | Files uploaded to IA        | 1                |
      | Storage cost                | $0               |

  Scenario: Alert on export failures
    Given the export process runs daily
    And the export fails for any date
    When the failure is detected
    Then an alert should be sent to administrators
    And the alert should include date and error details
    And the alert should suggest remediation steps

  # ============================================================================
  # PUBLIC ACCESS & TRANSPARENCY
  # ============================================================================

  Scenario: Public can download Parquet files
    Given Parquet files are uploaded to Internet Archive
    When a user visits https://archive.org/details/causaganha-2025-01-15
    Then they should see the Parquet file available for download
    And they should see metadata explaining the data (90 tribunals, 270K decisions)
    And they should be able to download without authentication
    And the file size should be clearly shown (~135 MB)

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
    Given 365 days × 270K decisions/day = ~100M decisions/year are stored on IA
    And the total size is ~365 days × 135 MB = ~49 GB/year
    When compared to AWS S3 alternative
    Then IA cost should be $0
    And AWS S3 cost would be ~$150/year (storage) + $500/year (bandwidth) = $650/year
    And annual savings should be $650+ for production scale

  Scenario: Track bandwidth savings with high download volume
    Given researchers download 50 GB of Parquet data per month (frequent queries)
    When served from Internet Archive
    Then bandwidth cost is $0 (IA provides free bandwidth)
    And AWS CloudFront would cost ~$500/month for 50 GB egress
    And annual savings: ~$6,000 in bandwidth alone
