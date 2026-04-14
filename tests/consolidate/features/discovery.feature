Feature: Find dates needing consolidation
  As the consolidation pipeline
  I want to know which dates have ZIPs ready but no Parquets yet
  So I only process the work that's still pending

  Scenario: Dates with uploaded ZIPs appear in the manifest
    Given a sync-manifest with 3 dates: 2026-04-01, 2026-04-02, 2026-04-03
    And all 3 dates have ia_status="uploaded"
    When I list dates with uploads
    Then all 3 dates appear
    And they are sorted newest-first

  Scenario: Dates without uploads are excluded
    Given a sync-manifest with 2 dates
    And date 2026-04-01 has ia_status="uploaded"
    And date 2026-04-02 has djen_status="absent" and no ia_status
    When I list dates with uploads
    Then only 2026-04-01 appears

  Scenario: Missing manifest returns empty list
    Given no sync-manifest file exists
    When I list dates with uploads
    Then the result is empty

  Scenario: Summary counts reflect the manifest state
    Given a sync-manifest with 5 uploaded, 3 absent, and 2 unknown rows
    When I request the counts summary
    Then uploaded count equals 5
    And absent count equals 3
    And total count equals 10
