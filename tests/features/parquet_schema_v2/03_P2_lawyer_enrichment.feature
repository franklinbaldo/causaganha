Feature: Lawyer Enrichment in Parquet (P2 - Medium Priority)
  As a legal researcher
  I want parquet files to include full lawyer profiles with ratings and statistics
  So that I can analyze decisions without joining external databases

  Background:
    Given the system has lawyer ratings calculated
    And lawyer ratings include OpenSkill mu, sigma, total cases, wins, losses

  @p2 @lawyer-enrichment @export
  Scenario: Export parquet with enriched lawyer profiles
    Given I have 500 analyzed decisions
    And each decision has winner and loser lawyer OAB numbers
    And lawyer ratings exist for all lawyers in the database
    When I export to parquet with schema v2
    Then the parquet file should contain "winner_lawyer" struct column
    And the parquet file should contain "loser_lawyer" struct column
    And each lawyer struct should include: oab, state, name, rating, sigma, total_cases, wins, losses, win_rate
    And the file size should increase by approximately 2-3%

  @p2 @lawyer-enrichment @self-contained
  Scenario: Analyze enriched parquet without database access
    Given I download a schema v2 parquet file from Internet Archive
    And I do NOT have access to the DuckDB lawyer_ratings table
    When I query for upset victories (lower-rated lawyer won)
    Then I can filter using winner_lawyer.rating < loser_lawyer.rating
    And I should find all upset victories without any database joins
    And the results should include full lawyer context

  @p2 @lawyer-enrichment @historical-snapshot
  Scenario: Preserve historical lawyer ratings at decision time
    Given a decision was made on "2025-01-15"
    And lawyer "5733" had rating 1425.5 on "2025-01-15"
    And lawyer "5733" now has rating 1520.3 (today)
    When I export the decision to parquet on "2025-01-15"
    Then the parquet should store rating 1425.5 (snapshot at decision time)
    And I can later track how the lawyer's rating changed
    And I can analyze rating trajectories over time

  @p2 @lawyer-enrichment @duckdb-queries
  Scenario: DuckDB queries parquet directly with enriched data
    Given I have parquet files stored on Internet Archive
    And the parquet files include enriched lawyer data
    When I query with DuckDB directly on the parquet URL
    Then DuckDB should read the lawyer struct columns
    And I can query: SELECT winner_lawyer.name, winner_lawyer.rating FROM parquet_url
    And I can filter: WHERE winner_lawyer.rating > 1500
    And no additional joins are needed

  @p2 @lawyer-enrichment @upset-victories
  Scenario: Find upset victories using enriched data
    Given I have a parquet file with 1000 decisions
    And the parquet includes enriched lawyer ratings
    When I query for decisions where winner_lawyer.rating < loser_lawyer.rating - 100
    Then I should find all significant upset victories
    And each result should include both lawyers' names, ratings, and win rates
    And I can rank upsets by rating difference

  @p2 @lawyer-enrichment @experience-analysis
  Scenario: Analyze how experience affects outcomes
    Given I have a parquet file with enriched lawyer data
    When I group decisions by winner_lawyer.total_cases ranges
    Then I can calculate win rates for different experience brackets
    And I can identify if experienced lawyers win more often
    And I can see confidence scores by experience level

    Examples:
      | experience_bracket | expected_win_rate |
      | 0-50 cases        | ~65%              |
      | 50-100 cases      | ~70%              |
      | 100-200 cases     | ~72%              |
      | 200+ cases        | ~75%              |

  @p2 @lawyer-enrichment @tribunal-specific
  Scenario: Include tribunal-specific lawyer ratings
    Given I have decisions from tribunal "TJRO"
    And lawyer "5733" has global rating 1425.5 but TJRO-specific rating 1380.2
    When I export to parquet for TJRO
    Then winner_lawyer.global_rating should be 1425.5
    And winner_lawyer.tribunal_rating should be 1380.2
    And I can analyze tribunal-specific performance differences

  @p2 @lawyer-enrichment @missing-ratings
  Scenario: Handle lawyers without ratings gracefully
    Given I have a decision with a new lawyer who has no rating yet
    When I export to parquet with enrichment
    Then the lawyer struct should include oab, state, name
    And rating fields should be null
    And total_cases should be 0
    And the export should not fail

  @p2 @lawyer-enrichment @privacy
  Scenario: Verify lawyer information is public data (not PII)
    Given lawyer names and OAB numbers are public record
    And this information is available on OAB public website
    When I export parquet with lawyer enrichment
    Then the data should be considered public information
    And no LGPD privacy violations should occur
    And the data can be shared on Internet Archive

  @p2 @lawyer-enrichment @quality-diagnostics
  Scenario: Identify suspicious decisions using enriched data
    Given I have a parquet file with enriched lawyer data
    When I filter for decisions where:
      | condition                                  |
      | winner_lawyer.rating < loser_lawyer.rating - 200 |
      | AND confidence_score < 0.75                |
    Then I should find potentially erroneous analyses
    And I can target these for re-analysis
    And I can investigate if rating disparities indicate analysis errors

  @p2 @lawyer-enrichment @rating-rank
  Scenario: Include lawyer ranking and percentile in enrichment
    Given I have 10000 lawyers in the rating system
    And lawyer "5733" is ranked #342 (top 3.4%)
    When I export decisions with this lawyer
    Then winner_lawyer.rating_rank should be 342
    And winner_lawyer.rating_percentile should be 0.966 (96.6th percentile)
    And I can identify top-tier lawyers easily

  @p2 @lawyer-enrichment @etl-performance
  Scenario: Enrichment join should not significantly slow export
    Given I have 10000 decisions to export
    When I export with lawyer enrichment (schema v2)
    And I export without enrichment (schema v1)
    Then schema v2 export should be less than 10% slower
    And the join should be efficient using OAB + state indices
