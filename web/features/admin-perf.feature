Feature: Performance Dashboard
  Admin page showing system latency, upload rates, and quality grades.

  Scenario: Show upload success rate
    Given perf metrics with 98.5 percent upload success rate
    When the perf dashboard loads
    Then I should see "98.5%" as the upload success rate

  Scenario: Show active tribunals count
    Given perf metrics with 91 active tribunals
    When the perf dashboard loads
    Then I should see "91" as active tribunals

  Scenario: Show backlog pending days
    Given perf metrics with 45 backlog pending days
    When the perf dashboard loads
    Then I should see "45" as pending backlog days

  Scenario: Show quality grade distribution
    Given quality scores with grades A:10 B:30 C:40 D:10 F:1
    When the perf dashboard loads
    Then I should see grade labels for non-zero grades

  Scenario: Show slowest tribunals
    Given perf metrics with slowest tribunals "TRT1" and "TRT2"
    When the perf dashboard loads
    Then I should see "TRT1" in the slowest tribunals list
    And I should see "TRT2" in the slowest tribunals list
