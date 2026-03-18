Feature: Backfill with 60-empty-day stop rule
  The backfill engine scans backward through dates per tribunal.
  After 60 consecutive authoritative empty days, the tribunal is
  marked stopped and skipped on future runs.

  Scenario: 60 consecutive empty dates stop tribunal
    Given a tribunal "TJXX" with 59 consecutive empties
    And DJEN proxy returns 404 for the next date
    And Internet Archive accepts uploads
    When I backfill "TJXX" for 1 date
    Then "TJXX" should be stopped
    And the empty streak should be 60

  Scenario: Hit before 60 resets streak
    Given a tribunal "TJYY" with 58 consecutive empties
    And DJEN proxy returns a valid ZIP for the next date
    And Internet Archive accepts uploads
    When I backfill "TJYY" for 1 date
    Then "TJYY" should not be stopped
    And the empty streak should be 0

  Scenario: Errors do not count as empty
    Given a tribunal "TJER" with 59 consecutive empties
    And DJEN proxy returns a server error for the next date
    When I backfill "TJER" for 1 date
    Then "TJER" should not be stopped
    And the empty streak should be 59

  Scenario: Stopped tribunal is skipped on next run
    Given a tribunal "TJST" that is already stopped
    When I backfill "TJST" for 1 date
    Then "TJST" should still be stopped
    And the backfill summary should show 1 skipped stopped

  Scenario: Manual reset re-enables tribunal
    Given a tribunal "TJRS" that is already stopped
    When I reset "TJRS"
    Then "TJRS" should not be stopped
    And the empty streak should be 0

  Scenario: Lower bound stops scanning
    Given a tribunal "TJLB" at the lower bound date
    When I backfill "TJLB" for 10 dates
    Then "TJLB" should not be stopped
    And the backfill summary should show 0 dates processed

  Scenario: No lower bound — stop rule halts scanning
    Given a tribunal "TJNB" with 59 consecutive empties
    And DJEN proxy returns 404 for the next date
    And Internet Archive accepts uploads
    When I backfill "TJNB" for 1 date with no lower bound
    Then "TJNB" should be stopped
    And the empty streak should be 60

  Scenario: Already-uploaded item on IA counts as hit
    Given a tribunal "TJIA" with 59 consecutive empties
    And IA state marks the next date as "uploaded"
    When I backfill "TJIA" for 1 date
    Then "TJIA" should not be stopped
    And the empty streak should be 0
