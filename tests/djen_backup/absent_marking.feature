Feature: Absent marking
  When DJEN returns 404 or an empty response for a tribunal/date,
  the internal state marks it as absent so we never retry.

  Scenario: Mark absent when DJEN returns 404
    Given DJEN proxy returns 404 for "TJRR" on "2024-01-15"
    And Internet Archive accepts uploads
    When I process the item "TJRR" on "2024-01-15"
    Then the state should mark "TJRR" on "2024-01-15" as "absent"

  Scenario: Mark absent when DJEN returns empty URL
    Given DJEN proxy returns an empty URL for "TJAP" on "2024-02-10"
    And Internet Archive accepts uploads
    When I process the item "TJAP" on "2024-02-10"
    Then the state should not mark "TJAP" on "2024-02-10" as "absent"
