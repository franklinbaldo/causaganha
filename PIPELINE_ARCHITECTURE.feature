Feature: CausaGanha Data Pipeline Architecture
  As a platform operator
  I want the data pipeline to efficiently collect, consolidate, and embed judicial data
  So that the catalog stays current with minimal resource waste

  Background:
    Given the pipeline runs every 5-10 minutes
    And only one workflow instance can run at a time (global lock)
    And all independent jobs run in parallel within a single workflow

  # ============================================================================
  # PARALLEL EXECUTION LAYER (Runs simultaneously)
  # ============================================================================

  Scenario: Collect DJEN Data checks for new data and exits quickly if none exists
    Given the COLLECT job starts
    When COLLECT checks if new DJEN data exists on DJEN API (not yet on IA)
    Then COLLECT should complete in less than 5 seconds
    And COLLECT sets outputs.files_added = false
    And COLLECT exits

  Scenario: Collect DJEN Data downloads and uploads new data
    Given the COLLECT job starts
    And new DJEN data exists on DJEN API for today
    When COLLECT downloads ZIPs from DJEN
    And COLLECT uploads ZIPs to Internet Archive
    Then COLLECT sets outputs.files_added = true
    And COLLECT completes successfully

  Scenario: Consolidate Parquet checks for complete days and exits if none ready
    Given the CONSOLIDATE job starts
    And today's ZIPs are incomplete (not all 91 tribunals collected yet)
    When CONSOLIDATE checks if any complete day exists on IA
    Then CONSOLIDATE should complete in less than 5 seconds
    And CONSOLIDATE sets outputs.files_added = false
    And CONSOLIDATE exits

  Scenario: Consolidate Parquet converts complete days to Parquet
    Given the CONSOLIDATE job starts
    And a complete day's worth of ZIPs exists on IA (all 91 tribunals)
    And this day has NOT been consolidated yet
    When CONSOLIDATE downloads the day's ZIPs from IA
    And CONSOLIDATE converts ZIPs to Parquet format
    And CONSOLIDATE uploads Parquet files to IA
    Then CONSOLIDATE sets outputs.files_added = true
    And CONSOLIDATE completes successfully

  Scenario: Consolidate Parquet skips already-consolidated days
    Given the CONSOLIDATE job starts
    And a complete day exists on IA
    And this day's Parquet files already exist on IA
    When CONSOLIDATE checks the day
    Then CONSOLIDATE skips it
    And no work is performed

  Scenario: Embed generates embeddings only for new decisions
    Given the EMBED job starts
    And new Parquet decisions exist without embeddings
    When EMBED generates vector embeddings
    And EMBED stores embeddings in DuckDB
    And EMBED uploads embeddings to IA
    Then EMBED sets outputs.files_added = true
    And EMBED completes successfully

  Scenario: Embed exits quickly when all decisions already embedded
    Given the EMBED job starts
    And all Parquet decisions already have embeddings
    When EMBED checks for unembedded decisions
    Then EMBED should complete in less than 5 seconds
    And EMBED sets outputs.files_added = false
    And EMBED exits

  # ============================================================================
  # CONDITIONAL CATALOG LAYER (Runs only if needed)
  # ============================================================================

  Scenario: Catalog rebuilds when any job added new files
    Given COLLECT, CONSOLIDATE, and EMBED jobs have completed
    And at least one job has outputs.files_added = true
    When the pipeline evaluates the condition
    Then CATALOG job is triggered
    And CATALOG rebuilds the master index on Internet Archive
    And CATALOG updates manifest.parquet
    And CATALOG completes successfully

  Scenario: Catalog is skipped when no jobs added files
    Given COLLECT, CONSOLIDATE, and EMBED jobs have completed
    And all jobs have outputs.files_added = false
    When the pipeline evaluates the condition
    Then CATALOG job is skipped
    And no unnecessary work is performed
    And pipeline completes faster

  Scenario: Catalog detects what changed on Internet Archive
    Given CATALOG job runs
    And new files exist on Internet Archive that aren't in old manifest
    When CATALOG rebuilds the manifest
    Then CATALOG sets outputs.catalog_updated = true
    And manifest.parquet is updated with new files

  # ============================================================================
  # DASHBOARD CACHE LAYER (Depends on Catalog)
  # ============================================================================

  Scenario: Dashboard cache updates when catalog changed
    Given CATALOG job has completed
    And CATALOG.outputs.catalog_updated = true
    When the pipeline evaluates the condition
    Then DASHBOARD-CACHE job is triggered
    And DASHBOARD-CACHE regenerates dashboard data from manifest.parquet
    And DASHBOARD-CACHE completes successfully

  Scenario: Dashboard cache is skipped when catalog unchanged
    Given CATALOG job has completed
    And CATALOG.outputs.catalog_updated = false
    When the pipeline evaluates the condition
    Then DASHBOARD-CACHE job is skipped
    And no unnecessary dashboard regeneration occurs

  # ============================================================================
  # CONCURRENT EXECUTION
  # ============================================================================

  Scenario: All three independent jobs run simultaneously
    Given a workflow starts
    When COLLECT, CONSOLIDATE, and EMBED jobs are triggered
    Then all three jobs start at approximately the same time
    And all three jobs execute in parallel
    And the total workflow time = max(collect_time, consolidate_time, embed_time)
    And NOT sum of individual times

  Scenario: Next workflow waits for previous one to complete
    Given workflow #1 is currently running
    When the next scheduled trigger fires (5-10 minutes)
    Then workflow #2 is queued as pending
    And workflow #2 waits for workflow #1 to fully complete (including CATALOG)
    And workflow #2 starts only after workflow #1 is completely finished
    And no two workflows execute simultaneously

  # ============================================================================
  # PERFORMANCE TARGETS
  # ============================================================================

  Scenario: Idle pipeline completes in seconds
    Given no new data exists on DJEN
    And all data is already consolidated
    And all decisions already have embeddings
    When the full pipeline runs
    Then COLLECT exits in < 5 seconds
    And CONSOLIDATE exits in < 5 seconds
    And EMBED exits in < 5 seconds
    And CATALOG is skipped
    And DASHBOARD-CACHE is skipped
    And total runtime < 20 seconds

  Scenario: Active pipeline completes within timeout
    Given new DJEN data exists
    And consolidation is needed
    And embeddings are being generated
    When the full pipeline runs
    Then each job completes within its timeout (25 minutes)
    And CATALOG runs after all three jobs finish
    And DASHBOARD-CACHE runs if CATALOG updated
    And total runtime < 25 minutes

  # ============================================================================
  # ERROR HANDLING
  # ============================================================================

  Scenario: Failed job blocks dependent jobs
    Given COLLECT completes successfully
    And CONSOLIDATE fails
    And EMBED completes successfully
    When checking CATALOG eligibility
    Then the failed CONSOLIDATE doesn't prevent CATALOG from running
    And CATALOG still runs because other jobs succeeded
    And CATALOG still sets outputs.catalog_updated correctly

  Scenario: One job failure doesn't block other parallel jobs
    Given COLLECT fails
    When CONSOLIDATE and EMBED are running
    Then CONSOLIDATE and EMBED continue executing
    And they are NOT blocked by COLLECT's failure
    And the pipeline continues to completion

