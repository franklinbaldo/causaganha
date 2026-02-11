# PR #254 Merge Analysis

**PR**: https://github.com/franklinbaldo/causaganha/pull/254
**Current branch**: `claude/analyze-architecture-3klSy`
**Common ancestor**: `22086ed` (2026-01-22 - PR #253 merge)

---

## 📊 PR Overview

### Title
"Improved RAG with Ground Truth Labeling and Local Embeddings"

### Commits (10 total)
```
2c420a1 feat: add test script for improved RAG on 490 documents
bead65e fix: add HTML cleaning to agent labeling scripts
69e5f4f feat: aggregate 998 labeled outcomes from 10 agents
0d62ab2 feat: add agent labeling scripts for 1000 document outcome extraction
654c179 feat: add merit decision query and outcome-only labeling
d904b6f feat: add procedural document filter with 85% accuracy
5a4d734 feat: add subagent helper scripts for ground truth labeling
a10da41 docs: add rich ground truth extraction schema and subagent prompt
6abbb2d feat: add dynamic sliding window chunking to improved RAG
5ffd971 feat: implement improved RAG with structured party data
```

---

## 📂 Changed Files (50+ files)

### New Source Files (in `src/causaganha/v2/analysis/`)
```
✅ dynamic_phrase_builder.py         (249 lines) - Dynamic phrase chunking
✅ heuristic_classifier.py           (397 lines) - Heuristic outcome classifier
✅ improved_rag_analyzer.py          (242 lines) - Improved RAG implementation
✅ parquet_party_loader.py           (169 lines) - Structured party data loader
✅ procedural_doc_filter.py          (261 lines) - Filter procedural docs (85% accuracy)
✅ situation_classifier.py           (NEW) - Situation classification
```

### Modified Source Files
```
⚠️ config.py                         - Added new configs
⚠️ v2/analysis/embedding_models.py   - Added local models
⚠️ v2/analysis/providers.py          - Added LocalProvider (+ ~200 lines)
```

### New Scripts (40+)
```
✅ scripts/agent_{2,3,4,5,6,8,10}_labeling.py  - Ground truth labeling
✅ scripts/aggregate_outcomes.py               - Aggregate labels from agents
✅ scripts/benchmark_*.py                      - Various benchmarks
✅ scripts/test_*.py                           - Testing scripts
✅ scripts/label_*.py                          - Labeling workflows
✅ scripts/query_*.py                          - Query utilities
```

### New Documentation (9 files)
```
✅ docs/experiments/README.md
✅ docs/experiments/embedding-quality-benchmark-guide.md        (297 lines)
✅ docs/experiments/ground-truth-accuracy-results.md            (191 lines)
✅ docs/experiments/heuristic-vs-rag-comparison.md              (318 lines)
✅ docs/experiments/local-embeddings-experiment.md              (369 lines)
✅ docs/experiments/real-data-test-results.md                   (220 lines)
✅ docs/experiments/improved-rag-with-dynamic-phrases-FINAL.md  (322 lines)
✅ docs/plans/rich-ground-truth-extraction-schema.md            (532 lines)
```

---

## 🔍 Key Features Added

### 1. **Improved RAG Analyzer** (`improved_rag_analyzer.py`)
- Dynamic phrase-based chunking (instead of fixed-size chunks)
- Structured party data loader from Parquet
- Better accuracy by matching party-specific phrases
- Integrated with existing RAG workflow

### 2. **Local Embeddings Support** (`LocalProvider`)
- CPU-optimized embeddings using sentence-transformers
- Models:
  - `intfloat/multilingual-e5-small` (384D, multilingual)
  - `neuralmind/bert-base-portuguese-cased` (768D, Portuguese-specific)
- No API costs (runs locally)
- Auto-selection priority: `["local", "jina", "google"]`

### 3. **Ground Truth Labeling System**
- **10 agent labeling scripts** for creating ground truth
- **998 labeled outcomes** aggregated from multiple agents
- **Merit decision filter** to exclude procedural documents
- **Procedural doc filter** with 85% accuracy

### 4. **Heuristic Classifier** (`heuristic_classifier.py`)
- Rule-based outcome classification
- Useful for comparison with RAG/LLM
- Benchmarking baseline

### 5. **Extensive Benchmarking**
- Embedding quality tests
- Winner/loser accuracy tests
- RAG vs Heuristic comparisons
- Real data test results

---

## ⚠️ CONFLICTS with Current Branch

### Path Conflicts (CRITICAL)

**PR uses**: `src/causaganha/v2/analysis/*`
**Our branch**: Moved `v2/` → root (`src/causaganha/analysis/*`)

**Affected files**:
```
PR #254                                    Our Branch
────────────────────────────────────────   ─────────────────────────────────
v2/analysis/dynamic_phrase_builder.py  →  analysis/dynamic_phrase_builder.py
v2/analysis/heuristic_classifier.py    →  analysis/heuristic_classifier.py
v2/analysis/improved_rag_analyzer.py   →  analysis/improved_rag_analyzer.py
v2/analysis/parquet_party_loader.py    →  analysis/parquet_party_loader.py
v2/analysis/procedural_doc_filter.py   →  analysis/procedural_doc_filter.py
v2/analysis/situation_classifier.py    →  analysis/situation_classifier.py
v2/analysis/embedding_models.py        →  analysis/embedding_models.py
v2/analysis/providers.py               →  analysis/providers.py
```

### Content Conflicts

#### 1. `analysis/providers.py`
```diff
PR #254:
+ class LocalProvider(EmbeddingProviderBase)
+ async def auto_select_provider(priority=["local", "jina", "google"])

Our Branch:
+ async def auto_select_provider(priority=["jina", "google"])  # No local yet
```

**Resolution**: Merge LocalProvider into our branch, update priority.

---

#### 2. `analysis/embedding_models.py`
```diff
PR #254:
+ LOCAL_MODELS = {
+     "intfloat/multilingual-e5-small": EmbeddingModel(...),
+     "neuralmind/bert-base-portuguese-cased": EmbeddingModel(...),
+ }

Our Branch:
# No local models yet
```

**Resolution**: Add local models to our branch.

---

#### 3. `config.py`
```diff
PR #254:
+ EMBEDDING_PROVIDER_PRIORITY: list[str] = ["local", "jina", "google"]

Our Branch:
+ EMBEDDING_PROVIDER_PRIORITY: list[str] = ["jina", "google"]
```

**Resolution**: Update priority to include local.

---

## 🎯 Merge Strategy

### Option 1: **Cherry-pick + Path Update** (RECOMMENDED)

**Approach**:
1. Create feature branch from current: `git checkout -b feature/improved-rag-from-pr254`
2. Cherry-pick commits from PR #254 one by one
3. For each commit, update paths: `v2/analysis/` → `analysis/`
4. Resolve conflicts manually
5. Test thoroughly
6. Merge to `claude/analyze-architecture-3klSy`

**Pros**:
- ✅ Preserves PR #254 commits history
- ✅ Full control over conflict resolution
- ✅ Can skip unwanted changes

**Cons**:
- ⚠️ Manual work (10 commits)
- ⚠️ Path updates needed for each commit

**Commands**:
```bash
# 1. Create feature branch
git checkout -b feature/improved-rag-from-pr254 claude/analyze-architecture-3klSy

# 2. Cherry-pick commits (oldest to newest)
git cherry-pick 5ffd971  # implement improved RAG
# Fix paths: v2/analysis → analysis
git add -A && git cherry-pick --continue

git cherry-pick 6abbb2d  # dynamic sliding window
# Fix paths again
git add -A && git cherry-pick --continue

# ... repeat for all 10 commits

# 3. Test
uv run pytest tests/ -v

# 4. Merge back
git checkout claude/analyze-architecture-3klSy
git merge feature/improved-rag-from-pr254
```

---

### Option 2: **Merge + Mass Path Rename**

**Approach**:
1. Merge PR #254 into current branch: `git merge pr-254`
2. Accept all conflicts keeping PR #254 version
3. Mass rename: `git mv src/causaganha/v2/* src/causaganha/`
4. Update all imports in new files
5. Test and fix

**Pros**:
- ✅ Faster (single merge)
- ✅ All changes at once

**Cons**:
- ❌ Messy merge history
- ❌ Harder to debug if something breaks
- ❌ Risk of breaking existing code

---

### Option 3: **Manual File Copy + Attribution**

**Approach**:
1. Manually copy new files from PR #254
2. Update paths during copy
3. Add commit with co-authored-by attribution
4. Skip git history from PR

**Pros**:
- ✅ Clean history
- ✅ Full control

**Cons**:
- ❌ Loses PR commit history
- ❌ Manual work

---

## 🔧 Detailed Merge Steps (Option 1 - Recommended)

### Phase 1: Setup
```bash
# Fetch PR
git fetch origin pull/254/head:pr-254

# Create feature branch
git checkout -b feature/improved-rag-from-pr254 claude/analyze-architecture-3klSy

# Verify base
git log --oneline -5
```

### Phase 2: Cherry-pick Commits (10 commits)

#### Commit 1: `5ffd971` - Implement improved RAG
```bash
git cherry-pick 5ffd971

# Expected conflicts:
# - src/causaganha/v2/analysis/improved_rag_analyzer.py (NEW)
# - src/causaganha/v2/analysis/parquet_party_loader.py (NEW)

# Fix:
git mv src/causaganha/v2/analysis/improved_rag_analyzer.py src/causaganha/analysis/
git mv src/causaganha/v2/analysis/parquet_party_loader.py src/causaganha/analysis/

# Update imports in new files
sed -i 's/from causaganha.v2./from causaganha./g' src/causaganha/analysis/improved_rag_analyzer.py
sed -i 's/from causaganha.v2./from causaganha./g' src/causaganha/analysis/parquet_party_loader.py

git add -A
git cherry-pick --continue
```

#### Commit 2: `6abbb2d` - Dynamic sliding window
```bash
git cherry-pick 6abbb2d

# Fix:
git mv src/causaganha/v2/analysis/dynamic_phrase_builder.py src/causaganha/analysis/
sed -i 's/from causaganha.v2./from causaganha./g' src/causaganha/analysis/dynamic_phrase_builder.py

git add -A
git cherry-pick --continue
```

#### Commit 3: `a10da41` - Docs (no conflicts)
```bash
git cherry-pick a10da41
# Should apply cleanly (only docs/)
```

#### Commit 4: `5a4d734` - Subagent scripts (no conflicts)
```bash
git cherry-pick 5a4d734
# Should apply cleanly (only scripts/)
```

#### Commit 5: `d904b6f` - Procedural filter
```bash
git cherry-pick d904b6f

# Fix:
git mv src/causaganha/v2/analysis/procedural_doc_filter.py src/causaganha/analysis/
sed -i 's/from causaganha.v2./from causaganha./g' src/causaganha/analysis/procedural_doc_filter.py

git add -A
git cherry-pick --continue
```

#### Commit 6: `654c179` - Merit decision query (scripts only)
```bash
git cherry-pick 654c179
# Should apply cleanly
```

#### Commit 7: `0d62ab2` - Agent labeling scripts
```bash
git cherry-pick 0d62ab2
# Should apply cleanly (only scripts/)
```

#### Commit 8: `69e5f4f` - Aggregate outcomes
```bash
git cherry-pick 69e5f4f
# Should apply cleanly (only scripts/)
```

#### Commit 9: `bead65e` - HTML cleaning
```bash
git cherry-pick bead65e
# Should apply cleanly (only scripts/)
```

#### Commit 10: `2c420a1` - Test script
```bash
git cherry-pick 2c420a1
# Should apply cleanly (only scripts/)
```

### Phase 3: Merge Provider Changes

**Conflict**: `analysis/providers.py` - Add LocalProvider

```bash
# Manually merge LocalProvider from PR #254
# Current file: analysis/providers.py (has JinaProvider, GoogleProvider)
# PR file: v2/analysis/providers.py (has JinaProvider, GoogleProvider, LocalProvider)

# Strategy: Copy LocalProvider class from PR
git show pr-254:src/causaganha/v2/analysis/providers.py > /tmp/pr_providers.py

# Extract LocalProvider class (lines 332-527)
# Paste into our analysis/providers.py

# Update create_provider():
# Add: if provider == "local": return LocalProvider()

# Update auto_select_provider():
# Change priority default: ["local", "jina", "google"]
```

### Phase 4: Merge Embedding Models

**Conflict**: `analysis/embedding_models.py` - Add local models

```bash
# Extract LOCAL_MODELS from PR
git show pr-254:src/causaganha/v2/analysis/embedding_models.py > /tmp/pr_models.py

# Copy LOCAL_MODELS dict and related functions to our embedding_models.py
```

### Phase 5: Update Config

```bash
# config.py: Update default priority
# Change: EMBEDDING_PROVIDER_PRIORITY = ["jina", "google"]
# To:     EMBEDDING_PROVIDER_PRIORITY = ["local", "jina", "google"]
```

### Phase 6: Test

```bash
# Install sentence-transformers (for local embeddings)
uv add sentence-transformers

# Run tests
uv run pytest tests/v2/analysis/test_embedding_providers.py -v

# Test improved RAG
uv run python scripts/test_improved_rag_490.py

# Test CLI
uv run causaganha --help
```

### Phase 7: Cleanup and Merge

```bash
# Commit any manual fixes
git add -A
git commit -m "chore: finalize PR #254 merge with path updates"

# Switch back and merge
git checkout claude/analyze-architecture-3klSy
git merge feature/improved-rag-from-pr254

# Push
git push -u origin claude/analyze-architecture-3klSy
```

---

## 📋 Checklist

### Before Merge
- [ ] Review all 10 commits from PR #254
- [ ] Understand LocalProvider implementation
- [ ] Review improved_rag_analyzer.py logic
- [ ] Check dependencies (sentence-transformers)

### During Merge
- [ ] Cherry-pick all 10 commits
- [ ] Fix path conflicts (v2/ → root)
- [ ] Update imports in new files
- [ ] Manually merge LocalProvider
- [ ] Manually merge LOCAL_MODELS
- [ ] Update config.py priority
- [ ] Update CLAUDE.md if needed

### After Merge
- [ ] Run tests: `uv run pytest tests/ -v`
- [ ] Test improved RAG: `uv run python scripts/test_improved_rag_490.py`
- [ ] Test local embeddings: `uv run python -c "from causaganha.analysis.providers import LocalProvider"`
- [ ] Update documentation if needed
- [ ] Push to remote

---

## 🎯 Recommendation

**PROCEED with Option 1 (Cherry-pick + Path Update)**

**Rationale**:
1. ✅ Preserves PR history (good attribution)
2. ✅ Full control over conflicts
3. ✅ Can test each commit
4. ✅ Clean final result

**Estimated time**: 2-3 hours

**Risk level**: 🟡 Medium (manual path updates needed)

---

## 🚨 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Import errors after path change | High | High | Update all imports, test thoroughly |
| LocalProvider breaks existing code | Low | Medium | Keep auto-select priority (local is first) |
| Test failures | Medium | Medium | Run full test suite after merge |
| Conflicts with future PRs | Low | Low | Document path migration in commit message |

---

## 📝 Next Steps

1. **Review this analysis**
2. **Decide on merge strategy** (Option 1 recommended)
3. **Execute merge** (follow Phase 1-7 steps)
4. **Test thoroughly**
5. **Update documentation**
6. **Close PR #254** (or keep open if issues found)

---

**Status**: ⏳ Ready for merge execution
**Author**: Claude (Architecture Analysis)
**Date**: 2026-01-23
