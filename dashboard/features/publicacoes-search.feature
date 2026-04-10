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
