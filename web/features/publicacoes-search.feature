Feature: Live DJEN publication search
  Users can search publications directly against the djen API
  from the publications overview page.

  Scenario: Idle state shows instructions
    When the publication search loads with no URL params
    Then I should see instructions about OAB, processo or texto livre

  Scenario: User searches by OAB and sees results
    Given the DJEN API returns 2 publications for the next request
    When I enter "OAB/SP 123456" and press Enter
    Then I should see 2 result cards
    And I should see "OAB SP/123456 detectada" as the hint

  Scenario: User pastes a CNJ process number
    Given the DJEN API returns 1 publication for the next request
    When I enter "1234567-89.2024.8.26.0100" and press Enter
    Then I should see the hint "Número de processo CNJ detectado"
    And I should see 1 result card

  Scenario: User hits the rate limit
    Given the DJEN API responds with HTTP 429 and retry-after 60
    When I enter "contrato" with tribunal "TJSP" and press Enter
    Then I should see a rate-limit banner with a countdown

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

  Scenario: Search criteria changes reset pagination
    Given the DJEN API returns 30 publications out of 60 for each request
    When I search for "contrato", go to page 2, and replace the search with "mandado de segurança"
    Then the last DJEN query should request page 1 for "mandado de segurança"


  Scenario: Shared result link preserves search params and expands result
    Given the DJEN API returns 2 publications with stable identifiers
    When I open a shared result link for "contrato" with tribunal "TJSP" pointing to the second publication
    Then the second publication should be expanded after results load

  Scenario: Copied result links preserve search params for DJEN and fallback IA
    Given clipboard capture is enabled
    When I copy a DJEN result link after searching "contrato" with tribunal "TJSP"
    Then the copied DJEN link should include search params and a publication identifier
    When I copy a fallback IA result link after searching "contrato" with tribunal "TJSP"
    Then the copied fallback IA link should include search params and a publication identifier
