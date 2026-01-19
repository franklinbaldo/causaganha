Feature: Lawyer Performance Scoring
  As a legal consumer
  I want to see transparent lawyer performance ratings
  So that I can make informed decisions about legal representation

  Background:
    Given the CausaGanha database is initialized
    And the OpenSkill rating system is configured
    And the PlackettLuce model is initialized with default parameters

  # ============================================================================
  # CORE RATING SCENARIOS
  # ============================================================================

  Scenario: New lawyer wins their first case
    Given a new lawyer "João Silva" with OAB "123456/SP"
    And the lawyer has no prior rating
    And there is an unrated analysis where "123456/SP" is the winner
    When I run the score command
    Then the lawyer_ratings table should contain a rating for "123456/SP"
    And the rating (mu) should be above the default baseline (25.0)
    And the uncertainty (sigma) should be high (approximately 8.333)
    And the conservative estimate should be positive
    And the wins count should be 1
    And the losses count should be 0
    And the win rate should be 1.0

  Scenario: New lawyer loses their first case
    Given a new lawyer "Maria Santos" with OAB "234567/RJ"
    And the lawyer has no prior rating
    And there is an unrated analysis where "234567/RJ" is the loser
    When I run the score command
    Then the lawyer_ratings table should contain a rating for "234567/RJ"
    And the rating (mu) should be below the default baseline (25.0)
    And the uncertainty (sigma) should be high (approximately 8.333)
    And the conservative estimate should be lower than a winning first case
    And the wins count should be 0
    And the losses count should be 1
    And the win rate should be 0.0

  Scenario: Update existing rating after a win
    Given lawyer "345678/MG" has current rating mu=28.5 and sigma=6.2
    And the lawyer has 5 prior matches (3 wins, 2 losses)
    And there is an unrated analysis where "345678/MG" is the winner
    When I run the score command
    Then the lawyer's mu should increase from 28.5
    And the lawyer's sigma should decrease from 6.2
    And the wins count should be 4
    And the win rate should be 0.6667 (4/6)

  Scenario: Update existing rating after a loss
    Given lawyer "456789/SP" has current rating mu=32.1 and sigma=5.0
    And the lawyer has 10 prior matches
    And there is an unrated analysis where "456789/SP" is the loser
    When I run the score command
    Then the lawyer's mu should decrease from 32.1
    And the lawyer's sigma should decrease slightly from 5.0
    And the losses count should increase by 1
    And the win rate should decrease

  # ============================================================================
  # OPENSSKILL ALGORITHM BEHAVIOR
  # ============================================================================

  Scenario: Rating changes are proportional to uncertainty
    Given lawyer "111111/RS" with high uncertainty (sigma=8.0)
    And lawyer "222222/PR" with low uncertainty (sigma=3.0)
    And both lawyers have similar mu values
    When both lawyers win a match
    Then lawyer "111111/RS" mu should change more than lawyer "222222/PR" mu
    And both lawyers' sigma should decrease

  Scenario: Conservative estimate accounts for uncertainty
    Given lawyer "333333/SC" has mu=30.0 and sigma=8.0
    And lawyer "444444/BA" has mu=30.0 and sigma=3.0
    When I query their conservative estimates
    Then lawyer "444444/BA" should have a higher conservative estimate
    And the conservative estimate should be approximately mu - 3*sigma

  Scenario: Upset victory increases winner rating significantly
    Given lawyer "555555/CE" has rating mu=20.0 (underdog)
    And lawyer "666666/PE" has rating mu=35.0 (favorite)
    And there is an unrated analysis where "555555/CE" defeats "666666/PE"
    When I run the score command
    Then lawyer "555555/CE" mu should increase significantly
    And lawyer "666666/PE" mu should decrease
    And the rating changes should reflect the upset magnitude

  Scenario: Expected victory changes rating minimally
    Given lawyer "777777/AL" has rating mu=40.0 (favorite)
    And lawyer "888888/SE" has rating mu=18.0 (underdog)
    And there is an unrated analysis where "777777/AL" defeats "888888/SE"
    When I run the score command
    Then lawyer "777777/AL" mu should increase slightly
    And lawyer "888888/SE" mu should decrease slightly
    And the rating changes should be smaller than in an upset

  # ============================================================================
  # BATCH SCORING
  # ============================================================================

  Scenario: Score multiple analyses in batch
    Given there are 20 unrated analyses in the database
    When I run the score command with limit 20
    Then all 20 analyses should be processed
    And all affected lawyer ratings should be updated
    And all analyses should be marked as rated

  Scenario: Process ratings in chronological order
    Given there are unrated analyses with timestamps:
      | Analysis ID | Timestamp            | Winner      | Loser       |
      | ana-1       | 2025-01-10 10:00:00  | 111111/SP   | 222222/RJ   |
      | ana-2       | 2025-01-10 11:00:00  | 222222/RJ   | 333333/MG   |
      | ana-3       | 2025-01-10 12:00:00  | 111111/SP   | 333333/MG   |
    When I run the score command
    Then analyses should be processed in chronological order
    And rating updates should reflect the correct sequence
    And lawyer "111111/SP" final rating should account for both wins

  Scenario: Handle concurrent matches for the same lawyer
    Given lawyer "999999/DF" appears in 5 unrated analyses
    And all 5 analyses have close timestamps
    When I run the score command
    Then all 5 analyses should be processed
    And the rating updates should be applied sequentially
    And the final rating should be consistent

  # ============================================================================
  # EDGE CASES & SPECIAL SCENARIOS
  # ============================================================================

  Scenario: Handle analysis with missing loser
    Given there is an unrated analysis with outcome "EXTINTO SEM MÉRITO"
    And the analysis has a winner but no loser
    When I run the score command
    Then the analysis should be skipped
    And no ratings should be updated
    And a warning should be logged

  Scenario: Handle analysis with missing winner
    Given there is an unrated analysis with unclear outcome
    And the analysis has no clear winner
    When I run the score command
    Then the analysis should be skipped
    And no ratings should be updated
    And a warning should be logged

  Scenario: Skip analysis with same lawyer as winner and loser
    Given there is an unrated analysis where "123456/SP" is both winner and loser
    When I run the score command
    Then the analysis should be skipped
    And no rating update should occur
    And an error should be logged about invalid match

  Scenario: Handle lawyer with only one side of the match
    Given there is an unrated analysis
    And the winner OAB is present but loser OAB is null
    When I run the score command
    Then the analysis should be skipped
    And no ratings should be changed

  # ============================================================================
  # MULTI-LAWYER SCENARIOS
  # ============================================================================

  Scenario: Score case with multiple winners against single loser
    Given there is an unrated analysis
    And the winners are lawyers: "111111/SP", "222222/SP", "333333/SP"
    And the loser is lawyer: "444444/RJ"
    When I run the score command
    Then all 3 winner lawyers should receive rating increases
    And the loser lawyer should receive a rating decrease
    And the rating changes should account for team dynamics

  Scenario: Score case with single winner against multiple losers
    Given there is an unrated analysis
    And the winner is lawyer: "555555/MG"
    And the losers are lawyers: "666666/RJ", "777777/SP"
    When I run the score command
    Then the winner lawyer should receive a rating increase
    And both loser lawyers should receive rating decreases
    And the rating changes should be distributed appropriately

  Scenario: Score case with teams on both sides
    Given there is an unrated analysis
    And the winning team has lawyers: "111111/SP", "222222/RJ"
    And the losing team has lawyers: "333333/MG", "444444/RS"
    When I run the score command
    Then both winning lawyers should receive rating increases
    And both losing lawyers should receive rating decreases
    And the OpenSkill team model should be applied

  # ============================================================================
  # TRIBUNAL-SPECIFIC RATINGS
  # ============================================================================

  Scenario: Calculate separate ratings per tribunal
    Given lawyer "123456/SP" has matches in tribunals "TJSP" and "TJRJ"
    And the lawyer won 5 cases in "TJSP" and 2 cases in "TJRJ"
    When I run the score command
    Then the lawyer should have a rating for tribunal "TJSP"
    And the lawyer should have a rating for tribunal "TJRJ"
    And the "TJSP" rating should be higher than "TJRJ" rating
    And a global rating across all tribunals should also exist

  Scenario: Global rating aggregates all tribunal performances
    Given lawyer "234567/RJ" has ratings:
      | Tribunal | Mu   | Sigma | Matches |
      | TJRJ     | 32.0 | 4.0   | 20      |
      | TJSP     | 28.0 | 5.0   | 10      |
      | TJMG     | 30.0 | 6.0   | 5       |
    When I query the global rating for "234567/RJ"
    Then the global rating should reflect performance across all tribunals
    And the global rating should weight recent matches more heavily

  # ============================================================================
  # RATING STATISTICS
  # ============================================================================

  Scenario: Track win/loss statistics accurately
    Given lawyer "345678/MG" has the following match history:
      | Match | Outcome |
      | 1     | Win     |
      | 2     | Win     |
      | 3     | Loss    |
      | 4     | Win     |
      | 5     | Loss    |
    When all matches are scored
    Then the lawyer should have wins=3, losses=2
    And the win rate should be 0.60
    And the total matches should be 5

  Scenario: Update statistics incrementally
    Given lawyer "456789/SP" has wins=10, losses=5
    And there is a new unrated analysis where the lawyer wins
    When I run the score command
    Then the wins should be 11
    And the losses should remain 5
    And the win rate should be 0.6875 (11/16)

  # ============================================================================
  # CONFIDENCE & RATING QUALITY
  # ============================================================================

  Scenario: Low-confidence analyses affect ratings normally
    Given there is an unrated analysis with confidence score 0.4
    And the analysis has a clear winner and loser
    When I run the score command
    Then the ratings should be updated
    And a warning should be logged about low confidence
    And the confidence score should be recorded for audit

  Scenario: Sigma decreases with more matches (rating stabilization)
    Given a new lawyer "111111/CE" starts with sigma=8.333
    When the lawyer completes 1 match
    Then sigma should decrease
    When the lawyer completes 5 more matches
    Then sigma should decrease further
    When the lawyer completes 20 more matches
    Then sigma should stabilize around 3.0-4.0

  # ============================================================================
  # INCREMENTAL PROCESSING
  # ============================================================================

  Scenario: Only score unrated analyses
    Given the decision_analysis table contains:
      | Analysis ID | Rated |
      | ana-1       | True  |
      | ana-2       | False |
      | ana-3       | False |
    When I run the score command
    Then only analyses "ana-2" and "ana-3" should be scored
    And analysis "ana-1" should be skipped

  Scenario: Mark analysis as rated after successful scoring
    Given an unrated analysis with ID "ana-mark"
    When I run the score command
    And the scoring succeeds
    Then the analysis "ana-mark" should be marked as rated
    And subsequent score commands should skip it

  # ============================================================================
  # RANKING & LEADERBOARDS
  # ============================================================================

  Scenario: Query top-rated lawyers by conservative estimate
    Given the lawyer_ratings table contains:
      | OAB       | State | Mu   | Sigma | Conservative |
      | 111111    | SP    | 35.0 | 3.0   | 26.0         |
      | 222222    | RJ    | 38.0 | 5.0   | 23.0         |
      | 333333    | MG    | 32.0 | 2.0   | 26.0         |
    When I query the top 10 lawyers
    Then the ranking should be ordered by conservative estimate
    And ties should be broken by uncertainty (lower sigma ranks higher)

  Scenario: Filter rankings by tribunal
    Given lawyers have ratings in multiple tribunals
    When I query the top lawyers for tribunal "TJSP"
    Then only ratings from "TJSP" should be included
    And the ranking should reflect tribunal-specific performance

  Scenario: Filter rankings by minimum matches
    Given lawyers have varying match counts:
      | OAB    | Matches | Rating |
      | 111111 | 50      | 35.0   |
      | 222222 | 5       | 40.0   |
      | 333333 | 100     | 32.0   |
    When I query rankings with minimum 20 matches
    Then only lawyers "111111" and "333333" should be included
    And lawyer "222222" should be excluded despite higher rating

  # ============================================================================
  # DATA INTEGRITY
  # ============================================================================

  Scenario: Prevent rating corruption from concurrent updates
    Given two processes attempt to update lawyer "123456/SP" rating simultaneously
    When both scoring operations complete
    Then the final rating should be consistent
    And no rating updates should be lost
    And the database should maintain referential integrity

  Scenario: Rollback ratings on scoring error
    Given there are 10 unrated analyses to process
    And analysis #5 causes a critical error
    When I run the score command
    Then analyses 1-4 should be scored successfully
    And analysis #5 should be logged as failed
    And analyses 6-10 should be processed
    And no partial rating updates should be left in inconsistent state

  # ============================================================================
  # PERFORMANCE & SCALE
  # ============================================================================

  Scenario: Score large batches efficiently
    Given there are 1000 unrated analyses
    When I run the score command with limit 1000
    Then all 1000 analyses should be scored
    And the scoring should complete within reasonable time
    And memory usage should remain bounded

  Scenario: Handle thousands of lawyer records
    Given the lawyer_ratings table contains 10,000 lawyers
    When I run the score command for 100 new analyses
    Then the scoring should complete efficiently
    And only affected lawyer ratings should be updated
    And database queries should use proper indexes
