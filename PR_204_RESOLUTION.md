# PR #204 Resolution

## Status: Superseded by PR #205

This PR (#204) has been superseded by PR #205 which was merged on 2026-01-16 via commit `5b3a9e5`.

## Background

Both PR #204 and PR #205 implement the same ML winner prediction feature for CausaGanha, but with different architectural approaches:

### PR #205 (Merged) - More Complete Implementation

**Components:**
- `WinnerClassifierRunner` - High-level orchestrator for the ML subsystem
- `DBBootstrapper` - Bootstrap model training from historical database decisions
- `EmbeddingCache` - SQLite-based caching to reduce API calls
- `GeminiEmbedder` - Async embedding generation with caching support
- `WinnerPredictor` - Online learning model with versioning and atomic saves
- `LLMTeacher` - Teacher LLM for labeling decisions
- Type system with proper enums (`WinnerClassifierMode`, `WinnerBootstrapMode`, `WinnerLabel`)

**Features:**
- Bootstrap modes: OFF, AUTO, FORCE
- Model versioning with MD5 hashes
- Atomic model saves to prevent corruption
- Embedding cache to reduce API costs
- Integrated into CLI with proper options
- Full integration into analysis pipeline

### PR #204 (This PR) - Simpler Implementation

**Components:**
- Direct integration without runner abstraction
- `WorkerPool` for parallel processing
- `StandardScaler` in predictor
- Simpler embedding without caching
- Basic integration into pipeline

## Merge Conflicts

When attempting to merge PR #204 into current main, the following conflicts occurred:
- `src/causaganha/application/pipeline/analyze.py` - Different integration approaches
- `src/causaganha/cli.py` - Different CLI parameter signatures
- `src/causaganha/ml/embeddings.py` - Caching vs non-caching implementations
- `src/causaganha/ml/online_learner.py` - Different model management approaches
- `src/causaganha/ml/teacher.py` - Similar but incompatible implementations
- `tests/features/winner_prediction.feature` - Different BDD scenarios

## Recommendation

**PR #204 should be closed** as the functionality it provides is already implemented in a more complete form via PR #205.

The winner prediction ML feature is now available in main with the following CLI usage:

```bash
# Inference mode (use existing model)
uv run causaganha analyze --winner-classifier=infer

# Teaching mode (train model with LLM labels)
uv run causaganha analyze --winner-classifier=teach

# With bootstrap from historical data
uv run causaganha analyze --winner-classifier=teach --winner-bootstrap=auto --winner-bootstrap-limit=5000
```

## Files Currently in Main (from PR #205)

```
src/causaganha/ml/
├── __init__.py
├── bootstrap.py         # Bootstrap from historical DB data
├── embeddings.py        # Embedder with caching
├── online_learner.py    # Online learning predictor
├── runner.py            # High-level orchestrator
├── teacher.py           # LLM teacher for labeling
└── types.py             # Type definitions and enums
```

## Critical Issue Identified

### Current Implementation Embeds LLM Results, Not Raw Text

The current implementation (PR #205) has an architectural issue:

**Current behavior** (src/causaganha/application/pipeline/analyze.py:77-78):
```python
# Construct text for embedding/teacher from analysis result
# Using summary + reasoning as proxy for decision text
text_context = f"{analysis.summary}\n\n{analysis.decision_reasoning}"
ml_result = await winner_runner.process_decision(text_context)
```

**Problem:**
- Embeds the LLM analysis results (summary + reasoning), NOT the raw intimação text
- The expensive LLM call happens BEFORE embedding
- Defeats the stated purpose: "scale analysis without always invoking an expensive LLM"
- Cannot use ML to skip or replace LLM analysis

**PR #204's approach:**
```python
pdf_text = " ".join(await doc_service.extract_text_from_pdf(pdf_bytes))
embedding = await ml_components["embedder"].embed_text(pdf_text)
```

**Recommended fix:**
The ML classifier should embed and analyze the raw PDF text, not the LLM output. This would allow:
1. Using ML predictions to skip expensive LLM calls for some decisions
2. Running ML and LLM in parallel for comparison
3. True cost optimization by reducing LLM usage

## Conclusion

While PR #205 provides a more complete architectural framework (runner, bootstrapper, caching), it has a critical flaw in what it embeds. PR #204's approach of embedding raw PDF text is architecturally correct for the stated use case.

**Action needed:** Fix the current implementation to embed raw PDF text instead of LLM analysis results.
