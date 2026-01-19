Feature: Legal and Regulatory Compliance
  As a compliance officer
  I want the platform to meet all legal requirements
  So that we operate lawfully and protect user rights

  Background:
    Given the CausaGanha platform is operational
    And compliance features are configured

  # ============================================================================
  # NOTE: This feature is PARTIALLY for MVP, fully implemented in Phase 2-3
  # Basic data security is MVP (P1)
  # LGPD workflows and dispute mechanisms are Public Beta/Launch (Phase 2-3)
  # ============================================================================

  # ============================================================================
  # LGPD (Brazilian Data Protection Law) - RIGHTS IMPLEMENTATION
  # ============================================================================

  Scenario: Lawyer exercises right to access (Article 18, I)
    Given I am lawyer "123456/SP"
    When I submit a data access request with identity verification
    Then I should receive within 15 days:
      | Data Category          | Content                               |
      | Personal Data          | OAB number, state, name (if stored)   |
      | Rating Data            | Current rating, uncertainty, percentile|
      | Case History           | All cases I participated in           |
      | Processing Activities  | How data was collected and used       |
      | Data Retention         | How long data will be kept            |

  Scenario: Lawyer exercises right to correction (Article 18, III)
    Given I am lawyer "123456/SP"
    And my rating includes an incorrect analysis
    When I submit a correction request with evidence
    Then my request should be reviewed within 5 business days
    And if confirmed incorrect:
      | Action                          |
      | Analysis marked as incorrect    |
      | Rating recalculated             |
      | Correction logged in audit trail|
      | I am notified of the correction |

  Scenario: Lawyer exercises right to deletion (Article 18, VI)
    Given I am lawyer "123456/SP"
    When I submit a deletion request
    Then the system should:
      | Step                              | Action                                    |
      | 1. Verify identity                | Confirm I am the lawyer via OAB or email  |
      | 2. Assess legal basis             | Balance privacy vs. transparency interest |
      | 3. Anonymize (not full delete)    | Remove name, keep anonymized rating       |
      | 4. Preserve statistics            | Maintain data integrity for other ratings |
      | 5. Notify                         | Confirm anonymization within 15 days      |
    And my name should no longer be searchable
    And my OAB should be anonymized in public displays
    But case outcomes should remain for statistical integrity

  Scenario: Handle deletion conflicts with transparency mission
    Given lawyer "123456/SP" requests deletion
    And their data is essential for other lawyers' ratings
    When the deletion request is processed
    Then the system should:
      | Action                                           |
      | Explain that full deletion would harm data integrity |
      | Offer anonymization as alternative                   |
      | Provide detailed explanation of balancing test       |
      | Allow lawyer to appeal decision                      |
    And if lawyer insists on full deletion:
      | Action                                           |
      | Legal counsel reviews                            |
      | Decision documented                              |
      | Lawyer notified of final decision                |

  Scenario: Lawyer exercises right to data portability (Article 18, V)
    Given I am lawyer "123456/SP"
    When I request my data in portable format
    Then I should receive within 15 days:
      | File               | Format | Content                        |
      | rating_data.csv    | CSV    | All rating history             |
      | case_history.csv   | CSV    | All cases and outcomes         |
      | analyses.json      | JSON   | LLM analyses of my cases       |
      | metadata.yaml      | YAML   | Data dictionary and schema     |
    And the data should be machine-readable
    And I should be able to use it with other services

  Scenario: Lawyer exercises right to oppose processing (Article 18, II)
    Given I am lawyer "123456/SP"
    When I oppose the processing of my data
    Then the system should:
      | Step                          | Action                                  |
      | 1. Review opposition grounds  | Assess if legitimate interest applies   |
      | 2. Explain legal basis        | We process public data for transparency |
      | 3. Offer alternatives         | Profile hiding, anonymization           |
      | 4. Escalate if unresolved     | Legal counsel review                    |
    And I should receive a response within 15 days

  # ============================================================================
  # LGPD - DATA MINIMIZATION & PURPOSE LIMITATION
  # ============================================================================

  Scenario: Only collect necessary data
    When the system collects lawyer data
    Then it should collect ONLY:
      | Data Type         | Justification                   |
      | OAB number        | Required for identification     |
      | State             | Required for jurisdiction       |
      | Case participation| Required for rating calculation |
      | Case outcomes     | Required for rating calculation |
    And it should NOT collect:
      | Data Type                    |
      | Personal addresses           |
      | Phone numbers                |
      | Email addresses (unless provided voluntarily)|
      | Financial information        |
      | Client identities            |

  Scenario: Purpose limitation enforcement
    Given lawyer data is collected for performance ratings
    When someone requests to use the data for marketing
    Then the request should be denied
    And the data should ONLY be used for:
      | Allowed Purpose                    |
      | Calculating lawyer ratings         |
      | Public transparency and disclosure |
      | Academic research (anonymized)     |
      | Legal compliance and dispute resolution|

  # ============================================================================
  # LGPD - TRANSPARENCY & ACCOUNTABILITY
  # ============================================================================

  Scenario: Privacy policy is clear and accessible
    Given I am a website visitor
    When I access the privacy policy
    Then it should explain in plain language:
      | Section                        | Content                                 |
      | What data we collect           | OAB, state, case outcomes               |
      | Why we collect it              | Lawyer performance transparency         |
      | Legal basis                    | Legitimate interest (Article 7, VI)     |
      | How we use it                  | Calculate ratings, publish transparently|
      | How long we keep it            | Permanently (public interest)           |
      | Your rights                    | Access, correction, deletion, etc.      |
      | How to exercise rights         | Email, web form, contact info           |
      | Contact information            | Data protection officer or team email   |

  Scenario: Terms of service address data processing
    When I review the terms of service
    Then they should include:
      | Section                      | Content                                  |
      | Data collection practices    | Clear explanation                        |
      | Consent (where applicable)   | For voluntary data (e.g., email subscriptions)|
      | Dispute resolution           | How to challenge incorrect data          |
      | Changes to terms             | How users will be notified               |

  # ============================================================================
  # LGPD - SECURITY MEASURES
  # ============================================================================

  Scenario: Database access controls
    Given the production database contains lawyer data
    Then access should be restricted to:
      | Who                    | Access Level         |
      | Pipeline automation    | Read/write (specific tables)|
      | Developers             | Read-only (non-production)  |
      | Administrators         | Read/write (with audit log) |
      | Public                 | No direct access            |
    And all access should be logged

  Scenario: API authentication and rate limiting
    When external parties access the API
    Then they must:
      | Requirement                 |
      | Authenticate with API key   |
      | Respect rate limits         |
      | Not scrape personal data    |
    And suspicious activity should be detected and blocked

  Scenario: Encryption in transit
    When data is transmitted over the network
    Then it must use HTTPS/TLS 1.3
    And HTTP requests should redirect to HTTPS
    And certificate should be valid and trusted

  Scenario: Secure credential management
    When the system uses API keys and secrets
    Then credentials must:
      | Security Measure                |
      | Stored in environment variables |
      | Never committed to git          |
      | Rotated periodically            |
      | Encrypted at rest               |

  # ============================================================================
  # LGPD - INCIDENT RESPONSE
  # ============================================================================

  Scenario: Data breach detection
    When unauthorized access to lawyer data occurs
    Then the system should:
      | Step                        | Timeline       |
      | Detect the breach           | Immediately    |
      | Contain the breach          | < 1 hour       |
      | Assess scope and impact     | < 24 hours     |
      | Notify ANPD (if significant)| < 48 hours     |
      | Notify affected lawyers     | < 48 hours     |
      | Public disclosure           | < 1 week       |

  Scenario: Breach notification to lawyers
    Given a data breach affected 5,000 lawyers
    When notifications are sent
    Then each lawyer should receive:
      | Information                          |
      | What data was compromised            |
      | How the breach occurred              |
      | Steps we're taking                   |
      | Steps they should take               |
      | Contact for questions                |
    And notifications should be via email
    And a public statement should be published

  # ============================================================================
  # LAWYER DISPUTE MECHANISM
  # ============================================================================

  Scenario: Lawyer submits dispute about incorrect rating
    Given I am lawyer "123456/SP"
    And my rating is based on an incorrect analysis
    When I submit a dispute via the web form
    Then I should provide:
      | Required Information          |
      | My OAB number and state       |
      | Specific case(s) in question  |
      | What is incorrect             |
      | Evidence (e.g., correct PDF)  |
      | My contact email              |
    And I should receive confirmation email immediately

  Scenario: Dispute is reviewed by data quality team
    Given a lawyer has disputed an analysis
    When the data quality team reviews it
    Then they should:
      | Step                              | Timeline       |
      | 1. Retrieve original PDF          | < 24 hours     |
      | 2. Manually re-analyze decision   | < 3 days       |
      | 3. Compare to LLM analysis        | < 3 days       |
      | 4. Determine if correction needed | < 5 days       |
      | 5. Notify lawyer of decision      | < 7 days       |
    And the review should be documented

  Scenario: Dispute is confirmed correct - analysis corrected
    Given a dispute is confirmed as valid
    When the correction is applied
    Then the system should:
      | Action                                  |
      | Mark original analysis as incorrect     |
      | Create corrected analysis               |
      | Recalculate affected lawyer ratings     |
      | Log correction in audit trail           |
      | Notify disputing lawyer of correction   |
      | Update confidence/accuracy metrics      |

  Scenario: Dispute is rejected - analysis was correct
    Given a dispute is reviewed and the original analysis is correct
    When the lawyer is notified
    Then they should receive:
      | Information                              |
      | Explanation of why analysis is correct   |
      | Reference to original PDF                |
      | Explanation of LLM reasoning             |
      | Opportunity to appeal decision           |
      | Contact for further questions            |

  Scenario: Dispute appeal process
    Given a lawyer's dispute was rejected
    And they believe the decision was wrong
    When they submit an appeal
    Then a second reviewer should:
      | Step                              |
      | Re-examine the case independently |
      | Review all evidence               |
      | Make final decision               |
      | Notify lawyer within 10 days      |
    And the second reviewer's decision is final

  # ============================================================================
  # OAB (BRAZILIAN BAR ASSOCIATION) COMPLIANCE
  # ============================================================================

  Scenario: Verify OAB numbers are valid
    When lawyer data is collected
    Then OAB numbers should be validated:
      | Validation                      |
      | Format: 4-7 digits              |
      | State: Valid Brazilian state    |
      | Optional: Cross-check OAB API   |
    And invalid OAB numbers should be rejected

  Scenario: No unfair lawyer advertising
    Given the platform displays lawyer ratings
    Then the display must be:
      | Requirement                          |
      | Objective (based on data, not ads)   |
      | Equal treatment (all lawyers rated)  |
      | Not paid by lawyers (independent)    |
      | Transparent methodology              |
    And no lawyer can pay for better placement

  Scenario: Respect OAB confidentiality rules
    When displaying case information
    Then we must NOT reveal:
      | Prohibited Information        |
      | Client identities             |
      | Privileged communications     |
      | Sealed court records          |
      | Confidential settlements      |
    And only public court decisions should be used

  Scenario: Handle OAB complaints
    Given the OAB files a complaint about the platform
    When we receive the complaint
    Then we should:
      | Step                                  |
      | Acknowledge receipt within 48 hours   |
      | Engage legal counsel                  |
      | Provide detailed explanation of methodology|
      | Offer to address specific concerns    |
      | Seek mediation if needed              |

  # ============================================================================
  # COURT DATA USAGE COMPLIANCE
  # ============================================================================

  Scenario: Respect PJe API rate limits
    When collecting data from PJe API
    Then requests must be rate-limited:
      | Limit Type            | Value                |
      | Requests per minute   | ≤ 60 (or court limit)|
      | Concurrent requests   | ≤ 10                 |
      | Retry backoff         | Exponential          |
    And 429 responses should be respected

  Scenario: Proper attribution to courts
    When displaying court data
    Then we must attribute the source:
      | Requirement                              |
      | Credit the tribunal (e.g., "Source: TJRO")|
      | Link to original court website           |
      | Include archive.org preservation link    |
      | Do not claim data as our own             |

  Scenario: Handle court requests to remove data
    Given a court requests removal of a specific decision
    When we receive the request
    Then we should:
      | Step                                     |
      | Verify request is legitimate (court official)|
      | Review legal obligation                   |
      | Remove data if legally required           |
      | Document removal reason                   |
      | Notify affected lawyers if ratings change |

  # ============================================================================
  # ANPD (BRAZILIAN DATA PROTECTION AUTHORITY) COMPLIANCE
  # ============================================================================

  Scenario: Maintain processing records (Article 37)
    When ANPD requests our data processing records
    Then we should provide:
      | Record                              |
      | Types of personal data processed    |
      | Purposes of processing              |
      | Legal basis (legitimate interest)   |
      | Data subjects (lawyers)             |
      | Data retention periods              |
      | Security measures implemented       |
      | Third-party processors (if any)     |
      | International transfers (if any)    |

  Scenario: Respond to ANPD inquiries
    Given ANPD requests information about our practices
    When we receive the request
    Then we should respond within required timeframe
    And provide complete, accurate information
    And cooperate fully with investigation

  Scenario: Conduct Data Protection Impact Assessment (DPIA)
    Given we are launching public-facing features
    When a DPIA is performed
    Then it should assess:
      | Risk Category                       | Assessment                   |
      | Data processing activities          | What data, why, how          |
      | Risks to lawyer privacy             | Low (public data)            |
      | Mitigation measures                 | Anonymization, dispute process|
      | Necessity and proportionality       | Justified by transparency    |
      | Rights of data subjects             | Access, correction, deletion |
    And the DPIA should be documented

  # ============================================================================
  # INTERNATIONAL CONSIDERATIONS
  # ============================================================================

  Scenario: Handle international data transfers (if applicable)
    Given we use cloud services outside Brazil (e.g., Gemini API, GitHub)
    When personal data is transferred internationally
    Then we must:
      | Requirement                                 |
      | Ensure adequate level of protection        |
      | Use standard contractual clauses if needed |
      | Document transfer mechanisms               |
      | Inform data subjects                       |

  # ============================================================================
  # AUDIT AND COMPLIANCE MONITORING
  # ============================================================================

  Scenario: Regular compliance audits
    Given the platform has been operating for 12 months
    When a compliance audit is performed
    Then it should check:
      | Audit Item                             | Status |
      | Privacy policy up to date              | ✓      |
      | All LGPD rights workflows functional   | ✓      |
      | Security measures in place             | ✓      |
      | Data minimization practiced            | ✓      |
      | Purpose limitation enforced            | ✓      |
      | Incident response plan tested          | ✓      |
      | Staff trained on data protection       | ✓      |
    And findings should be documented and addressed

  Scenario: Track compliance metrics
    When monitoring compliance
    Then the following should be tracked:
      | Metric                              | Target     |
      | LGPD requests response time         | < 15 days  |
      | Disputes resolved                   | < 7 days   |
      | Data breaches                       | 0          |
      | OAB complaints                      | 0          |
      | ANPD enforcement actions            | 0          |
      | Compliance audit findings           | 0 critical |

  # ============================================================================
  # USER CONSENT (WHERE APPLICABLE)
  # ============================================================================

  Scenario: Consent for optional data collection
    Given a user wants to subscribe to email updates
    When they provide their email
    Then we must:
      | Requirement                              |
      | Obtain explicit consent                  |
      | Explain what emails they'll receive      |
      | Provide easy unsubscribe mechanism       |
      | Not use email for other purposes         |
      | Allow them to withdraw consent anytime   |

  Scenario: Cookie consent (if applicable)
    Given the website uses cookies
    When a user visits
    Then we should:
      | Action                                  |
      | Display cookie banner                   |
      | Explain what cookies are used           |
      | Allow granular consent (essential vs optional)|
      | Respect "Do Not Track" signals          |
      | Provide cookie policy link              |

  # ============================================================================
  # CHILDREN'S DATA PROTECTION
  # ============================================================================

  Scenario: No collection of children's data
    Given the platform is not intended for children under 18
    When data is collected
    Then we should:
      | Action                                  |
      | Not knowingly collect data from minors  |
      | Include age restriction in terms        |
      | Delete data if informed it's a minor    |
    And lawyers (adults) are our data subjects

  # ============================================================================
  # RETENTION AND DELETION POLICIES
  # ============================================================================

  Scenario: Define data retention periods
    When establishing retention policies
    Then the following should apply:
      | Data Type           | Retention Period             | Justification                |
      | Court decisions     | Permanent                    | Public interest, transparency|
      | Lawyer ratings      | Permanent                    | Historical record            |
      | Audit logs          | 5 years                      | Legal compliance             |
      | Dispute records     | 5 years                      | Legal defense                |
      | Analytics data      | 2 years                      | Business need                |
      | Email subscriptions | Until unsubscribe            | User choice                  |

  Scenario: Automated data deletion
    Given retention periods are defined
    When data reaches end of retention period
    Then it should be automatically deleted
    And deletion should be logged
    And backups should also purge expired data
