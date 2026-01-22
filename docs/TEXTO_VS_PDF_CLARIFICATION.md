# Texto vs PDF Clarification

**Date:** 2026-01-22
**Status:** IMPLEMENTED ✅

## TL;DR: We Use `texto`, NOT PDFs!

All analysis (RAG, LLM, Hybrid) now uses the **`texto`** field from intimations table.
PDF links are NO LONGER REQUIRED for analysis.

---

## Historical Context

### Old Approach (Deprecated)
```python
# LLM Analyzer used to read PDFs via Gemini's native PDF support
llm_result = await analyzer.analyze_pdf("http://pje.tjro.jus.br/documento/123.pdf")
```

**Problems:**
- ❌ Required PDF URL to be available
- ❌ Network dependency (download PDF every time)
- ❌ Slower (PDF download + processing)
- ❌ More complex (PDF parsing)

### New Approach (Current)
```python
# LLM Analyzer now uses texto field directly
texto = "SENTENÇA\n\nVistos os autos..."
llm_result = await analyzer.analyze_text(texto)
```

**Benefits:**
- ✅ No PDF dependency
- ✅ Works offline (parquet files have texto)
- ✅ Faster (no PDF download)
- ✅ Simpler (direct text processing)

---

## Current Analysis Flow

### Data Source: `intimations` Table

```sql
CREATE TABLE intimations (
    id INTEGER PRIMARY KEY,
    numero_processo TEXT,
    texto TEXT,           -- ✅ Full decision text (what we use!)
    link TEXT,            -- ❌ PDF URL (deprecated for analysis)
    data_disponibilizacao DATE,
    ...
);
```

The `texto` field contains the **full decision text** extracted from the PDF during collection.
This is all we need for analysis!

### Analysis Pipeline

```
Collection Phase:
  PJe API → Download PDF → Extract text → Store in intimations.texto

Analysis Phase:
  intimations.texto → Analyzer → decision_analysis table

  No PDF needed! ✨
```

---

## Updated Analysis Strategies

### 1. RAG Analysis (Cheap, Fast)

```python
# Always used texto (no change)
rag_analyzer = await RAGAnalyzer.create()
result = await rag_analyzer.analyze_text(texto)

# Cost: $0.000008 per decision
# Speed: ~200ms per decision
```

### 2. LLM Analysis (Expensive, Accurate) - NOW USES TEXTO!

```python
# OLD (deprecated):
# llm_analyzer = DecisionAnalyzer()
# result = await llm_analyzer.analyze_pdf("http://example.com/pdf.pdf")

# NEW (current):
llm_analyzer = DecisionAnalyzer()
result = await llm_analyzer.analyze_text(texto)  # ✅ Uses texto!

# Cost: $0.000420 per decision
# Speed: ~2-4 seconds per decision
```

### 3. Hybrid Analysis (Optimal) - NOW USES TEXTO!

```python
# OLD (deprecated):
# hybrid = HybridAnalyzer(rag, llm, threshold=0.70)
# result = await hybrid.analyze_text(texto, pdf_url="http://...")

# NEW (current):
hybrid = HybridAnalyzer(rag, llm, threshold=0.70)
result = await hybrid.analyze_text(texto)  # ✅ No PDF URL needed!

# Flow:
# 1. Try RAG with texto (cheap)
# 2. If confidence < 0.70: use LLM with texto (expensive)
# 3. No PDF download needed at any step!
```

---

## Code Changes Made

### 1. `DecisionAnalyzer` (src/causaganha/v2/analysis/analyzer.py)

```python
class DecisionAnalyzer:
    # NEW: Primary method (uses texto)
    async def analyze_text(self, decision_text: str) -> DecisionAnalysis:
        """Analyze decision from text content."""
        result = await self.agent.run(
            f"Analyze this judicial decision:\n\n{decision_text}"
        )
        return result.data

    # DEPRECATED: Kept for backward compatibility
    async def analyze_pdf(self, pdf_url: str) -> DecisionAnalysis:
        """Deprecated: Use analyze_text() instead."""
        logger.warning("analyze_pdf() is deprecated, use analyze_text()")
        # ... still works but warns

    # UPDATED: Batch method now supports texto
    async def analyze_batch(
        self,
        inputs: list[str],
        input_type: str = "text",  # ✅ Default to "text"
    ) -> list[DecisionAnalysis]:
        """Analyze multiple decisions (text or PDF)."""
        if input_type == "text":
            # Use texto (recommended)
            tasks = [self.analyze_text(text) for text in inputs]
        else:
            # Use PDF (deprecated)
            tasks = [self.analyze_pdf(url) for url in inputs]
        return await asyncio.gather(*tasks)
```

### 2. `HybridAnalyzer` (src/causaganha/v2/analysis/hybrid_analyzer.py)

```python
class HybridAnalyzer:
    async def analyze_text(
        self,
        text: str,
        pdf_url: str | None = None,  # ❌ No longer used!
    ) -> DecisionAnalysis:
        """Analyze using hybrid strategy."""

        # Step 1: Try RAG with texto
        rag_result = await self.rag.analyze_text(text)

        # Step 2: If low confidence, use LLM with texto (not PDF!)
        if rag_result.confidence < self.threshold:
            llm_result = await self.llm.analyze_text(text)  # ✅ Uses texto!
            return llm_result

        return rag_result
```

### 3. `analyze.py` (src/causaganha/v2/pipeline/analyze.py)

```python
async def analyze_pending_decisions(strategy: AnalysisStrategy):
    """Analyze decisions from DuckDB."""

    pending = get_unanalyzed_intimations(con)

    # Extract texts (not PDF URLs!)
    intimation_ids = [p["id"] for p in pending]
    texts = [p.get("texto", "") for p in pending]

    # Analyze using texto
    if strategy == AnalysisStrategy.LLM:
        analyses = await analyzer.analyze_batch(texts, input_type="text")

    elif strategy == AnalysisStrategy.HYBRID:
        analyses = await analyzer.analyze_batch(
            texts,
            intimation_ids,
            pdf_urls=None,  # ✅ No PDFs needed!
        )
```

### 4. `analyze_parquet.py` (src/causaganha/v2/pipeline/analyze_parquet.py)

```python
async def _process_decisions(decisions: list[dict], analyzer, strategy):
    """Process decisions from parquet."""

    # Extract texts from parquet
    texts = [d.get("texto", "") for d in decisions]

    # Analyze using texto (no PDF URLs!)
    if strategy == AnalysisStrategy.LLM:
        analyses = await analyzer.analyze_batch(texts, input_type="text")

    elif strategy == AnalysisStrategy.HYBRID:
        analyses = await analyzer.analyze_batch(
            texts,
            intimation_ids,
            pdf_urls=None,  # ✅ No PDFs needed!
        )
```

---

## Parquet Schema: `link` Field is Deprecated

### Current Parquet Schema

```python
parquet_schema = pa.schema([
    ('intimation_id', pa.int64()),
    ('numero_processo', pa.string()),
    ('texto', pa.string()),            # ✅ USED for analysis
    ('link', pa.string()),              # ⚠️ DEPRECATED for analysis
    ('data_disponibilizacao', pa.date32()),
    # ... analysis results
])
```

### What's `link` Used For Now?

**Nothing for analysis!** We keep it only for:
1. **Reference**: Link back to original PDF on PJe
2. **Audit**: Verify our texto extraction
3. **Re-extraction**: If texto is corrupted, can re-download PDF

But **analysis never touches it** anymore.

---

## Migration Guide for Existing Code

### If You Were Using PDFs:

```python
# OLD CODE (deprecated):
pdf_urls = [intimation["link"] for intimation in intimations]
results = await analyzer.analyze_batch(pdf_urls)

# NEW CODE (current):
texts = [intimation["texto"] for intimation in intimations]
results = await analyzer.analyze_batch(texts, input_type="text")
```

### If You Have Old Parquet Files:

**Good news!** Old parquet files already have `texto` field, so they work immediately:

```python
# Read old parquet file
df = pq.read_table("old-file.parquet").to_pandas()

# Analyze using texto (works!)
for _, row in df.iterrows():
    result = await analyzer.analyze_text(row["texto"])
```

---

## Benefits of Texto-Based Analysis

| Aspect | PDF-based (Old) | Texto-based (New) |
|--------|----------------|-------------------|
| **Speed** | Slow (download + parse) | Fast (direct text) |
| **Network** | Required | Not required |
| **Offline** | ❌ No | ✅ Yes |
| **Parquet** | ❌ Needs link | ✅ Self-contained |
| **Reliability** | ❌ URL can break | ✅ Text always available |
| **Cost** | Same | Same |
| **Accuracy** | Same | Same |

---

## Frequently Asked Questions

### Q: Why did we use PDFs before?

**A:** Originally, Gemini's PDF reading capability seemed like a nice feature (pass URL, Gemini downloads and reads it). But it added unnecessary complexity and network dependency.

### Q: Does texto have all the information from the PDF?

**A:** Yes! The `texto` field is extracted from the PDF during collection. It contains the full decision text that was in the PDF.

### Q: What if texto is missing or empty?

**A:** Analysis will return low confidence or error. This is rare since collection validates texto before storing.

### Q: Can I still use PDFs if I want to?

**A:** Yes, `analyze_pdf()` still exists for backward compatibility, but it's deprecated and logs a warning.

### Q: Will old code break?

**A:** No! `analyze_pdf()` still works. But you'll see deprecation warnings in logs. Update to `analyze_text()` when convenient.

---

## Summary of Changes

✅ **Added**: `DecisionAnalyzer.analyze_text()` - primary method using texto
✅ **Deprecated**: `DecisionAnalyzer.analyze_pdf()` - still works but warns
✅ **Updated**: `HybridAnalyzer` - uses texto for LLM fallback, no PDFs
✅ **Updated**: `analyze.py` - passes texto to analyzers
✅ **Updated**: `analyze_parquet.py` - passes texto to analyzers
✅ **Clarified**: Documentation now correctly states we use texto

**Result:** All analysis now uses `texto` field. PDFs are no longer required! 🎉

---

## Related Documentation

- [Parquet Format Improvements](PARQUET_FORMAT_IMPROVEMENTS.md) - Schema v2 proposals
- [Parquet Analysis Adaptation Plan](plans/parquet-analysis-adaptation.md) - Implementation plan
- [Lawyer Enrichment Explained](LAWYER_ENRICHMENT_EXPLAINED.md) - Schema v2 features

---

**Last Updated:** 2026-01-22
**Status:** Implemented and tested ✅
