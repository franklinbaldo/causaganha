Feature: DuckDB Metadata Catalog for Remote Parquet Files
  As a data analyst or researcher
  I want a lightweight DuckDB catalog file that references remote Parquet files
  So that I can query Internet Archive data without downloading gigabytes of files

  Background:
    Given parquet files are publicly accessible on Internet Archive
    And DuckDB supports creating views that reference remote files
    And the catalog database file contains only metadata (no data)

  @catalog @metadata @distribution
  Scenario: Create metadata-only catalog database
    Given I have parquet files on Internet Archive
    And parquet files are publicly accessible on Internet Archive
    And DuckDB supports creating views that reference remote files
    And the catalog database file contains only metadata (no data)
    When I create a metadata catalog "causaganha-catalog.duckdb"
    Then the catalog file should be created
    And the catalog file size should be < 100 KB (metadata only)
    And the catalog should contain view definitions
    And the catalog should NOT contain any actual data rows

  @catalog @views @remote-access
  Scenario: Catalog exposes views to remote parquet files
    Given a metadata catalog "causaganha-catalog.duckdb" exists
    When I create base views in the catalog
    Then the catalog should contain 3 view definitions
    And each view should reference external parquet files
    And querying a view should fetch data from Internet Archive
    And the catalog file size should remain < 100 KB

  @catalog @analytical-views
  Scenario: Catalog includes curated analytical views
    Given a metadata catalog with base views exists
    When I create analytical views
    Then the catalog should contain 3 analytical views
    And each analytical view should reference base views
    And users can query analytical views without writing SQL
    And all queries fetch fresh data from Internet Archive

  @catalog @user-experience
  Scenario: Users query catalog with zero setup
    Given a catalog file "causaganha-catalog.duckdb" is distributed
    When a user downloads the catalog file (< 100 KB)
    And the user opens the catalog in DuckDB
    Then the query should execute successfully
    And data should be fetched from Internet Archive
    And the user should get results without downloading parquet files
    And the user should not need any configuration

  @catalog @versioning
  Scenario: Create versioned catalog snapshots
    Given parquet files are updated monthly on Internet Archive
    When I create versioned catalogs
    Then 3 catalog files should be created
    And each catalog should reference specific month's data
    And "causaganha-latest.duckdb" should always point to newest parquet
    And users can choose between specific months or latest

  @catalog @read-only @security
  Scenario: Catalog distributed as read-only for security
    Given a catalog file is created
    When I set read-only mode on the catalog
    And a user opens the catalog
    Then users can query views
    But users cannot modify views
    And users cannot drop views
    And users cannot alter the catalog
    And this prevents accidental corruption

  @catalog @hybrid @offline-mode
  Scenario: Support hybrid online/offline catalogs
    Given users may want offline access to data
    When I create a hybrid catalog that supports:
      | Mode | View Pattern | Use Case |
      | Online | read_parquet('https://archive.org/download/*.parquet') | Fresh data, no downloads |
      | Offline | read_parquet('data/local/*.parquet') | No internet, fast queries |
    Then users can switch modes by downloading parquet locally
    And the same SQL queries work in both modes
    And documentation explains both patterns

  @catalog @schema-documentation
  Scenario: Catalog includes schema documentation
    Given a catalog file is created
    When I add schema documentation:
      | View | Columns | Description |
      | intimations_raw | numero_processo, data_disponibilizacao, sigla_tribunal, tipo_comunicacao | Raw DJEN intimation data |
      | lawyers_raw | oab_number, lawyer_name, rating, win_rate, total_cases | Lawyer profiles and ratings |
      | top_lawyers | Same as lawyers_raw | Filtered to lawyers with 10+ cases, top 100 by rating |
    Then users can introspect the schema:
      ```sql
      DESCRIBE intimations_raw;
      SHOW TABLES;
      ```
    And documentation is embedded in the catalog

  @catalog @complex-views @joins
  Scenario: Catalog exposes complex analytical views with joins
    Given a catalog with base views exists
    When I create a complex view "lawyer_performance":
      ```sql
      CREATE VIEW lawyer_performance AS
      SELECT
        l.oab_number,
        l.lawyer_name,
        l.rating,
        l.win_rate,
        COUNT(DISTINCT i.numero_processo) as total_cases,
        AVG(i.confidence_score) as avg_confidence
      FROM lawyers_raw l
      LEFT JOIN intimations_raw i
        ON l.oab_number = i.winner_lawyer_oab
      WHERE l.total_cases >= 5
      GROUP BY l.oab_number, l.lawyer_name, l.rating, l.win_rate
      ORDER BY l.rating DESC
      ```
    Then the view should join multiple remote parquet files
    And querying the view should work seamlessly
    And DuckDB should optimize the join execution
    And results should include lawyer stats with case data

  @catalog @performance @caching
  Scenario: DuckDB caches remote parquet for performance
    Given a catalog references remote parquet files
    When a user runs the same query twice:
      ```sql
      SELECT COUNT(*) FROM intimations_raw WHERE sigla_tribunal = 'TST'
      ```
    Then the first query should download data from Internet Archive
    And the second query should use DuckDB's HTTP cache
    And the second query should be significantly faster
    And users benefit from automatic caching

  @catalog @distribution @github-releases
  Scenario: Distribute catalog via GitHub releases
    Given a catalog file "causaganha-catalog.duckdb" is created
    When I publish a GitHub release
    Then the catalog should be attached as a release asset
    And users can download directly from GitHub
    And the download URL should be stable
    And file size should be < 100 KB (fast download)
    And release notes should include:
      | Section | Content |
      | What's New | Views included, data coverage dates |
      | Usage | Python/SQL query examples |
      | Data Sources | Links to Internet Archive parquet files |

  @catalog @cli @generation
  Scenario: Generate catalog via CLI command
    Given the causaganha CLI is installed
    When I run the catalog generation command
    Then a catalog file should be created
    And the catalog should reference January 2026 parquet files
    And the catalog should include specified analytical views
    And success message should show file size and views created

  @catalog @cli @listing
  Scenario: List views in existing catalog
    Given a catalog "causaganha-catalog.duckdb" exists
    When I run:
      ```bash
      causaganha catalog list causaganha-catalog.duckdb
      ```
    Then I should see a list of all views:
      | View Name | Type | Rows (Estimated) |
      | intimations_raw | Base | N/A (Remote) |
      | lawyers_raw | Base | N/A (Remote) |
      | partes_raw | Base | N/A (Remote) |
      | top_lawyers | Analytical | N/A (Remote) |
      | recent_intimations | Analytical | N/A (Remote) |
      | tribunal_stats | Analytical | N/A (Remote) |

  @catalog @validation
  Scenario: Validate catalog creation
    Given a catalog is being created
    When the creation process runs
    Then it should validate:
      | Validation | Check |
      | Remote URLs are accessible | HTTP HEAD request to each parquet |
      | View SQL is syntactically correct | DuckDB parse check |
      | No circular view dependencies | Dependency graph analysis |
      | File size stays < 100 KB | Size check after creation |
    And any validation failures should abort catalog creation
    And clear error messages should guide troubleshooting

  @catalog @documentation @examples
  Scenario: Include usage examples in catalog metadata
    Given a catalog file is created
    When I embed example queries in catalog:
      | Example | Query |
      | Count intimations | SELECT COUNT(*) FROM intimations_raw |
      | Top 10 lawyers | SELECT * FROM top_lawyers LIMIT 10 |
      | Recent activity | SELECT * FROM recent_intimations LIMIT 100 |
    Then users can discover examples via:
      ```sql
      SELECT * FROM duckdb_views() WHERE schema_name = 'main'
      ```
    And documentation table should exist with examples

  @catalog @automation @scheduled
  Scenario: Automate weekly catalog generation
    Given new parquet files are uploaded to IA weekly
    When I set up automated catalog generation:
      | Schedule | Action |
      | Every Monday 2 AM UTC | Generate causaganha-latest.duckdb |
      | Every 1st of month | Generate causaganha-YYYY-MM.duckdb |
    Then catalogs should be auto-generated on schedule
    And catalogs should be uploaded to GitHub releases
    And users always have access to latest metadata catalog

  @catalog @error-handling
  Scenario: Handle remote parquet unavailability gracefully
    Given a catalog references a remote parquet file
    And the remote file becomes temporarily unavailable
    When a user queries the view
    Then DuckDB should return a clear error message
    And the error should indicate which remote file is unavailable
    And the error should suggest checking internet connection
    And the catalog itself should remain valid

  @catalog @export @local-cache
  Scenario: Export catalog results to local parquet for caching
    Given a user runs an expensive query on remote data
    When the user wants to cache results locally:
      ```sql
      COPY (
        SELECT * FROM lawyer_performance WHERE rating > 1500
      ) TO 'high_rated_lawyers.parquet' (FORMAT PARQUET)
      ```
    Then DuckDB should stream results to local file
    And only the result set should be downloaded (not all source data)
    And the user can query the local cache for fast repeated access
    And local cache can be refreshed by re-running the query

  @catalog @multi-tribunal @selective-access
  Scenario: Create tribunal-specific catalogs
    Given different users may only need specific tribunals
    When I create tribunal-specific catalogs:
      | Catalog Name | Tribunal Filter |
      | causaganha-tst-catalog.duckdb | TST only |
      | causaganha-tjro-catalog.duckdb | TJRO only |
      | causaganha-superior-catalog.duckdb | TST, STJ, STF |
      | causaganha-all-catalog.duckdb | All tribunals |
    Then each catalog should reference only relevant parquet files
    And smaller catalogs should reduce query scope
    And users download only catalogs they need

  @catalog @comparison @traditional-db
  Scenario: Compare catalog approach to traditional database
    Given I compare catalog vs traditional database
    When evaluating metrics:
      | Metric | Metadata Catalog | Traditional DB |
      | Setup time | Instant (download 100 KB) | Hours (load 50 GB) |
      | Storage needed | 0 GB (remote data) | 50 GB (local copy) |
      | Data freshness | Always latest (IA) | Stale (manual sync) |
      | Distribution | 100 KB file | 50 GB dump |
      | Query speed | Medium (network) | Fast (local) |
      | Maintenance | None | Regular updates |
    Then metadata catalog wins on:
      | Benefit |
      | Zero local storage |
      | Instant setup |
      | Always fresh data |
      | Easy distribution |
    And traditional DB wins on:
      | Benefit |
      | Faster repeated queries |
      | Offline access |

  @catalog @integration @data-pipeline
  Scenario: Integrate catalog generation into data pipeline
    Given the data pipeline uploads parquet to IA
    When the pipeline completes successfully:
      | Step | Action |
      | 1. Upload parquet | Files to Internet Archive |
      | 2. Generate catalog | Create metadata catalog |
      | 3. Validate catalog | Test queries work |
      | 4. Publish catalog | Upload to GitHub releases |
    Then catalog generation should be part of the pipeline
    And each parquet upload should trigger catalog regeneration
    And users always have matching catalog and parquet versions

  @catalog @monitoring @health-check
  Scenario: Monitor catalog health and validity
    Given catalogs are distributed to users
    When I implement health checks:
      | Check | Validation |
      | Views are queryable | Run sample query on each view |
      | Remote files accessible | HTTP HEAD on each parquet URL |
      | File size reasonable | Check < 100 KB threshold |
      | Last update timestamp | Track when catalog was generated |
    Then health checks should run daily
    And failures should trigger alerts
    And stale catalogs (> 7 days old) should be flagged
