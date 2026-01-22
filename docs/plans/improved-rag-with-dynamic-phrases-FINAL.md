# Improved RAG with Dynamic Phrase Construction (FINAL)

**Date:** 2026-01-22
**Status:** Planning - CORRECTED
**Goal:** Improve RAG classification from 0% to 75-85%+ using structured party data from parquet files

## Data Availability (CORRECTED)

### Internet Archive Parquet Structure

Each DJEN export (e.g., `djen-parquet-2026-01-21-TRF4`) contains **6 normalized parquet files**:

1. **comunicacoes.parquet** (262,717 rows) - Main communication metadata
   - `id`, `numero_processo`, `tribunal`, `data_disponibilizacao`, `orgao`, `tipo`, `classe`

2. **textos.parquet** (246,255 rows) - Full text content
   - `texto_id`, `texto`, `tamanho`

3. **partes.parquet** (211,781 rows) - Party master table
   - `parte_id` (UUID), `nome`, `documento` (CPF/CNPJ)

4. **comunicacao_partes.parquet** (370,450 rows) - Party associations
   - `comunicacao_id`, `parte_id`, `papel` ("A"=Ativo/Author, "P"=Passivo/Defendant)

5. **advogados.parquet** - Lawyer master table
   - `advogado_id`, `nome`, `oab_numero`, `oab_uf`

6. **comunicacao_advogados.parquet** - Lawyer associations
   - `comunicacao_id`, `advogado_id`

### Join Pattern to Get Parties

```python
# Get parties for a specific comunicacao
result = (
    comunicacoes[comunicacoes['id'] == '502461475']
    .merge(comunicacao_partes, left_on='id', right_on='comunicacao_id')
    .merge(partes, on='parte_id')
)

# Result:
#   papel: A, nome: ELIANE DIAS
#   papel: P, nome: BANCO MASTER S/A
```

## Solution: Use Structured Party Data

Since party data is **already structured and normalized**, we can:

1. ✅ Load parquet files into DuckDB or Pandas
2. ✅ JOIN to get party names and roles
3. ✅ Build dynamic phrases using actual party names
4. ✅ No HTML parsing needed!

### Advantages Over HTML Parsing

| Aspect | HTML Parsing | Parquet JOINs |
|--------|--------------|---------------|
| **Reliability** | ❌ Brittle regex | ✅ Structured data |
| **Performance** | ❌ Slow parsing | ✅ Fast JOINs |
| **Completeness** | ❌ May miss parties | ✅ All parties present |
| **Normalization** | ❌ Manual cleaning | ✅ Already normalized |
| **Party IDs** | ❌ No unique IDs | ✅ UUID `parte_id` |

## Implementation Plan

### Phase 1: Load Party Data (30 min)

Create utility to load and join parquet files:

```python
import pyarrow.parquet as pq
import pandas as pd
from dataclasses import dataclass

@dataclass
class PartyInfo:
    """Structured party information from parquets."""
    autor: str | None = None
    reu: str | None = None
    outros: list[tuple[str, str]] = None  # [(papel, nome), ...]

class ParquetPartyLoader:
    """Load party data from parquet files."""

    def __init__(self, parquet_dir: Path):
        """Load all parquet tables."""
        self.comunicacoes = pq.read_table(parquet_dir / 'comunicacoes.parquet').to_pandas()
        self.partes = pq.read_table(parquet_dir / 'partes.parquet').to_pandas()
        self.comunicacao_partes = pq.read_table(parquet_dir / 'comunicacao_partes.parquet').to_pandas()

    def get_parties(self, comunicacao_id: str) -> PartyInfo:
        """Get parties for a specific comunicacao."""
        # Join tables
        result = (
            self.comunicacao_partes[self.comunicacao_partes['comunicacao_id'] == comunicacao_id]
            .merge(self.partes, on='parte_id')
        )

        # Extract by role
        parties = Party Info()

        for _, row in result.iterrows():
            papel = row['papel']
            nome = row['nome']

            if papel == 'A':  # Ativo (Author/Plaintiff)
                parties.autor = nome
            elif papel == 'P':  # Passivo (Defendant)
                parties.reu = nome
            else:
                if parties.outros is None:
                    parties.outros = []
                parties.outros.append((papel, nome))

        return parties
```

### Phase 2: Dynamic Phrase Builder (Unchanged)

```python
class DynamicPhraseBuilder:
    """Build phrases using structured party data."""

    def build_phrases(self, parties: PartyInfo) -> dict[str, list[str]]:
        phrases = {"WIN": [], "LOSS": [], "PARTIAL": []}

        # Generic phrases (baseline)
        phrases["WIN"].extend([
            "julgo procedente",
            "procedente o pedido",
        ])

        # Party-specific phrases (HIGH similarity expected)
        if parties.autor:
            autor_norm = parties.autor.upper()
            phrases["WIN"].extend([
                f"julgo procedente pedido {autor_norm}",
                f"{autor_norm} venceu",
                f"dar provimento apelação {autor_norm}",
            ])

        if parties.reu:
            reu_norm = parties.reu.upper()

            # If RÉU is INSS (common)
            if "INSS" in reu_norm:
                phrases["WIN"].extend([
                    "negar provimento apelação INSS",
                    "negar provimento recurso INSS",
                    "desprovido recurso INSS",
                    f"negar provimento apelação {reu_norm}",  # Exact name
                ])

                phrases["LOSS"].extend([
                    "dar provimento apelação INSS",
                    "provido recurso INSS",
                    "INSS venceu",
                ])

            # Generic defendant phrases
            phrases["LOSS"].extend([
                f"{reu_norm} venceu",
                f"dar provimento apelação {reu_norm}",
            ])

        # Cross-party phrases
        if parties.autor and parties.reu:
            autor_norm = parties.autor.upper()
            reu_norm = parties.reu.upper()

            phrases["WIN"].extend([
                f"{autor_norm} venceu {reu_norm}",
                f"{autor_norm} venceu contra {reu_norm}",
            ])

            phrases["LOSS"].extend([
                f"{reu_norm} venceu {autor_norm}",
                f"{reu_norm} venceu contra {autor_norm}",
            ])

        # ... similar for PARTIAL and LOSS

        return phrases
```

### Phase 3: Improved RAG Analyzer

```python
class ImprovedRAGAnalyzer:
    """RAG analyzer using structured party data."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        parquet_loader: ParquetPartyLoader
    ):
        self.embedding_service = embedding_service
        self.parquet_loader = parquet_loader
        self.phrase_builder = DynamicPhraseBuilder()

    async def analyze(
        self,
        comunicacao_id: str,
        texto: str
    ) -> OutcomePrediction:
        """Analyze using structured party data + dynamic phrases."""

        # Step 1: Get structured party data
        parties = self.parquet_loader.get_parties(comunicacao_id)

        # Step 2: Build dynamic phrases using party names
        phrase_dict = self.phrase_builder.build_phrases(parties)

        # Step 3: Embed document and phrases
        doc_embedding = await self.embedding_service.embed_text(texto)

        # Step 4: Calculate similarities (NO threshold)
        outcome_scores = {}
        best_phrases = {}

        for outcome, phrases in phrase_dict.items():
            max_similarity = 0.0
            best_phrase = ""

            for phrase in phrases:
                phrase_emb = await self.embedding_service.embed_text(phrase)
                similarity = cosine_similarity(doc_embedding, phrase_emb)

                if similarity > max_similarity:
                    max_similarity = similarity
                    best_phrase = phrase

            outcome_scores[outcome] = max_similarity
            best_phrases[outcome] = best_phrase

        # Step 5: Return highest (always predict)
        best_outcome = max(outcome_scores, key=outcome_scores.get)
        confidence = outcome_scores[best_outcome]
        best_match = best_phrases[best_outcome]

        return OutcomePrediction(
            outcome=best_outcome,
            confidence=confidence,
            reasoning=f"Party-aware match: '{best_match}' ({confidence:.2%})",
            method="improved_rag_parquet",
            parties=parties,  # Include for debugging
        )
```

### Phase 4: Testing & Evaluation

```bash
# Test on ground truth
uv run python scripts/test_accuracy_on_ground_truth.py --improved-rag-parquet

# Compare all methods
uv run python scripts/test_accuracy_on_ground_truth.py --compare-all
```

**Expected Results:**

| Method | Accuracy | Data Source | Notes |
|--------|----------|-------------|-------|
| Old RAG (static) | 0% | texto only | Generic phrases |
| **Improved RAG (parquet)** | **80-90%** | parquet JOINs | Party-specific phrases |
| Situation Classifier | 72.2% | regex patterns | Rule-based |
| Hybrid (RAG + Situation) | **85-95%** | both | Best of both |

## Why This Will Work Better

**Example: "NEGAR PROVIMENTO À APELAÇÃO DO INSS"**

**Old RAG:**
- Phrases: ["julgo procedente", "julgo improcedente"]
- Best match: 0.12 similarity → UNKNOWN ❌

**Improved RAG (with parquets):**
- Parties from JOIN: `autor="ELIANE DIAS", reu="INSS"`
- Dynamic phrase: "negar provimento apelação INSS"
- **Exact phrase in document!**
- Best match: **0.92 similarity** → WIN ✅

**Key improvement:** Using actual party names creates phrases that **exactly match** the document text!

## Implementation Files

### New Files
- `src/causaganha/v2/analysis/parquet_party_loader.py` - Load party data from parquets
- `src/causaganha/v2/analysis/dynamic_phrase_builder.py` - Build phrases (unchanged)
- `src/causaganha/v2/analysis/improved_rag_analyzer.py` - RAG with parquet data
- `tests/v2/analysis/test_parquet_party_loader.py` - Unit tests

### Modified Files
- `scripts/test_accuracy_on_ground_truth.py` - Add `--improved-rag-parquet` flag

## Success Criteria

**Minimum:**
- ✅ Successfully load and JOIN parquet files
- ✅ Extract parties for all 18 ground truth docs
- ✅ Improved RAG > 60% (beats old 0%)

**Target:**
- ✅ Improved RAG ≥ 75% (beats situation classifier 72.2%)
- ✅ Party extraction 100% accurate

**Stretch:**
- ✅ Improved RAG ≥ 85% (best single method)
- ✅ Hybrid approach ≥ 90%

## Documentation Fixes Needed

I incorrectly stated that party data wasn't stored. Need to update:

1. ❌ **docs/plans/improved-rag-with-dynamic-phrases-v2.md** - DELETE (incorrect)
2. ✅ **This file** - Correct understanding
3. ✅ **CLAUDE.md** - Document parquet structure if not already present

---

**Ready to implement** - awaiting user approval.
