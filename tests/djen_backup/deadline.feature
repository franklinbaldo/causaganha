Feature: Deadline awareness
  The runner respects a time budget and skips remaining items
  when fewer than 30 seconds remain.

  Scenario: Skip item when deadline is near
    Given the deadline is 10 seconds from now
    And there are 3 items in the work queue
    When processing takes 5 seconds per item
    Then at least 1 item should be skipped due to deadline

  Scenario: Process all items when time is sufficient
    Given the deadline is 300 seconds from now
    And there are 2 items in the work queue
    When processing takes 0 seconds per item
    Then 0 items should be skipped due to deadline
