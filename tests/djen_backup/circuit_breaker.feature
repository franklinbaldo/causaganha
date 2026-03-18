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
