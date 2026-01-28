Feature: Internet Archive Catalog System
  As a data analyst or researcher
  I want to download a master catalog from Internet Archive
  So that I can discover what DJEN data exists and what needs to be collected

  Background:
    Given the CausaGanha catalog is hosted on Internet Archive
    And the catalog item is "causaganha-catalog"
    And the catalog contains manifest and backfill tracking files

  # ==============================================================================
  # CATALOG DOWNLOAD
  # ==============================================================================

  @catalog @download @ia
  Scenario: Download catalog from Internet Archive
    Given Internet Archive is accessible
    When I run the catalog download command
    Then the catalog files should be downloaded
    And the files should be saved to the output directory
    And total download size should be < 10 MB

  @catalog @download @cached
  Scenario: Skip download if files already exist
    Given catalog files already exist locally
    When I run the catalog download command without --force
    Then existing files should be skipped
    And a message should indicate files already exist
    And no network requests should be made for existing files

  @catalog @download @force
  Scenario: Force re-download of catalog files
    Given catalog files already exist locally
    When I run the catalog download command with --force
    Then all files should be re-downloaded
    And existing files should be overwritten

  # ==============================================================================
  # BACKFILL STATUS
  # ==============================================================================

  @catalog @backfill @status
  Scenario: Show backfill status summary
    Given catalog files are downloaded locally
    When I run the backfill-status command
    Then I should see a summary
    And I should see breakdown by tribunal

  @catalog @backfill @filter
  Scenario: Filter backfill status by tribunal
    Given catalog files are downloaded locally
    When I run the backfill-status command with --tribunal TJSP
    Then I should see only TJSP missing items
    And summary should be filtered to TJSP

  @catalog @backfill @limit
  Scenario: Limit backfill results display
    Given catalog files are downloaded locally
    When I run the backfill-status command with --limit 10
    Then only top 10 tribunals should be shown
    And a message should indicate more results are available

  # ==============================================================================
  # CATALOG QUERY
  # ==============================================================================

  @catalog @query @sql
  Scenario: Query catalog using SQL
    Given catalog files are downloaded locally
    When I run a SQL query on the catalog
    Then the query should execute successfully
    And results should be displayed in table format

  @catalog @query @format-csv
  Scenario: Export query results as CSV
    Given catalog files are downloaded locally
    When I run a SQL query with --format csv
    Then results should be output in CSV format
    And headers should be included

  @catalog @query @format-json
  Scenario: Export query results as JSON
    Given catalog files are downloaded locally
    When I run a SQL query with --format json
    Then results should be output in JSON format
    And each row should be a JSON object

  @catalog @query @limit
  Scenario: Automatic query result limiting
    Given catalog files are downloaded locally
    When I run a query without explicit LIMIT
    Then results should be automatically limited to 100 rows
    And row count should be displayed

  # ==============================================================================
  # MANIFEST STRUCTURE
  # ==============================================================================

  @catalog @manifest @structure
  Scenario: Manifest contains complete file index
    Given the manifest.parquet file exists
    When I query the manifest
    Then each record should contain required columns
    And all DJEN files on IA should be indexed

  @catalog @manifest @tribunals
  Scenario: Manifest covers all 91 tribunals
    Given the manifest.parquet file exists
    When I query distinct tribunals
    Then I should find entries for all active tribunals:
      | Category | Examples |
      | Superior | STF, STJ, TST, TSE, STM |
      | TRFs | TRF1, TRF2, TRF3, TRF4, TRF5, TRF6 |
      | TJs | TJSP, TJRJ, TJMG, TJRS, ... |
      | TRTs | TRT1, TRT2, TRT3, ... |
      | TREs | TRE-SP, TRE-RJ, TRE-MG, ... |

  # ==============================================================================
  # BACKFILL TRACKING
  # ==============================================================================

  @catalog @backfill @tracking
  Scenario: Backfill file tracks missing data
    Given the backfill-needed.parquet file exists
    When I query the backfill file
    Then each record should contain required columns
    And items should represent data not yet on IA

  @catalog @backfill @date-range
  Scenario: Backfill covers full date range
    Given DJEN started collecting data on 2024-01-01
    When I check the backfill file
    Then it should track from 2024-01-01 to today
    And weekends and holidays should be excluded

  # ==============================================================================
  # REMOTE VIEWS
  # ==============================================================================

  @catalog @views @remote
  Scenario: Catalog contains remote parquet views
    Given the catalog.duckdb file exists
    When I list views in the catalog
    Then I should find views for each table type
    And views should use read_parquet with IA URLs

  @catalog @views @query-remote
  Scenario: Query remote data through catalog views
    Given the catalog.duckdb file exists
    And Internet Archive is accessible
    When I query a remote view:
      """
      SELECT COUNT(*) FROM comunicacoes LIMIT 1
      """
    Then data should be fetched from Internet Archive
    And query should succeed

  # ==============================================================================
  # CATALOG GENERATION
  # ==============================================================================

  @catalog @generate @script
  Scenario: Generate catalog from Internet Archive items
    Given the generate_catalog.py script exists
    When I run the catalog generation script
    Then it should list all djen-* items from IA
    And it should generate manifest.parquet
    And it should generate backfill-needed.parquet
    And it should generate catalog.sql
    And it should generate catalog.duckdb

  @catalog @generate @upload
  Scenario: Upload generated catalog to Internet Archive
    Given catalog files have been generated
    When the workflow uploads to Internet Archive
    Then files should be uploaded to causaganha-catalog item
    And previous versions should be overwritten

  # ==============================================================================
  # WORKFLOW AUTOMATION
  # ==============================================================================

  @catalog @workflow @daily
  Scenario: Daily catalog update workflow
    Given the update-catalog.yml workflow exists
    When the workflow runs on schedule (6 AM UTC)
    Then it should generate fresh catalog
    And it should upload to Internet Archive
    And workflow summary should show statistics

  @catalog @workflow @manual
  Scenario: Manual catalog update trigger
    Given the update-catalog.yml workflow exists
    When triggered manually via workflow_dispatch
    Then it should run the same catalog generation
    And user can force full regeneration

  # ==============================================================================
  # CLI INTEGRATION
  # ==============================================================================

  @catalog @cli @help
  Scenario: Catalog CLI shows available commands
    When I run "causaganha catalog --help"
    Then I should see available commands:
      | Command | Description |
      | create | Create a local metadata catalog |
      | download | Download master catalog from IA |
      | backfill-status | Show what data needs to be collected |
      | query | Query the catalog using SQL |
      | list | List views in a catalog |
      | info | Show catalog information |
      | validate | Validate a catalog database |

  @catalog @cli @download-usage
  Scenario: Catalog download command usage
    When I run "causaganha catalog download --help"
    Then I should see options:
      | Option | Default | Description |
      | --output | ./causaganha-catalog | Output directory |
      | --force | false | Force re-download |

  @catalog @cli @backfill-usage
  Scenario: Backfill-status command usage
    When I run "causaganha catalog backfill-status --help"
    Then I should see options:
      | Option | Default | Description |
      | --catalog-dir | ./causaganha-catalog | Catalog location |
      | --tribunal | None | Filter by tribunal |
      | --limit | 20 | Max items to show |

  @catalog @cli @query-usage
  Scenario: Query command usage
    When I run "causaganha catalog query --help"
    Then I should see options:
      | Option | Default | Description |
      | --catalog-dir | ./causaganha-catalog | Catalog location |
      | --format | table | Output format |
      | --limit | 100 | Max rows |

  # ==============================================================================
  # ERROR HANDLING
  # ==============================================================================

  @catalog @error @not-found
  Scenario: Handle missing catalog files gracefully
    Given catalog files do not exist locally
    When I run the backfill-status command
    Then I should see an error message
    And the error should suggest running "catalog download" first

  @catalog @error @ia-unavailable
  Scenario: Handle Internet Archive unavailability
    Given Internet Archive is temporarily unavailable
    When I run the catalog download command
    Then I should see an error message
    And the error should indicate connection failure
    And existing local files should not be corrupted

  @catalog @error @invalid-query
  Scenario: Handle invalid SQL queries
    Given catalog files are downloaded locally
    When I run an invalid SQL query
    Then I should see a clear error message
    And the error should indicate what went wrong

  # ==============================================================================
  # DATA FRESHNESS
  # ==============================================================================

  @catalog @freshness @timestamp
  Scenario: Track catalog generation timestamp
    Given the catalog is generated
    Then the catalog should include generation timestamp
    And users can see when catalog was last updated

  @catalog @freshness @stale-warning
  Scenario: Warn about stale catalog
    Given the catalog was generated more than 7 days ago
    When I use the catalog
    Then I should see a warning about stale data
    And the warning should suggest running "catalog download" again
