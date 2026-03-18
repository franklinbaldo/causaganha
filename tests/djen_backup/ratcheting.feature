Feature: Ratcheting prevention
  Ensure that stopped tribunals do not scan further back than their stop point
  when checking for new data.

  Scenario: Stopped tribunal stops at previous boundary if no new data found
    Given a tribunal "TJRATCHET" stopped at "2025-01-01" with 60 empties
    When backfill runs starting from "2025-01-10"
    And no data is found between "2025-01-10" and "2025-01-01"
    Then the tribunal cursor should remain at "2025-01-01"
    And the tribunal should be stopped

  Scenario: Stopped tribunal resumes scanning if data is found
    Given a tribunal "TJRESUME" stopped at "2025-01-01" with 60 empties
    When backfill runs starting from "2025-01-10"
    And data is found at "2025-01-05"
    Then the tribunal cursor should be older than "2025-01-01"
