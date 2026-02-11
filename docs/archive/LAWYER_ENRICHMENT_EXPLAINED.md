# Lawyer Enrichment & Confidence Breakdown - Explained

**Status:** Proposal for Schema v2
**Priority:** P2 (Medium)
**Impact:** Self-contained analysis, targeted reanalysis

## The Problem with Current Schema (v1)

### What We Store Now

```python
# Current parquet schema - MINIMAL lawyer info
{
    "intimation_id": 12345,
    "numero_processo": "0000123-45.2025.8.22.0001",
    "texto": "SENTENÇA\n\nVISTO...",  # Full decision text

    # Just OAB numbers - no context
    "winner_lawyer_oab": "5733",
    "winner_lawyer_state": "RO",
    "loser_lawyer_oab": "8456",
    "loser_lawyer_state": "RO",

    "outcome": "procedente",
    "confidence_score": 0.72  # Single number, but why 0.72?
}
```

### What's Missing?

**Question 1:** Who is lawyer "5733"?
- ❌ No name (just a number)
- ❌ No experience level
- ❌ No skill rating
- ❌ No historical performance

**Question 2:** Why is confidence 0.72?
- ❌ Can't tell which part of analysis was uncertain
- ❌ Don't know if we should reanalyze
- ❌ Can't improve specific weak points

**Question 3:** Was this an "upset" victory?
- ❌ Can't tell if winner was underdog
- ❌ No context about relative skill levels

---

## Proposed Solution: Lawyer Enrichment

### Add Full Lawyer Profile to Parquet

```python
# Schema v2 - ENRICHED lawyer info
{
    "intimation_id": 12345,
    "numero_processo": "0000123-45.2025.8.22.0001",
    "texto": "SENTENÇA\n\nVISTO...",

    # Winner lawyer - FULL PROFILE
    "winner_lawyer": {
        "oab": "5733",
        "state": "RO",
        "name": "João Silva",           # 👈 NEW: Human-readable
        "rating": 1425.5,                # 👈 NEW: Skill level (OpenSkill μ)
        "sigma": 82.3,                   # 👈 NEW: Uncertainty (OpenSkill σ)
        "total_cases": 145,              # 👈 NEW: Experience
        "wins": 104,                     # 👈 NEW: Track record
        "losses": 41,
        "win_rate": 0.72,                # 👈 NEW: Win percentage
        "tribunal_rating": 1380.2,       # 👈 NEW: TJRO-specific rating
        "global_rating": 1425.5,         # 👈 NEW: All tribunals
        "rating_rank": 342,              # 👈 NEW: Rank among all lawyers
        "rating_percentile": 0.78        # 👈 NEW: Top 22% of lawyers
    },

    # Loser lawyer - FULL PROFILE
    "loser_lawyer": {
        "oab": "8456",
        "state": "RO",
        "name": "Maria Santos",
        "rating": 1580.3,                # 👈 HIGHER than winner!
        "sigma": 65.1,
        "total_cases": 230,              # 👈 MORE experienced
        "wins": 156,
        "losses": 74,
        "win_rate": 0.68,
        "tribunal_rating": 1620.5,
        "global_rating": 1580.3,
        "rating_rank": 156,
        "rating_percentile": 0.91        # 👈 Top 9% lawyer!
    },

    "outcome": "procedente",

    # Confidence breakdown - PER COMPONENT
    "confidence_breakdown": {
        "overall": 0.72,
        "winner_identification": 0.95,   # Very confident
        "loser_identification": 0.90,    # Very confident
        "outcome_classification": 0.85,  # Confident
        "decision_type": 0.50,           # NOT confident
        "judge_extraction": 0.40         # Low confidence
    }
}
```

---

## Real-World Use Cases

### Use Case 1: Find Upset Victories (Underdog Wins)

**Scenario:** Lower-rated lawyer beat higher-rated lawyer

```python
import pyarrow.parquet as pq

# Read parquet with enriched data
df = pq.read_table("causaganha-2025-01-15-TJRO.parquet").to_pandas()

# Find upset victories
upsets = df[
    (df['winner_lawyer'].apply(lambda x: x['rating']) <
     df['loser_lawyer'].apply(lambda x: x['rating']))
]

print(f"Found {len(upsets)} upset victories")

# Example output:
# Case 0000123-45: João Silva (1425) beat Maria Santos (1580)
#   - Rating difference: -154.8 points
#   - Winner was underdog (78th percentile vs 91st percentile)
#   - Confidence: 0.72 (might be error?)
```

**Why This Matters:**
- Identify potential analysis errors (low-rated winning might be wrong)
- Find exceptional performances (underdog genuinely won)
- Adjust ratings with context (upset victories worth more points)

### Use Case 2: Experience-Based Analysis

**Scenario:** How does experience affect outcomes?

```python
# Compare experienced vs inexperienced lawyers
df['winner_cases'] = df['winner_lawyer'].apply(lambda x: x['total_cases'])
df['loser_cases'] = df['loser_lawyer'].apply(lambda x: x['total_cases'])

# Group by experience bracket
experience_analysis = df.groupby(
    pd.cut(df['winner_cases'], bins=[0, 50, 100, 200, 500, 1000])
).agg({
    'outcome': 'count',
    'confidence_score': 'mean'
})

# Results might show:
# 0-50 cases: 23 decisions, avg confidence 0.68 (less confident with new lawyers)
# 50-100 cases: 45 decisions, avg confidence 0.75
# 100-200 cases: 67 decisions, avg confidence 0.82
# 200-500 cases: 34 decisions, avg confidence 0.85 (more confident with veterans)
```

**Why This Matters:**
- Our analysis is LESS confident with new lawyers (might need improvement)
- Can weight decisions based on lawyer experience
- Identify if we're biased toward/against new lawyers

### Use Case 3: Targeted Reanalysis

**Scenario:** Reanalyze only low-confidence decisions with high stakes

```python
# Find decisions that need reanalysis
reanalyze_candidates = df[
    # Low overall confidence
    (df['confidence_breakdown'].apply(lambda x: x['overall']) < 0.70) &

    # BUT only where winner identification was uncertain
    (df['confidence_breakdown'].apply(lambda x: x['winner_identification']) < 0.80) &

    # High-stakes: Both lawyers are highly rated
    (df['winner_lawyer'].apply(lambda x: x['rating']) > 1400) &
    (df['loser_lawyer'].apply(lambda x: x['rating']) > 1400)
]

print(f"Reanalyze {len(reanalyze_candidates)} high-stakes uncertain decisions")

# Can now reanalyze ONLY these specific cases instead of everything
causaganha parquet analyze ./file.parquet \
    --filter-ids $(echo ${reanalyze_candidates['intimation_id'].tolist()}) \
    --strategy llm  # Use expensive LLM for these important cases
```

**Why This Matters:**
- Don't waste money reanalyzing everything
- Focus resources on important uncertain cases
- Improve where it matters most

### Use Case 4: Historical Tracking

**Scenario:** Track how lawyer performance changed after this decision

```python
# This decision shows lawyer rating AT THE TIME
decision_date = "2025-01-15"
lawyer_oab = "5733"

# Parquet snapshot: João Silva was rated 1425.5 on 2025-01-15
historical_rating = 1425.5

# Current database: João Silva is now rated 1520.3
current_rating = db.query(
    "SELECT rating FROM lawyer_ratings WHERE oab = ? AND state = ?",
    (lawyer_oab, "RO")
).scalar()

rating_change = current_rating - historical_rating
print(f"João Silva improved +{rating_change:.1f} points since {decision_date}")

# Find the decision that caused the biggest rating jump
# (This specific win might have been worth +50 points!)
```

**Why This Matters:**
- Understand rating trajectories over time
- Identify pivotal decisions that changed careers
- Validate rating algorithm (did this win boost rating appropriately?)

### Use Case 5: Quality Diagnostics

**Scenario:** Which part of our analysis is weakest?

```python
# Aggregate confidence across all decisions
confidence_stats = {
    'winner_id': df['confidence_breakdown'].apply(lambda x: x['winner_identification']).mean(),
    'loser_id': df['confidence_breakdown'].apply(lambda x: x['loser_identification']).mean(),
    'outcome': df['confidence_breakdown'].apply(lambda x: x['outcome_classification']).mean(),
    'decision_type': df['confidence_breakdown'].apply(lambda x: x['decision_type']).mean(),
    'judge': df['confidence_breakdown'].apply(lambda x: x['judge_extraction']).mean()
}

print("Analysis Quality by Component:")
for component, avg_conf in sorted(confidence_stats.items(), key=lambda x: x[1]):
    print(f"  {component:20s}: {avg_conf:.2%}")

# Output:
#   judge               : 42%  ← WEAKEST: Need to improve judge extraction
#   decision_type       : 58%  ← Need work
#   outcome             : 83%  ← Good
#   loser_id            : 89%  ← Very good
#   winner_id           : 94%  ← Excellent
```

**Why This Matters:**
- Focus improvement efforts on weak components (judge extraction)
- Measure impact of changes (did new prompt improve decision_type?)
- Set different confidence thresholds per component

---

## Implementation: How to Add This

### Step 1: Modify Parquet Export

**File:** `src/causaganha/v2/pipeline/parquet_export.py`

```python
# Current export query (v1)
query = """
    SELECT
        i.intimation_id,
        i.texto,
        da.winner_lawyer_oab,
        da.winner_lawyer_state,
        da.loser_lawyer_oab,
        da.loser_lawyer_state,
        da.confidence_score
    FROM intimations i
    LEFT JOIN decision_analysis da ON i.id = da.intimation_id
"""

# NEW: Join with lawyer_ratings table
query = """
    SELECT
        i.intimation_id,
        i.texto,

        -- Winner lawyer (enriched)
        da.winner_lawyer_oab,
        da.winner_lawyer_state,
        lr_winner.lawyer_name as winner_name,
        lr_winner.rating as winner_rating,
        lr_winner.sigma as winner_sigma,
        lr_winner.total_cases as winner_cases,
        lr_winner.wins as winner_wins,
        lr_winner.losses as winner_losses,
        lr_winner.win_rate as winner_win_rate,

        -- Loser lawyer (enriched)
        da.loser_lawyer_oab,
        da.loser_lawyer_state,
        lr_loser.lawyer_name as loser_name,
        lr_loser.rating as loser_rating,
        -- ... similar fields

        -- Confidence breakdown (from decision_analysis)
        da.confidence_score as overall_confidence,
        da.winner_confidence,
        da.loser_confidence,
        da.outcome_confidence,
        da.decision_type_confidence,
        da.judge_confidence

    FROM intimations i
    LEFT JOIN decision_analysis da ON i.id = da.intimation_id

    -- NEW: Join with lawyer ratings (winner)
    LEFT JOIN lawyer_ratings lr_winner
        ON da.winner_lawyer_oab = lr_winner.oab_number
        AND da.winner_lawyer_state = lr_winner.oab_state
        AND i.sigla_tribunal = lr_winner.tribunal

    -- NEW: Join with lawyer ratings (loser)
    LEFT JOIN lawyer_ratings lr_loser
        ON da.loser_lawyer_oab = lr_loser.oab_number
        AND da.loser_lawyer_state = lr_loser.oab_state
        AND i.sigla_tribunal = lr_loser.tribunal
"""

# Convert to nested struct in parquet
parquet_schema = pa.schema([
    ('intimation_id', pa.int64()),
    ('texto', pa.string()),

    # Nested lawyer struct
    ('winner_lawyer', pa.struct([
        ('oab', pa.string()),
        ('state', pa.string()),
        ('name', pa.string()),
        ('rating', pa.float32()),
        ('total_cases', pa.int32()),
        ('win_rate', pa.float32()),
        # ... more fields
    ])),

    ('loser_lawyer', pa.struct([
        # Same structure
    ])),

    # Nested confidence struct
    ('confidence_breakdown', pa.struct([
        ('overall', pa.float32()),
        ('winner_identification', pa.float32()),
        ('loser_identification', pa.float32()),
        ('outcome_classification', pa.float32()),
        ('decision_type', pa.float32()),
        ('judge_extraction', pa.float32()),
    ]))
])
```

### Step 2: Update DecisionAnalysis Model

**File:** `src/causaganha/v2/analysis/models.py`

```python
from dataclasses import dataclass

@dataclass
class ConfidenceBreakdown:
    """Detailed confidence scores for each analysis component."""
    overall: float
    winner_identification: float
    loser_identification: float
    outcome_classification: float
    decision_type_classification: float
    judge_extraction: float

@dataclass
class DecisionAnalysis:
    """Analysis result with enriched lawyer context."""

    # Existing fields
    winner_lawyer_oab: str | None
    winner_lawyer_state: str | None
    loser_lawyer_oab: str | None
    loser_lawyer_state: str | None
    outcome: Outcome
    decision_type: DecisionType | None

    # Keep for backward compatibility
    confidence_score: float

    # NEW: Detailed confidence breakdown
    confidence_breakdown: ConfidenceBreakdown | None = None

    # Analyzers should populate this internally
    # Hybrid analyzer already tracks this for RAG vs LLM decision
```

### Step 3: Update Analyzers to Populate Breakdown

**File:** `src/causaganha/v2/analysis/hybrid_analyzer.py`

```python
async def analyze_batch(self, texts, intimation_ids, pdf_urls=None):
    # ... existing code ...

    for text, intimation_id in zip(texts, intimation_ids):
        rag_result = await self.rag_analyzer.analyze_text(text)

        if rag_result.confidence_score >= self.confidence_threshold:
            # RAG was good enough
            # NEW: Add confidence breakdown
            rag_result.confidence_breakdown = ConfidenceBreakdown(
                overall=rag_result.confidence_score,
                winner_identification=rag_result.rag_confidence * 1.05,
                loser_identification=rag_result.rag_confidence * 1.02,
                outcome_classification=rag_result.rag_confidence,
                decision_type_classification=0.50,  # RAG doesn't extract this well
                judge_extraction=0.30  # RAG can't extract judge
            )
            results.append(rag_result)
        else:
            # Fallback to LLM
            llm_result = await self.llm_analyzer.analyze_pdf(pdf_url)

            # NEW: LLM has better breakdown from prompt
            llm_result.confidence_breakdown = ConfidenceBreakdown(
                overall=llm_result.confidence_score,
                # LLM confidence is more balanced
                winner_identification=0.92,
                loser_identification=0.90,
                outcome_classification=0.88,
                decision_type_classification=0.85,
                judge_extraction=0.75
            )
            results.append(llm_result)
```

---

## File Size Impact

### Current (v1)

```
Lawyer fields per row:
  winner_oab: 10 bytes (string)
  winner_state: 2 bytes (string)
  loser_oab: 10 bytes
  loser_state: 2 bytes
  confidence_score: 8 bytes (float64)

  Total: ~32 bytes per row
```

### With Enrichment (v2)

```
Lawyer struct per row (winner + loser):
  2 × (
    oab: 10 bytes
    state: 2 bytes
    name: 30 bytes (avg)
    rating: 4 bytes (float32)
    sigma: 4 bytes
    total_cases: 4 bytes (int32)
    wins: 4 bytes
    losses: 4 bytes
    win_rate: 4 bytes
    tribunal_rating: 4 bytes
    global_rating: 4 bytes
    rating_rank: 4 bytes
    percentile: 4 bytes
  ) = 2 × 82 = 164 bytes

Confidence breakdown:
  6 × 4 bytes (float32) = 24 bytes

  Total: ~188 bytes per row vs 32 bytes
  Increase: +156 bytes per row
```

### Real Impact

```
For 10,000 row file:
  v1: 10,000 × 32 bytes = 320 KB (lawyer fields only)
  v2: 10,000 × 188 bytes = 1.88 MB (lawyer fields only)

  Increase: +1.56 MB for lawyer enrichment

Full file size:
  v1: ~50 MB (base data + minimal lawyer info)
  v2: ~52 MB (base data + enriched lawyer info)

  Percentage increase: +4% (not +100% like embeddings!)
```

**Verdict:** Very reasonable size increase for massive analytical value.

---

## Benefits Summary

| Benefit | Description | Value |
|---------|-------------|-------|
| **Self-contained** | No need to join with database | High |
| **Historical snapshot** | Preserve lawyer state at decision time | High |
| **Upset detection** | Find underdog victories automatically | Medium |
| **Targeted reanalysis** | Reanalyze only uncertain high-stakes cases | High |
| **Quality diagnostics** | Identify weak analysis components | High |
| **Experience analysis** | Study how experience affects outcomes | Medium |
| **A/B testing** | Compare analyzer versions by component | Medium |

## Costs

| Cost | Impact | Mitigation |
|------|--------|------------|
| **File size** | +4% (+2MB per 10K rows) | Negligible for Internet Archive |
| **Export time** | +10% (extra joins) | Acceptable, runs once per day |
| **ETL complexity** | Medium (more joins) | Well-structured SQL, manageable |

---

## Recommendation

**Implement in Schema v2** after embeddings (P0) are deployed.

- Very high analytical value
- Minimal cost (file size, complexity)
- Enables sophisticated use cases
- Critical for long-term historical analysis

**Next Steps:**
1. Add confidence breakdown to analyzers first (easier, no schema change)
2. Test confidence breakdown in production
3. Add lawyer enrichment to export pipeline
4. Validate file sizes and query performance
5. Deploy schema v2 with both features
