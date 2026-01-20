---
title: "🧑‍🌾 Historical Archive"
date: 2025-12-23
author: "Shepherd"
emoji: "🧑‍🌾"
type: journal
---

# Shepherd's Journal - Coverage Improvement Learnings

This journal tracks critical learnings from coverage improvement sessions.

## Format
```
## YYYY-MM-DD - Coverage: XX% → YY% (+Z.Z%)
**Files Tested:** [module names]
**Key Behaviors:** [What behaviors were tested?]
**Obstacles:** [What made testing difficult?]
**Solutions:** [How did you overcome them?]
```

---

## 2025-12-23 - Coverage: 35% → 39% (Initial Baseline)
**Files Tested:** Initial baseline established
**Key Behaviors:** N/A - baseline measurement
**Obstacles:**
- Coverage was measured with statement coverage only (43.91%)
- CI uses branch coverage (--cov-branch) which is stricter (39.24%)
- Mismatch caused CI failures
**Solutions:**
- Set threshold to 39% to match branch coverage
- Added --cov-branch to pre-commit configuration
- Documented difference between statement vs branch coverage

**Note:** Branch coverage requires testing BOTH branches of if/else statements, not just executing the if statement. This is why it's lower than statement coverage.

---

## 2026-01-04 - RAG Module Coverage: 64% → 77% (+13.27%)
**Files Tested:** `src/egregora/rag/embeddings.py` (0% → 85.42%)
**Key Behaviors:**
- API key resolution (`is_rag_available`, environment variable fallback)
- Embedding vector generation (768-dimensional outputs)
- Error handling (rate limits, API errors, validation errors)
- Batch processing (empty lists, multiple texts)
- Task type specification (RETRIEVAL_QUERY for queries)

**Obstacles:**
- `embed_query_text()` implementation detail: Uses batch endpoint internally
- Initial tests mocked single endpoint (`:embedContent`) but function calls batch endpoint (`:batchEmbedContents`)
- AllMockedAssertionError revealed the implementation gap

**Solutions:**
- Read implementation before writing tests (violated initial assumption)
- Changed mocks to match actual endpoint (`:batchEmbedContents`)
- Focused on WHAT the function does (returns 768-dim vector) not HOW (batch vs single)
- Used `respx` to verify request bodies contain expected task types

**Learning:**
- Behavioral testing doesn't mean ignoring implementation
- Must understand WHICH endpoints are called to mock correctly
- Reading source code is essential even for behavioral tests
- respx.mock allows verifying request content (task types, params)
