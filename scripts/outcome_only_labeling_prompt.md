# Outcome-Only Labeling Task (Simplified)

You are an expert in Brazilian law. Your task is to **extract ONLY outcomes** from 100 judicial decisions.

**⚠️ IMPORTANT: Do NOT extract party or lawyer data - it's already structured in parquet files!**

## Your Assignment

- **Documents**: 100 pre-filtered merit decisions (Agent {AGENT_ID})
- **Document IDs**: Read from `/home/user/causaganha/data/merit_decision_ids.txt` (lines {START_LINE}-{END_LINE})
- **Database**: `/home/user/causaganha/data/causaganha_real.duckdb`
- **Output**: `/home/user/causaganha/data/outcome_labels_agent_{AGENT_ID}.json`
- **Time budget**: 1-2 minutes per document (much faster than before!)

## What to Extract (ONLY 3 fields!)

For each document, extract:

### 1. **Outcome** (REQUIRED)

```json
{
  "intimation_id": "507772304",
  "outcome_normalized": "WIN | LOSS | PARTIAL | UNKNOWN",
  "confidence": "HIGH | MEDIUM | LOW",
  "outcome_phrase": "Brief key phrase from text (max 100 chars)"
}
```

**Outcome Rules:**

| Text Pattern | outcome_normalized | Perspective |
|--------------|-------------------|-------------|
| "julgo procedente" | WIN | Author/plaintiff won |
| "julgo improcedente" | LOSS | Author/plaintiff lost |
| "julgo parcialmente procedente" | PARTIAL | Split outcome |
| "dar provimento à apelação" | WIN | Appellant won |
| "negar provimento à apelação" | LOSS | Appellant lost |
| "condenar o réu" | WIN | Author won |
| "absolver o réu" | LOSS | Author lost |
| "extinguir sem mérito" | UNKNOWN | No merit decision |

**Key Insight - Appeals:**
- If **author appealed** and got "PROVIDO" → Author WIN
- If **defendant appealed** and got "DESPROVIDO" → Author WIN (original victory confirmed)
- If **defendant appealed** and got "PROVIDO" → Author LOSS

**confidence levels:**
- **HIGH**: Clear outcome phrase ("julgo procedente", "dar provimento")
- **MEDIUM**: Outcome implied but not explicit
- **LOW**: Ambiguous or unclear outcome

### 2. **Decision Type** (OPTIONAL - if obvious)

```json
{
  "decision_type": "SENTENCA | ACORDAO | DECISAO_MONOCRATICA"
}
```

Only include if clearly stated. Skip if unclear (saves time).

---

## What NOT to Extract (Already in Parquets!)

❌ **DO NOT EXTRACT:**
- Party names (autor, réu) - already in `partes.parquet`
- Lawyer names/OAB - already in `advogados.parquet`
- Procedural details - not needed for this task
- Legal reasoning - not needed for this task
- Monetary values - not needed for this task

**Why?** We already have this data structured! Focus ONLY on outcomes.

---

## Database Query

```python
import duckdb

# Load your assigned IDs
with open('/home/user/causaganha/data/merit_decision_ids.txt') as f:
    all_ids = [line.strip() for line in f.readlines()]

# Get your slice
start = {START_LINE} - 1  # 0-indexed
end = {END_LINE}
my_ids = all_ids[start:end]

# Query database
db = duckdb.connect('/home/user/causaganha/data/causaganha_real.duckdb')
for intimation_id in my_ids:
    result = db.execute(
        "SELECT id, numero_processo, texto FROM intimations WHERE id = ?",
        [intimation_id]
    ).fetchone()

    # Extract outcome from result[2] (texto)
    # ...
```

---

## Output Format

```json
{
  "agent_id": {AGENT_ID},
  "docs_range": "{START_LINE}-{END_LINE}",
  "total_docs": 100,
  "labeling_date": "2026-01-22",
  "method": "OUTCOME_ONLY",
  "documents": [
    {
      "intimation_id": "507772304",
      "numero_processo": "50095247820244047005",
      "outcome_normalized": "WIN",
      "confidence": "HIGH",
      "outcome_phrase": "julgo procedente o pedido autoral"
    },
    {
      "intimation_id": "495211090",
      "numero_processo": "50056192220254047105",
      "outcome_normalized": "LOSS",
      "confidence": "HIGH",
      "outcome_phrase": "julgo improcedente a demanda"
    }
    // ... 98 more documents
  ],
  "summary": {
    "total_labeled": 100,
    "high_confidence": 0,
    "medium_confidence": 0,
    "low_confidence": 0,
    "outcome_distribution": {
      "WIN": 0,
      "LOSS": 0,
      "PARTIAL": 0,
      "UNKNOWN": 0
    }
  }
}
```

---

## Examples

### Example 1: Simple SENTENÇA

**Text**: "...Ante o exposto, JULGO PROCEDENTE o pedido inicial para condenar o réu ao pagamento..."

**Output**:
```json
{
  "intimation_id": "123456",
  "numero_processo": "50001234...",
  "outcome_normalized": "WIN",
  "confidence": "HIGH",
  "outcome_phrase": "JULGO PROCEDENTE o pedido inicial"
}
```

### Example 2: Appeal Decision

**Text**: "...ACORDAM em DAR PROVIMENTO À APELAÇÃO interposta pelo autor..."

**Output**:
```json
{
  "intimation_id": "789012",
  "numero_processo": "50009876...",
  "outcome_normalized": "WIN",
  "confidence": "HIGH",
  "outcome_phrase": "DAR PROVIMENTO À APELAÇÃO interposta pelo autor"
}
```

### Example 3: Defendant Appeal Denied

**Text**: "...NEGAR PROVIMENTO AO RECURSO do INSS, mantendo a sentença de procedência..."

**Output**:
```json
{
  "intimation_id": "345678",
  "numero_processo": "50005555...",
  "outcome_normalized": "WIN",
  "confidence": "HIGH",
  "outcome_phrase": "NEGAR PROVIMENTO AO RECURSO do INSS"
}
```
*(Author won in first instance, INSS appealed, appeal denied = Author still wins)*

### Example 4: Partial Grant

**Text**: "...JULGO PARCIALMENTE PROCEDENTE o pedido, condenando o réu em 50% dos valores..."

**Output**:
```json
{
  "intimation_id": "567890",
  "numero_processo": "50007777...",
  "outcome_normalized": "PARTIAL",
  "confidence": "HIGH",
  "outcome_phrase": "JULGO PARCIALMENTE PROCEDENTE o pedido"
}
```

---

## Quality Guidelines

✅ **MUST DO:**
- Extract outcome for ALL 100 documents
- Use exact text phrase (don't paraphrase)
- Mark confidence LOW if unclear
- Complete in 2-3 hours total (~1-2 min/doc)

❌ **DON'T:**
- Extract party/lawyer data (already exists!)
- Spend > 3 minutes per document
- Guess if completely unclear (use UNKNOWN)
- Skip difficult documents

---

## Common Patterns Cheat Sheet

| Pattern | Outcome | Notes |
|---------|---------|-------|
| julgo procedente | WIN | Author wins |
| julgo improcedente | LOSS | Author loses |
| julgo parcialmente | PARTIAL | Split |
| dar provimento (autor) | WIN | Author's appeal granted |
| dar provimento (réu) | LOSS | Defendant's appeal granted |
| negar provimento (autor) | LOSS | Author's appeal denied |
| negar provimento (réu) | WIN | Defendant's appeal denied |
| condenar o réu | WIN | Defendant must pay |
| absolver o réu | LOSS | Defendant absolved |
| extinguir sem mérito | UNKNOWN | No decision on merits |
| não conhecer | UNKNOWN | Procedural dismissal |

---

## Start Labeling!

1. Load your 100 document IDs from merit_decision_ids.txt
2. Query database for each document's texto
3. Extract outcome using patterns above
4. Save to JSON file
5. Verify summary statistics

**Target**: 100 documents in 2-3 hours (~1-2 min each)

**Good luck! 🎯**
