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
  # - Partitioned by DATE (daily) then sub-partitioned by TRIBUNAL
  # - Naming: causaganha-{YYYY}-{MM}-{DD}-{TRIBUNAL}.parquet
  # - File sizes: 1-50 MB per file (tribunal-dependent)
  # - ~90 files per day (one per tribunal) = 32,850 files/year
  # - $0 cost vs $1,500+/year on AWS S3
  # - Public download for verification and reproducibility
  # ============================================================================

  # ============================================================================
  # PARQUET EXPORT FROM DUCKDB
  # ============================================================================

  Scenario: Export single day partition for one tribunal
    Given it is the end of January 15, 2025
    And there are 3,000 analyzed intimations for "TJRO" on 2025-01-15
    When I run the export command for date "2025-01-15" and tribunal "TJRO"
    Then a Parquet file should be created named "causaganha-2025-01-15-TJRO.parquet"
    And the file should contain exactly 3,000 rows
    And the file should be compressed with snappy codec
    And the file size should be approximately 1.5 MB

  Scenario: Export creates separate files per tribunal (hierarchical partitioning)
    Given there are analyzed intimations from multiple tribunals on 2025-01-15:
      | Tribunal | Count   |
      | TJSP     | 50,000  |
      | TJRJ     | 30,000  |
      | TJMG     | 25,000  |
      | TJRO     | 3,000   |
      | TJAC     | 2,000   |
    When I run the export command for date "2025-01-15"
    Then 5 Parquet files should be created:
      | Filename                             | Rows   | Size   |
      | causaganha-2025-01-15-TJSP.parquet  | 50,000 | ~25 MB |
      | causaganha-2025-01-15-TJRJ.parquet  | 30,000 | ~15 MB |
      | causaganha-2025-01-15-TJMG.parquet  | 25,000 | ~12 MB |
      | causaganha-2025-01-15-TJRO.parquet  | 3,000  | ~1.5MB |
      | causaganha-2025-01-15-TJAC.parquet  | 2,000  | ~1 MB  |
    And each file contains only decisions from its respective tribunal
    And users can selectively download only needed tribunals

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
    Given a Parquet file "causaganha-2025-01-15-TJRO.parquet" exists locally
    And it contains 3,000 analyzed decisions from TJRO
    When I run the archive upload command
    Then the file should be uploaded to Internet Archive
    And the item identifier should be "causaganha-2025-01-15-TJRO"
    And the item URL should be "https://archive.org/details/causaganha-2025-01-15-TJRO"

  Scenario: Generate comprehensive metadata for IA item
    Given a Parquet file for "TJRO" on "2025-01-15" is being uploaded
    When the upload occurs
    Then the Internet Archive metadata should include:
      | Field           | Value                                           |
      | title           | CausaGanha - TJRO - 2025-01-15                  |
      | collection      | causaganha                                      |
      | mediatype       | data                                            |
      | subject         | judicial decisions; brazil; TJRO; 2025-01-15    |
      | description     | Daily judicial decision data from TJRO for January 15, 2025 |
      | format          | Parquet                                         |
      | coverage        | TJRO (Tribunal de Justiça de Rondônia)          |
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
      | ia_item_id         | causaganha-2025-01-15-TJRO                     |
      | ia_url             | https://archive.org/details/causaganha-2025-01-15-TJRO |
      | parquet_filename   | causaganha-2025-01-15-TJRO.parquet             |
      | tribunal           | TJRO                                           |
      | partition_date     | 2025-01-15                                     |
      | row_count          | 3,000                                          |
      | file_size_mb       | 1.5                                            |
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

  Scenario: Hierarchical partitioning - date then tribunal (recommended strategy)
    Given decisions span multiple tribunals and dates
    When partitions are created
    Then files should follow naming convention: "causaganha-{YYYY}-{MM}-{DD}-{TRIBUNAL}.parquet"
    And each file should contain decisions for ONE tribunal on ONE date
    And file sizes should vary by tribunal: 1-50 MB per file
    And this enables selective downloads by tribunal or date
    And approximately 90 files per day (one per tribunal)

  Scenario: Daily partition boundary handling with tribunal sub-partitions
    Given decisions are collected from TJRO on January 15 and January 16, 2025
    When the export runs
    Then January 15 TJRO decisions should be in causaganha-2025-01-15-TJRO.parquet
    And January 16 TJRO decisions should be in causaganha-2025-01-16-TJRO.parquet
    And decisions from TJSP on Jan 15 should be in causaganha-2025-01-15-TJSP.parquet
    And no decisions should be in the wrong partition

  Scenario: Export only complete days
    Given it is January 15, 2025 at 14:00 UTC (mid-day)
    When the export command runs
    Then it should export only complete days (January 14, 2025 and earlier)
    And it should create ~90 files for January 14 (one per tribunal)
    And January 15, 2025 should not be exported yet (day incomplete)
    And a warning should indicate "January 15, 2025 is incomplete"

  # ============================================================================
  # INCREMENTAL UPDATES
  # ============================================================================

  Scenario: Daily export workflow with tribunal sub-partitions
    Given it is January 16, 2025 at 02:00 UTC (after midnight)
    And January 15, 2025 is now complete
    When the daily export runs
    Then all tribunals' data for 2025-01-15 should be exported
    And approximately 90 files should be created (one per tribunal)
    And files should be named causaganha-2025-01-15-{TRIBUNAL}.parquet
    And all files should be uploaded to Internet Archive
    And local DuckDB should mark 2025-01-15 data as archived
    And older data (> 6 months) should be purged from DuckDB

  Scenario: Backfill historical days creates tribunal sub-partitions
    Given historical data exists from 2024-12-01 to 2024-12-31 (31 days)
    And data spans 5 active tribunals (TJRO, TJAC, TJSP, TJRJ, TJMG)
    And no Parquet exports have been created yet
    When the backfill export command runs
    Then 31 days × 5 tribunals = 155 Parquet files should be created
    And all should be uploaded to Internet Archive
    And the process should be resumable if interrupted

  Scenario: Avoid duplicate exports per tribunal
    Given "causaganha-2025-01-15-TJRO.parquet" already exists on IA
    When the export command runs for date "2025-01-15" and tribunal "TJRO"
    Then the system should check if the file already exists
    And if exists, skip the upload
    And log "Already archived: 2025-01-15 TJRO"

  # ============================================================================
  # COMPRESSION & OPTIMIZATION
  # ============================================================================

  Scenario: Parquet compression is effective per tribunal
    Given 3,000 TJRO intimations with avg texto length of 5,000 characters
    And raw JSON would be approximately 15 MB
    When the data is exported to Parquet with snappy compression
    Then the Parquet file should be approximately 1.5 MB
    And the compression ratio should be 10:1

  Scenario: Row group size optimization for variable-sized partitions
    Given a TJSP partition with 50,000 rows
    When the Parquet file is created
    Then row groups should be sized at 10,000-20,000 rows
    And this enables efficient partial reads
    And memory usage during writes should remain bounded at ~50 MB per file

  Scenario: Column statistics for query optimization
    When a Parquet file is created
    Then it should include column statistics (min, max, null count)
    And these statistics enable predicate pushdown
    And queries can skip irrelevant row groups

  # ============================================================================
  # QUERY VERIFICATION
  # ============================================================================

  Scenario: Query single tribunal partition with DuckDB
    Given a Parquet file "causaganha-2025-01-15-TJRO.parquet" has been downloaded
    When I query it with DuckDB:
      """
      SELECT COUNT(*) FROM 'causaganha-2025-01-15-TJRO.parquet'
      """
    Then the query should return 3,000 (all TJRO decisions for that day)
    And the query should complete in < 50ms (small file, columnar efficiency)

  Scenario: Filter by date range for specific tribunal (selective download)
    Given a researcher needs only TJRO data for January 2025
    When they download only TJRO files:
      """
      causaganha-2025-01-*-TJRO.parquet (31 files)
      """
    And query with DuckDB:
      """
      SELECT * FROM 'causaganha-2025-01-*-TJRO.parquet'
      WHERE partition_date BETWEEN '2025-01-01' AND '2025-01-15'
      """
    Then they download only 31 × 1.5 MB = ~47 MB (TJRO only)
    And approximately 90,000 TJRO decisions are returned (15 days × 3K/day)
    And they did NOT need to download other tribunals' data

  Scenario: Query across all tribunals for specific date
    Given a researcher needs all tribunals for January 15, 2025
    When they download all files for that date:
      """
      causaganha-2025-01-15-*.parquet (~90 files)
      """
    And query with DuckDB:
      """
      SELECT * FROM 'causaganha-2025-01-15-*.parquet'
      """
    Then they download ~90 files totaling ~135 MB
    And approximately 270,000 decisions are returned (all tribunals)
    And columnar format enables efficient filtering

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

  Scenario: Track export metrics with tribunal sub-partitions
    When the export process completes for 2025-01-15
    Then the following metrics should be logged:
      | Metric                      | Example Value    |
      | Date exported               | 2025-01-15       |
      | Tribunals included          | 90               |
      | Total rows exported         | 270,000          |
      | Total Parquet size          | 135 MB           |
      | Compression ratio           | 10.0:1           |
      | Export duration             | 5m 15s           |
      | Upload duration             | 8m 45s           |
      | Files uploaded to IA        | 90               |
      | Storage cost                | $0               |

  Scenario: Alert on export failures per tribunal
    Given the export process runs daily
    And the export fails for tribunal "TJSP" on date "2025-01-15"
    When the failure is detected
    Then an alert should be sent to administrators
    And the alert should include date, tribunal, and error details
    And the alert should suggest remediation steps
    And other tribunal exports should continue (isolated failures)

  # ============================================================================
  # PUBLIC ACCESS & TRANSPARENCY
  # ============================================================================

  Scenario: Public can download Parquet files by tribunal
    Given Parquet files are uploaded to Internet Archive
    When a user visits https://archive.org/details/causaganha-2025-01-15-TJRO
    Then they should see the Parquet file available for download
    And they should see metadata explaining the data (TJRO, 3K decisions, Jan 15)
    And they should be able to download without authentication
    And the file size should be clearly shown (~1.5 MB)
    And they can browse other tribunals' files for the same date

  Scenario: Provide query examples for users
    Given Parquet files are public on IA
    When users access the causaganha collection
    Then they should find documentation on how to query the data
    And examples should be provided for DuckDB, Pandas, Spark
    And the documentation should explain the schema

  # ============================================================================
  # COST TRACKING
  # ============================================================================

  Scenario: Calculate storage cost savings with tribunal partitions
    Given 365 days × 90 tribunals = 32,850 files/year are stored on IA
    And 365 days × 270K decisions/day = ~100M decisions/year
    And the total size is ~49 GB/year (varies by tribunal)
    When compared to AWS S3 alternative
    Then IA cost should be $0
    And AWS S3 cost would be ~$150/year (storage) + $500/year (bandwidth) = $650/year
    And annual savings should be $650+ for production scale
    And file management is simpler than millions of destinatário files

  Scenario: Track bandwidth savings with high download volume
    Given researchers download 50 GB of Parquet data per month (frequent queries)
    When served from Internet Archive
    Then bandwidth cost is $0 (IA provides free bandwidth)
    And AWS CloudFront would cost ~$500/month for 50 GB egress
    And annual savings: ~$6,000 in bandwidth alone
