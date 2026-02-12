Feature: Pipeline Orchestration
  As a developer
  I want a single Python script to orchestrate the data pipeline
  So that GitHub Actions YAML stays minimal and I can debug locally

  Background:
    Given a default pipeline configuration

  # ==============================================================================
  # TIER 1: END-TO-END PIPELINE BEHAVIOR
  # ==============================================================================

  @pipeline @e2e
  Scenario: Full pipeline plans all initial steps then conditional steps
    Given a config with job "all"
    When I plan the initial steps
    Then I should get 3 step plans
    And step plan 0 should have name "collect"
    And step plan 1 should have name "consolidate"
    And step plan 2 should have name "embed"
    And each step plan should have a non-empty command tuple

  @pipeline @e2e
  Scenario: Catalog only triggers when files were added
    Given a config with job "all"
    And a pipeline state with files_added true and catalog_updated false
    When I plan the catalog step
    Then I should get 1 step plans
    And step plan 0 should have name "catalog"

  @pipeline @e2e
  Scenario: Dashboard only triggers when catalog was updated
    Given a config with job "all"
    And a pipeline state with files_added true and catalog_updated true
    When I plan the dashboard step
    Then I should get 1 step plans
    And step plan 0 should have name "dashboard"

  @pipeline @e2e
  Scenario: Nothing cascades when no files produced
    Given a config with job "all"
    And a pipeline state with files_added false and catalog_updated false
    When I plan the catalog step
    Then I should get 1 step plans
    And step plan 0 should have name "catalog"

  @pipeline @e2e
  Scenario: Single job only runs that step
    Given a config with job "embed"
    When I plan the initial steps
    Then I should get 1 step plans

  # ==============================================================================
  # TIER 2: CONDITIONAL LOGIC
  # ==============================================================================

  @pipeline @conditional
  Scenario: Catalog runs when files were added
    When I check should_run_catalog with job "all" and files_added true
    Then the decision should be true

  @pipeline @conditional
  Scenario: Catalog always runs for job all
    When I check should_run_catalog with job "all" and files_added false
    Then the decision should be true

  @pipeline @conditional
  Scenario: Catalog runs when explicitly requested
    When I check should_run_catalog with job "catalog" and files_added false
    Then the decision should be true

  @pipeline @conditional
  Scenario: Dashboard runs when catalog was updated
    When I check should_run_dashboard with job "all" and catalog_updated true
    Then the decision should be true

  @pipeline @conditional
  Scenario: Dashboard always runs for job all
    When I check should_run_dashboard with job "all" and catalog_updated false
    Then the decision should be true

  @pipeline @conditional
  Scenario: Dashboard runs when explicitly requested
    When I check should_run_dashboard with job "dashboard" and catalog_updated false
    Then the decision should be true

  @pipeline @conditional
  Scenario: Plan catalog step always runs for job all
    Given a config with job "all"
    And a pipeline state with files_added false and catalog_updated false
    When I plan the catalog step
    Then I should get 1 step plans
    And step plan 0 should have name "catalog"

  @pipeline @conditional
  Scenario: Plan dashboard step always runs for job all
    Given a config with job "all"
    And a pipeline state with files_added true and catalog_updated false
    When I plan the dashboard step
    Then I should get 1 step plans
    And step plan 0 should have name "dashboard"

  # ==============================================================================
  # TIER 3: STATE TRANSITIONS
  # ==============================================================================

  @pipeline @state
  Scenario: Empty initial state
    When I create an empty pipeline state
    Then the state should have 0 results
    And the state files_added should be false
    And the state catalog_updated should be false

  @pipeline @state
  Scenario: Update state with files_added result
    Given an empty pipeline state
    And a step result named "collect" with output key "files_added" and value "true"
    When I update the state with the result
    Then the state should have 1 results
    And the state files_added should be true
    And the state catalog_updated should be false

  @pipeline @state
  Scenario: Update state with catalog_updated result
    Given an empty pipeline state
    And a step result named "catalog" with output key "catalog_updated" and value "true"
    When I update the state with the result
    Then the state should have 1 results
    And the state files_added should be false
    And the state catalog_updated should be true

  @pipeline @state
  Scenario: State accumulates multiple results
    Given an empty pipeline state
    And a step result named "collect" with output key "files_added" and value "true"
    When I update the state with the result
    And I add another result named "consolidate" with output key "files_added" and value "false"
    Then the state should have 2 results
    And the state files_added should be true

  @pipeline @state
  Scenario: State preserves files_added across updates
    Given an empty pipeline state
    And a step result named "collect" with output key "files_added" and value "true"
    When I update the state with the result
    And I add another result named "embed" with output key "files_added" and value "false"
    Then the state files_added should be true

  @pipeline @state
  Scenario: No failures in empty state
    When I create an empty pipeline state
    And I check for failures
    Then the failure check should be false

  @pipeline @state
  Scenario: Detect failure when a step failed
    Given a state with one failed step
    When I check for failures
    Then the failure check should be true

  @pipeline @state
  Scenario: No failure when all steps succeed
    Given a state with one successful step
    When I check for failures
    Then the failure check should be false

  # ==============================================================================
  # TIER 4: STEP PLANNING
  # ==============================================================================

  @pipeline @planning
  Scenario: Filter initial steps for job all
    When I filter initial steps for job "all"
    Then the filtered steps should be collect, consolidate, embed

  @pipeline @planning
  Scenario: Filter initial steps for single job collect
    When I filter initial steps for job "collect"
    Then the filtered steps should be collect

  @pipeline @planning
  Scenario: Filter initial steps for single job consolidate
    When I filter initial steps for job "consolidate"
    Then the filtered steps should be consolidate

  @pipeline @planning
  Scenario: Filter initial steps for single job embed
    When I filter initial steps for job "embed"
    Then the filtered steps should be embed

  @pipeline @planning
  Scenario: Filter initial steps returns empty for catalog
    When I filter initial steps for job "catalog"
    Then there should be no filtered steps

  @pipeline @planning
  Scenario: Filter initial steps returns empty for dashboard
    When I filter initial steps for job "dashboard"
    Then there should be no filtered steps

  # ==============================================================================
  # TIER 5: COMMAND BUILDING
  # ==============================================================================

  @pipeline @command
  Scenario: Build collect command with date and tribunal
    Given a config with date "2026-01-15" and tribunal "TJSP"
    When I build the collect command
    Then the command should include flag "--proxy-url"
    And the command should include flag "--date" with value "2026-01-15"
    And the command should include flag "--tribunal" with value "TJSP"
    And the command should include flag "--max-items" with value "10000"
    And the command should include flag "--workers" with value "64"
    And the command should include flag "--deadline" with value "1200s"

  @pipeline @command
  Scenario: Build collect command without optional params
    Given a config with no date and no tribunal
    When I build the collect command
    Then the command should include flag "--proxy-url"
    And the command should not include flag "--date"
    And the command should not include flag "--tribunal"

  @pipeline @command
  Scenario: Build consolidate command with specific date
    Given a config with date "2026-01-15" and no tribunal
    When I build the consolidate command
    Then the command should include flag "--date" with value "2026-01-15"
    And the command should not include flag "--backfill"
    And the command should include flag "--deadline" with value "1200s"
    And the command should include flag "--workers" with value "32"

  @pipeline @command
  Scenario: Build consolidate command in backfill mode
    Given a config with no date and no tribunal
    When I build the consolidate command
    Then the command should include flag "--backfill"
    And the command should include flag "--force"
    And the command should not include flag "--date"

  @pipeline @command
  Scenario: Build embed command
    When I build the embed command
    Then the command should include flag "--deadline" with value "10m"
    And the command should include flag "--max-decisions" with value "500"

  @pipeline @command
  Scenario: Build catalog command
    When I build the catalog command
    Then the command should include substring "generate_catalog.py"
    And the command should include flag "--upload"

  @pipeline @command
  Scenario: Build dashboard command
    When I build the dashboard command
    Then the command should include substring "generate_dashboard_cache.py"

  @pipeline @command
  Scenario: Build command via registry lookup
    When I look up "collect" in the command builder registry
    Then the builder should return a non-empty command tuple

  # ==============================================================================
  # TIER 6: CONFIGURATION
  # ==============================================================================

  @pipeline @config
  Scenario: Build config strips whitespace from date and tribunal
    Given raw inputs with date "  2026-01-15  " and tribunal "  TJSP  "
    When I build a pipeline config
    Then the config date should be "2026-01-15"
    And the config tribunal should be "TJSP"

  @pipeline @config
  Scenario: Build config with empty optional fields
    Given raw inputs with no date and no tribunal
    When I build a pipeline config
    Then the config date should be empty
    And the config tribunal should be empty

  # ==============================================================================
  # TIER 7: OUTPUT PARSING
  # ==============================================================================

  @pipeline @parsing
  Scenario: Parse key-value output lines
    Given step output text with content "files_added=true\ncatalog_updated=false\n"
    When I parse the step outputs
    Then parsed key "files_added" should be "true"
    And parsed key "catalog_updated" should be "false"

  @pipeline @parsing
  Scenario: Parse empty output
    Given step output text that is empty
    When I parse the step outputs
    Then the parsed outputs should be empty

  @pipeline @parsing
  Scenario: Parse output with extra whitespace
    Given step output text with content "  files_added=true  \n  \n"
    When I parse the step outputs
    Then parsed key "files_added" should be "true"

  @pipeline @parsing
  Scenario: Parse output preserves values with equals signs
    Given step output text with content "key=value=with=equals\n"
    When I parse the step outputs
    Then parsed key "key" should be "value=with=equals"

  # ==============================================================================
  # TIER 8: OUTPUT FORMATTING
  # ==============================================================================

  @pipeline @formatting
  Scenario: Format GitHub Actions output with files added
    Given a pipeline state with files_added true and catalog_updated false
    When I format the GitHub output
    Then the formatted text should contain "files_added=true"
    And the formatted text should contain "catalog_updated=false"

  @pipeline @formatting
  Scenario: Format GitHub Actions output all false
    Given a pipeline state with files_added false and catalog_updated false
    When I format the GitHub output
    Then the formatted text should contain "files_added=false"
    And the formatted text should contain "catalog_updated=false"

  @pipeline @formatting
  Scenario: Format GitHub summary with catalog link
    Given a pipeline state with files_added true and catalog_updated true
    When I format the GitHub summary for job "all"
    Then the formatted text should contain "## Pipeline Summary"
    And the formatted text should contain "**Job**: `all`"
    And the formatted text should contain "catalog.duckdb"

  @pipeline @formatting
  Scenario: Format GitHub summary without catalog link
    Given a pipeline state with files_added false and catalog_updated false
    When I format the GitHub summary for job "all"
    Then the formatted text should not contain "catalog.duckdb"

  @pipeline @formatting
  Scenario: Format step header
    Given a step called "Collect" with command "uv run python collect.py"
    When I format the step header
    Then the formatted text should contain "STEP: Collect"
    And the formatted text should contain "uv run python collect.py"

  @pipeline @formatting
  Scenario: Format step footer success
    Given a step called "Collect" that succeeded with outputs "files_added=true"
    When I format the step footer
    Then the formatted text should contain "[Collect] OK"
    And the formatted text should contain "files_added=true"

  @pipeline @formatting
  Scenario: Format step footer failure
    Given a step called "Collect" that failed with no outputs
    When I format the step footer
    Then the formatted text should contain "[Collect] FAILED"

  @pipeline @formatting
  Scenario: Format pipeline header with all options
    Given a config with job "all" and date "2026-01-15" and tribunal "TJSP"
    When I format the pipeline header
    Then the formatted text should contain "job=all"
    And the formatted text should contain "date=2026-01-15"
    And the formatted text should contain "tribunal=TJSP"

  @pipeline @formatting
  Scenario: Format pipeline header without optional fields
    Given a config with job "collect" and no date and no tribunal
    When I format the pipeline header
    Then the formatted text should contain "job=collect"
    And the formatted text should not contain "date="
    And the formatted text should not contain "tribunal="

  @pipeline @formatting
  Scenario: Format pipeline summary
    Given a pipeline state with files_added true and catalog_updated true
    When I format the pipeline summary
    Then the formatted text should contain "Pipeline complete"
    And the formatted text should contain "files_added:     True"
    And the formatted text should contain "catalog_updated: True"
