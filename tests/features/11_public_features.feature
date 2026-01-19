Feature: Public User-Facing Features
  As a legal consumer
  I want to search and compare lawyers
  So that I can make informed decisions about legal representation

  Background:
    Given the CausaGanha public website is accessible
    And the database contains lawyer ratings

  # ============================================================================
  # NOTE: This feature is OUT OF SCOPE for MVP (Phase 1)
  # Targeted for Public Beta (Phase 2) and Public Launch (Phase 3)
  # ============================================================================

  # ============================================================================
  # LAWYER SEARCH
  # ============================================================================

  Scenario: Search for lawyers by location
    Given I am on the lawyer search page
    When I select state "São Paulo"
    And I click "Search"
    Then I should see lawyers licensed in São Paulo
    And results should be sorted by rating (highest first)
    And each result should show OAB number, name, rating, and win rate

  Scenario: Filter lawyers by practice area
    Given I am on the lawyer search page
    When I select practice area "Labor Law"
    And I select state "Rondônia"
    And I click "Search"
    Then I should see lawyers specializing in Labor Law in Rondônia
    And results should indicate "98% of cases in Labor Law"

  Scenario: Filter by minimum case count
    Given I am on the lawyer search page
    When I set minimum cases to 20
    And I click "Search"
    Then all results should have at least 20 cases
    And lawyers with fewer than 20 cases should be excluded
    And a note should explain "Minimum 20 cases for statistical reliability"

  Scenario: Sort search results
    Given I have search results for labor lawyers in São Paulo
    When I sort by "Win Rate"
    Then results should be ordered by win rate (descending)
    When I sort by "Experience"
    Then results should be ordered by total cases (descending)
    When I sort by "Rating"
    Then results should be ordered by conservative rating estimate (descending)

  Scenario: Empty search results
    Given I am on the lawyer search page
    When I search for lawyers in a practice area with no data
    Then I should see "No lawyers found matching your criteria"
    And I should see suggestions to broaden search criteria
    And I should see "Try selecting a different state or practice area"

  Scenario: Pagination of search results
    Given a search returns 150 lawyers
    When I view the results
    Then I should see the first 20 results
    And pagination controls should show "Page 1 of 8"
    When I click "Next"
    Then I should see results 21-40
    And the URL should update with page parameter

  # ============================================================================
  # LAWYER PROFILE PAGES
  # ============================================================================

  Scenario: View lawyer profile
    Given lawyer "123456/SP" has a rating in the database
    When I navigate to "/lawyer/123456-SP"
    Then I should see the lawyer's profile page
    And the page should display:
      | Field              | Example Value                    |
      | OAB Number         | 123456/SP                        |
      | Rating             | 32.5 ± 4.2 (95% confidence)      |
      | Win Rate           | 68% (31 wins, 14 losses)         |
      | Total Cases        | 45                               |
      | Practice Area      | Labor Law (98% of cases)         |
      | Active in          | TJSP (Tribunal de Justiça de SP) |
      | Confidence Badge   | High (45+ cases)                 |

  Scenario: View case history on profile
    Given lawyer "123456/SP" has 45 cases
    When I view the lawyer's profile
    Then I should see a case history section
    And the 10 most recent cases should be displayed
    And each case should show:
      | Field           | Example                    |
      | Outcome         | ✅ Win or ❌ Loss          |
      | Case Type       | Rescisão contratual        |
      | Date            | Feb 2024                   |
      | Tribunal        | TJSP                       |
      | Confidence      | 92%                        |
      | Archive Link    | [View on Archive.org ↗]    |

  Scenario: View rating chart over time
    Given lawyer "123456/SP" has been rated for 12 months
    When I view the lawyer's profile
    Then I should see a chart showing rating over time
    And the chart should display months on X-axis
    And rating values on Y-axis
    And confidence intervals should be shown as shaded areas

  Scenario: View practice area breakdown
    Given lawyer "234567/RJ" has cases in multiple areas:
      | Practice Area | Cases | Percentage |
      | Labor Law     | 35    | 70%        |
      | Civil Law     | 10    | 20%        |
      | Family Law    | 5     | 10%        |
    When I view the lawyer's profile
    Then I should see a practice area breakdown
    And it should show "Primary: Labor Law (70%)"
    And it should list secondary areas

  Scenario: View win rate by case type
    Given lawyer "345678/MG" has case outcomes by type
    When I view the detailed statistics
    Then I should see win rate broken down by case type
    And each case type should show wins/losses/total
    And confidence should be indicated for each category

  Scenario: SEO-optimized lawyer profile
    Given lawyer "Dr. João Silva" with OAB "123456/SP"
    When I view the profile page
    Then the page title should be "Dr. João Silva - OAB 123456/SP - Lawyer Rating | CausaGanha"
    And meta description should include rating and win rate
    And the page should have structured data (JSON-LD) for search engines

  Scenario: Share lawyer profile
    Given I am viewing a lawyer profile
    When I click "Share"
    Then I should see share options for:
      | Platform     |
      | Copy Link    |
      | WhatsApp     |
      | Email        |
      | LinkedIn     |
    And the shared link should be the canonical profile URL

  # ============================================================================
  # LAWYER COMPARISON
  # ============================================================================

  Scenario: Compare two lawyers
    Given I have selected lawyer "123456/SP"
    When I click "Compare"
    And I select lawyer "234567/SP" for comparison
    Then I should see a side-by-side comparison
    And the comparison should show:
      | Metric              | Lawyer 1       | Lawyer 2       |
      | Rating              | 32.5           | 28.3           |
      | Win Rate            | 68%            | 55%            |
      | Total Cases         | 45             | 22             |
      | Confidence          | High           | Medium         |
      | Primary Practice    | Labor Law      | Labor Law      |
    And differences should be highlighted

  Scenario: Compare three lawyers
    Given I want to compare 3 lawyers
    When I select lawyers "111111/SP", "222222/SP", "333333/SP"
    Then I should see a three-column comparison table
    And each lawyer's strengths should be highlighted
    And the comparison URL should be shareable

  Scenario: Comparison shows confidence warnings
    Given I am comparing:
      | Lawyer      | Cases | Confidence |
      | 111111/SP   | 45    | High       |
      | 222222/SP   | 8     | Low        |
    When I view the comparison
    Then lawyer "222222/SP" should have a warning badge
    And the warning should say "⚠️ Low confidence (only 8 cases)"
    And a tooltip should explain the confidence system

  Scenario: Remove lawyer from comparison
    Given I am comparing 3 lawyers
    When I click "Remove" on lawyer "222222/SP"
    Then the comparison should update to show 2 lawyers
    And I should be able to add a different lawyer

  # ============================================================================
  # METHODOLOGY & TRANSPARENCY
  # ============================================================================

  Scenario: View "How Ratings Work" page
    Given I am on the website
    When I click "How Ratings Work"
    Then I should see the methodology explanation page
    And it should explain:
      | Section                  |
      | Data Collection (PJe)    |
      | AI Analysis (Gemini LLM) |
      | OpenSkill Rating System  |
      | Confidence Intervals     |
      | Accuracy Validation      |
    And it should include diagrams and examples

  Scenario: Interactive OpenSkill demo
    Given I am on the "How Ratings Work" page
    When I scroll to the "OpenSkill Algorithm" section
    Then I should see an interactive demo
    And I can simulate a match between two lawyers
    And I can see how ratings change based on outcomes

  Scenario: Access methodology paper
    Given I am on the methodology page
    When I click "Download Full Methodology (PDF)"
    Then a PDF should download
    And the PDF should contain academic-style documentation
    And it should be citable in research papers

  # ============================================================================
  # SEARCH ENGINE OPTIMIZATION
  # ============================================================================

  Scenario: Homepage is SEO-optimized
    When I view the homepage HTML
    Then the title should be "CausaGanha - Transparent Lawyer Performance Ratings in Brazil"
    And meta description should be under 160 characters
    And structured data should include Organization schema
    And Open Graph tags should be present for social sharing

  Scenario: Lawyer search page is indexed
    Given a search for "labor lawyers in São Paulo"
    When search engines crawl the results page
    Then the page should be indexable
    And it should have canonical URL
    And it should have relevant H1 heading
    And it should link to individual lawyer profiles

  Scenario: Site map for search engines
    When search engines request /sitemap.xml
    Then a sitemap should be generated
    And it should include:
      | URL Pattern              |
      | Homepage                 |
      | /lawyer/[oab]-[state]    |
      | /search?state=[state]    |
      | /methodology             |
    And it should be updated daily

  # ============================================================================
  # RESPONSIVE DESIGN
  # ============================================================================

  Scenario: Mobile-friendly search
    Given I am on a mobile device
    When I access the search page
    Then the layout should adapt to mobile screen
    And filters should be collapsible
    And results should be scrollable
    And touch targets should be at least 44x44 pixels

  Scenario: Mobile lawyer profile
    Given I am viewing a lawyer profile on mobile
    Then the profile should be readable without zooming
    And charts should be optimized for mobile
    And case history should be swipeable
    And the share button should use native mobile sharing

  # ============================================================================
  # ACCESSIBILITY
  # ============================================================================

  Scenario: Keyboard navigation
    Given I am using only a keyboard
    When I navigate the search page
    Then all interactive elements should be keyboard-accessible
    And focus indicators should be visible
    And I can tab through filters in logical order

  Scenario: Screen reader compatibility
    Given I am using a screen reader
    When I navigate a lawyer profile
    Then all content should be announced correctly
    And images should have alt text
    And charts should have accessible data tables
    And ARIA labels should be present

  Scenario: Color contrast compliance
    When I analyze the website's color scheme
    Then all text should meet WCAG AA contrast ratios
    And important information should not rely on color alone
    And links should be distinguishable from regular text

  # ============================================================================
  # PERFORMANCE
  # ============================================================================

  Scenario: Fast page load times
    Given I am on a typical connection
    When I load the lawyer search page
    Then the page should load in under 3 seconds
    And largest contentful paint (LCP) should be < 2.5s
    And first input delay (FID) should be < 100ms

  Scenario: Optimized images
    When I view lawyer profiles
    Then images should be served in modern formats (WebP, AVIF)
    And images should be lazy-loaded
    And responsive images should be used for different screen sizes

  # ============================================================================
  # ANALYTICS & TRACKING
  # ============================================================================

  Scenario: Track search behavior
    Given analytics are enabled
    When a user performs a search
    Then the following should be tracked:
      | Event              | Data                              |
      | Search Performed   | State, practice area, filters     |
      | Results Viewed     | Number of results, time on page   |
      | Profile Clicked    | Which lawyer, position in results |
      | Comparison Started | Which lawyers compared            |

  Scenario: Privacy-respecting analytics
    When analytics are collected
    Then no personally identifiable information should be stored
    And users should be able to opt out
    And analytics should use cookie-free tracking (if possible)
    And data should be anonymized

  # ============================================================================
  # ERROR STATES
  # ============================================================================

  Scenario: Handle profile not found
    Given lawyer "999999/XX" does not exist
    When I navigate to "/lawyer/999999-XX"
    Then I should see a 404 error page
    And it should say "Lawyer not found"
    And it should provide a link back to search
    And it should suggest checking the OAB number

  Scenario: Handle server errors gracefully
    Given the backend is temporarily unavailable
    When I try to load the search page
    Then I should see a friendly error message
    And it should say "We're experiencing technical difficulties"
    And it should suggest trying again later
    And it should not expose technical error details

  # ============================================================================
  # FEEDBACK & SUPPORT
  # ============================================================================

  Scenario: Report incorrect information
    Given I am viewing a lawyer profile
    When I click "Report Issue"
    Then I should see a form to describe the issue
    And I can select issue type (incorrect name, wrong cases, etc.)
    And I can provide my email for follow-up
    And the form should submit to support system

  Scenario: Help and FAQ
    Given I am confused about ratings
    When I click "Help" or "FAQ"
    Then I should see frequently asked questions
    And answers should be clear and non-technical
    And there should be contact information for further help
