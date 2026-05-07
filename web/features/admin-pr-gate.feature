Feature: PR Readiness Gate
  Admin tool to check if a PR is ready to merge.

  Scenario: Show PR lookup form
    When the PR gate page loads
    Then I should see a PR number input field
    And I should see a submit button

  Scenario: Show loading state during fetch
    Given the PR gate page is loaded
    When I submit PR number "42"
    Then I should see a loading indicator

  Scenario: Show error on invalid PR
    Given the PR gate page is loaded
    And the GitHub API returns an error
    When I submit PR number "99999"
    Then I should see an error message

  Scenario: Show merged PR status
    Given the PR gate page is loaded
    And PR 42 is already merged
    When I submit PR number "42"
    Then I should see "Mesclado" status
