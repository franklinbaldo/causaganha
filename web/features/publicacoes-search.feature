Feature: Explicit DJEN publication search
  Users can prepare publication search criteria locally and submit
  explicit searches against the DJEN API from the publications overview page.

  Scenario: Idle state shows instructions
    When the publication search loads with no URL params
    Then I should see instructions about OAB, processo or texto livre

  Scenario: Typing prepares criteria without submitting to DJEN
    Given the DJEN API returns 2 publications for the next request
    When I type "OAB/SP 123456" without submitting
    Then I should see the prepared OAB criteria "OAB/SP 123456"
    And the DJEN API should not have been called

  Scenario: User searches by OAB and sees results
    Given the DJEN API returns 2 publications for the next request
    When I enter "OAB/SP 123456" and press Enter
    Then I should see 2 result cards
    And I should see "OAB SP/123456 detectada" as the hint

  Scenario: User submits with the Buscar button
    Given the DJEN API returns 1 publication for the next request
    When I type "mandado de segurança" and click Buscar
    Then I should see 1 result card
    And the last DJEN query should include text "mandado de segurança"

  Scenario: User pastes a CNJ process number
    Given the DJEN API returns 1 publication for the next request
    When I enter "1234567-89.2024.8.26.0100" and press Enter
    Then I should see the hint "Número de processo CNJ detectado"
    And I should see 1 result card

  Scenario: User hits the rate limit
    Given the DJEN API responds with HTTP 429 and retry-after 60
    When I enter "contrato" with tribunal "TJSP" and press Enter
    Then I should see a DJEN rate-limit banner with a countdown and historical archive action

  Scenario: User uses Ctrl+K to focus search input
    When I press Ctrl+K
    Then the search input should be focused

  Scenario: User presses Escape to clear input
    When I type "Some search text" in the search input
    And I press Escape
    Then the search input should be empty

  Scenario: Input is auto-focused on load
    When the publication search loads with no URL params
    Then the search input should be focused

  Scenario: Search criteria changes reset pagination only after explicit submit
    Given the DJEN API returns 30 publications out of 60 for each request
    When I search for "contrato", go to page 2, type "mandado de segurança", and click Buscar
    Then the last DJEN query should request page 1 for "mandado de segurança"
