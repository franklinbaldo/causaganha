Feature: Not Found Page
  Shows a friendly error when users visit an undefined route.

  Scenario: Show 404 error message
    When the 404 page loads
    Then I should see "404"
    And I should see "Pagina nao encontrada"

  Scenario: Show navigation buttons
    When the 404 page loads
    Then I should see a "Dashboard" link
    And I should see an "Inicio" link
