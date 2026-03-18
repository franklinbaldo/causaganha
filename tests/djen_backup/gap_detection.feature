Feature: Gap detection
  The system detects which (date, tribunal) pairs are missing from
  the Internet Archive so it can build a work queue.

  Scenario: Detect missing tribunals for a date
    Given Internet Archive has files for "2024-01-15":
      | filename                        |
      | backup-djen-2024-01-15-TJSP.zip        |
      | backup-djen-2024-01-15-TJRO.absent     |
    And the tribunal list is:
      | tribunal |
      | TJSP     |
      | TJRO     |
      | TJRJ     |
    When I detect gaps for "2024-01-15"
    Then the gaps should be:
      | tribunal |
      | TJRJ     |

  Scenario: No gaps when all tribunals are covered
    Given Internet Archive has files for "2024-03-10":
      | filename                        |
      | backup-djen-2024-03-10-TJSP.zip        |
      | backup-djen-2024-03-10-TJRJ.absent     |
    And the tribunal list is:
      | tribunal |
      | TJSP     |
      | TJRJ     |
    When I detect gaps for "2024-03-10"
    Then there should be no gaps

  Scenario: All tribunals missing when IA item does not exist
    Given Internet Archive has no item for "2024-06-01"
    And the tribunal list is:
      | tribunal |
      | TJSP     |
      | TRT1     |
    When I detect gaps for "2024-06-01"
    Then the gaps should be:
      | tribunal |
      | TJSP     |
      | TRT1     |

  Scenario: State cache skips IA query for fully-covered date
    Given the state cache marks "2024-02-20" as fully covered for:
      | tribunal |
      | TJSP     |
      | TJRJ     |
    And the tribunal list is:
      | tribunal |
      | TJSP     |
      | TJRJ     |
    When I detect gaps for "2024-02-20"
    Then there should be no gaps
    And the Internet Archive should not have been queried
