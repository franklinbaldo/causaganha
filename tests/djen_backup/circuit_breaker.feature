Feature: Circuit breaker
  After consecutive IA upload failures the circuit breaker opens,
  skipping further uploads.  It transitions to half-open after a
  recovery timeout and retests with one request.

  Scenario: Circuit opens after 5 consecutive failures
    Given the circuit breaker threshold is 5
    When 5 consecutive IA uploads fail
    Then the circuit breaker should be open
    And the next upload request should be skipped

  Scenario: Circuit enters half-open after recovery timeout
    Given the circuit breaker threshold is 5
    And the recovery timeout is 1 second
    When 5 consecutive IA uploads fail
    And I wait for the recovery timeout
    Then the circuit breaker should be half-open
    And one test request should be allowed

  Scenario: Successful test request closes the circuit
    Given the circuit breaker threshold is 5
    And the recovery timeout is 1 second
    When 5 consecutive IA uploads fail
    And I wait for the recovery timeout
    And the test request succeeds
    Then the circuit breaker should be closed

  Scenario: Failed test request reopens the circuit with a doubled timeout
    Given the circuit breaker threshold is 5
    And the recovery timeout is 1 second
    When 5 consecutive IA uploads fail
    And I wait for the recovery timeout
    And the test request fails
    Then the circuit breaker should be open
    And the recovery timeout should have doubled

  Scenario: Sync is_open check reflects half-open recovery
    Given the circuit breaker threshold is 5
    And the recovery timeout is 1 second
    When 5 consecutive IA uploads fail
    Then is_open should report True
    When I wait for the recovery timeout
    Then is_open should report False

  Scenario: Failed sync probe reopens the circuit with a doubled timeout
    Given the circuit breaker threshold is 5
    And the recovery timeout is 1 second
    When 5 consecutive IA uploads fail
    And I wait for the recovery timeout
    And the sync probe fails
    Then the circuit breaker should be open
    And the recovery timeout should have doubled
    And is_open should report True
