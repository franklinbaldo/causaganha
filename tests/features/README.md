# BDD Feature Suite - CausaGanha

This directory contains Behavior-Driven Development (BDD) features for the CausaGanha judicial decision analysis platform. Features are organized by priority based on their importance to the core value proposition.

## Feature Hierarchy

### 🔴 Priority 1: Core Business Value
These features represent the fundamental value proposition of CausaGanha - without these, the platform cannot function.

1. **`01_data_collection.feature`** - Automated collection of judicial decisions from Brazilian tribunals via PJe API
2. **`02_decision_analysis.feature`** - AI-powered extraction of structured information from decisions using LLM
3. **`03_lawyer_scoring.feature`** - Dynamic lawyer performance ratings using OpenSkill algorithm

### 🟡 Priority 2: Essential Operations
These features enable the core business features to work properly and provide essential support functions.

4. **`04_document_archival.feature`** - Long-term preservation of decisions to Internet Archive
5. **`05_pipeline_orchestration.feature`** - End-to-end workflow from collection to scoring

### 🟢 Priority 3: Advanced Capabilities
These features optimize costs, enable scale, and improve system resilience.

6. **`06_winner_prediction.feature`** - ML-based outcome prediction to reduce LLM costs
7. **`07_multi_court_coverage.feature`** - Support for 90+ Brazilian tribunals
8. **`08_error_handling.feature`** - Graceful failure handling and recovery

### 🔵 Priority 4: Quality & Operations
These features ensure data quality, system performance, and operational excellence.

9. **`09_data_quality.feature`** - Validation of extracted legal data accuracy
10. **`10_performance_monitoring.feature`** - System observability and performance tracking

## Running BDD Tests

```bash
# Run all features
uv run pytest tests/features/

# Run specific priority level
uv run pytest tests/features/01_*.feature
uv run pytest tests/features/02_*.feature

# Run specific feature
uv run pytest tests/features/01_data_collection.feature

# Run with coverage
uv run pytest tests/features/ --cov=causaganha
```

## Writing New Features

Follow Gherkin syntax:
- **Feature**: Business capability description
- **Background**: Common setup for all scenarios
- **Scenario**: Specific behavior example
- **Given**: Initial context
- **When**: Action/event
- **Then**: Expected outcome

Example:
```gherkin
Feature: Lawyer Performance Ratings
  As a legal professional
  I want to see transparent lawyer performance ratings
  So that I can make informed decisions about legal representation

  Scenario: New lawyer wins first case
    Given a new lawyer "João Silva" with OAB "12345/SP"
    And the lawyer has no prior rating
    When the lawyer wins their first case
    Then the lawyer should have a rating above the default baseline
    And the rating confidence should be low due to limited data
```

## Feature Organization Principles

1. **Business Value First**: Features are ordered by their impact on end users
2. **Clear Scenarios**: Each scenario tests one specific behavior
3. **Domain Language**: Use legal/business terminology, not technical jargon
4. **Testable**: Each scenario can be implemented with step definitions
5. **Independent**: Scenarios should not depend on each other

## Stakeholder Mapping

| Priority | Stakeholder | Key Question Answered |
|----------|-------------|----------------------|
| P1 | Legal Professionals | "Can I trust the lawyer ratings?" |
| P1 | Lawyers | "How is my performance measured?" |
| P2 | Auditors | "Are decisions preserved permanently?" |
| P2 | Operations | "Does the system run reliably?" |
| P3 | Product Team | "How do we scale to 90+ courts?" |
| P4 | Data Analysts | "Is the extracted data accurate?" |

## Coverage Goals

- **Critical (P1)**: 90%+ scenario coverage
- **Essential (P2)**: 80%+ scenario coverage
- **Advanced (P3)**: 70%+ scenario coverage
- **Quality (P4)**: 60%+ scenario coverage

## Next Steps

1. Implement step definitions in `tests/step_defs/`
2. Create fixtures in `tests/conftest.py`
3. Add integration tests for each feature
4. Monitor coverage and add scenarios for edge cases
