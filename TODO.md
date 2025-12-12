# CausaGanha v2 Implementation TODO

## Phase 1: Parallel Development

- [x] Create v2 directory structure (`src/causaganha/v2/`, `tests/v2/`)
- [x] Implement PJe API Client (TDD)
    - [x] Test client initialization
    - [x] Implement client initialization
    - [x] Test fetching intimations returns list
    - [x] Implement fetching intimations
    - [x] Test pagination
    - [x] Implement pagination
    - [x] Test error handling
    - [x] Implement error handling
- [x] Implement Ibis Storage Layer (TDD)
    - [x] Create `schema.sql`
    - [x] Create tests for storage connection and schema initialization
    - [x] Implement connection and schema initialization
    - [x] Create tests for storing intimations
    - [x] Implement storing intimations
- [ ] Implement Pydantic AI Analyzer (TDD)
    - [ ] Create tests for analyzer
    - [ ] Implement analyzer
    - [ ] Create tests for batch analysis
    - [ ] Implement batch analysis

## Phase 2: Integration Testing

- [ ] Implement Metadata Collection Pipeline (TDD)
- [ ] Implement Analysis Pipeline (TDD)
- [ ] Implement Rating Calculation integration
- [ ] Create integration tests for full flow

## Phase 3: Gradual Rollout

- [ ] Run parallel collection script
- [ ] Compare v1 and v2 data

## Phase 4: Expansion

- [ ] Add TJMT support
- [ ] Test multi-court support

## Phase 5: Cleanup

- [ ] Remove v1 code
- [ ] Update documentation
