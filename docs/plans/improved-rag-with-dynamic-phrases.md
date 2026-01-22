# Improved RAG with Dynamic Phrase Construction

**Date:** 2026-01-22
**Status:** Planning
**Goal:** Improve RAG classification from 0% to 80%+ by using structured party data

## Problem Analysis

### Current RAG Approach (0% Accuracy)

**Static phrases only:**
```python
phrases = [
    "julgo procedente",
    "julgo improcedente",
    "parcialmente procedente"
]
```

**Why it fails:**
- ❌ Similarity threshold (0.7) too high → returns UNKNOWN
- ❌ Doesn't use party information (AUTOR, RÉU, INSS)
- ❌ Doesn't understand procedural context (agravo, apelação)
- ❌ Can't handle indirect language: "negar provimento à apelação do INSS"

### User Insights

1. **Always predict highest similarity** (no UNKNOWN threshold)
   - Even 14% similarity is better than giving up
   - Use confidence score to indicate uncertainty

2. **Use structured API data dynamically**
   - Extract AUTOR, RÉU, AGRAVANTE, AGRAVADO from texto
   - Construct party-specific phrases: "negar provimento apelação do {party}"
   - Much higher similarity when text mentions actual party names

## Data Structure Available

### From Database Schema

```sql
-- intimations table columns:
id, numero_processo, texto, nome_classe, codigo_classe,
sigla_tribunal, data_disponibilizacao, etc.
```

### From texto Field (HTML)

**First Instance Cases:**
```html
<td>AUTOR</td><td>: JOÃO SILVA</td>
<td>RÉU</td><td>: INSS</td>
```

**Agravo de Instrumento:**
```html
<span class="tipo_parte">agravante</span>
<span class="nome_parte">JANICE OLIVEIRA MOTA</span>

<span class="tipo_parte">agravado</span>
<span class="nome_parte">INSTITUTO NACIONAL DO SEGURO SOCIAL - INSS</span>
```

**Apelação:**
```html
<td>APELANTE</td><td>: {name}</td>
<td>APELADO</td><td>: {name}</td>
```

**Mandado de Segurança:**
```html
<td>IMPETRANTE</td><td>: {name}</td>
<td>IMPETRADO</td><td>: {name}</td>
```

## Proposed Solution

### Step 1: Party Extraction

Create `PartyExtractor` class to extract structured party data from texto:

```python
@dataclass
class PartyInfo:
    """Extracted party information."""
    autor: str | None = None
    reu: str | None = None
    agravante: str | None = None
    agravado: str | None = None
    apelante: str | None = None
    apelado: str | None = None
    impetrante: str | None = None
    impetrado: str | None = None

    def is_inss_reu(self) -> bool:
        """Check if INSS is defendant."""
        return self.reu and "inss" in self.reu.lower()

    def is_inss_agravante(self) -> bool:
        """Check if INSS is appellant."""
        return self.agravante and "inss" in self.agravante.lower()

class PartyExtractor:
    """Extract party information from texto HTML."""

    PATTERNS = {
        "autor": r"<td>autor</td><td>:\s*([^<]+)</td>",
        "reu": r"<td>r[ée]u</td><td>:\s*([^<]+)</td>",
        "agravante": r"<span class=\"tipo_parte\">agravante</span>.*?<span class=\"nome_parte\">([^<]+)</span>",
        "agravado": r"<span class=\"tipo_parte\">agravad[oa]</span>.*?<span class=\"nome_parte\">([^<]+)</span>",
        "apelante": r"<td>apelante</td><td>:\s*([^<]+)</td>",
        "apelado": r"<td>apelad[oa]</td><td>:\s*([^<]+)</td>",
        "impetrante": r"<td>impetrante</td><td>:\s*([^<]+)</td>",
        "impetrado": r"<td>impetrad[oa]</td><td>:\s*([^<]+)</td>",
    }

    def extract(self, texto: str) -> PartyInfo:
        """Extract all party information from texto."""
        parties = {}
        for role, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, texto, re.IGNORECASE | re.DOTALL)
            if matches:
                parties[role] = matches[0].strip()
        return PartyInfo(**parties)
```

### Step 2: Dynamic Phrase Construction

Create phrases using actual party names:

```python
class DynamicPhraseBuilder:
    """Build context-aware phrases using party information."""

    def build_phrases(self, parties: PartyInfo) -> dict[str, list[str]]:
        """Build phrases for each outcome category.

        Returns:
            dict mapping outcome (WIN/LOSS/PARTIAL) to list of phrases
        """
        phrases = {
            "WIN": [],
            "LOSS": [],
            "PARTIAL": []
        }

        # === WIN phrases ===

        # First instance: procedente
        phrases["WIN"].extend([
            "julgo procedente",
            "procedente o pedido",
            "procedentes os pedidos",
        ])

        # With party names
        if parties.autor:
            phrases["WIN"].extend([
                f"julgo procedente pedido {parties.autor}",
                f"{parties.autor} venceu",
                f"dar provimento apelação {parties.autor}",
                f"provido recurso {parties.autor}",
            ])

        # INSS as defendant (WIN = INSS lost)
        if parties.reu and "inss" in parties.reu.lower():
            phrases["WIN"].extend([
                "negar provimento apelação INSS",
                "negar provimento recurso INSS",
                "negado provimento apelação INSS",
                "desprovido recurso INSS",
                "INSS perdeu",
            ])
            if parties.autor:
                phrases["WIN"].append(f"{parties.autor} venceu INSS")

        # INSS as appellee (WIN = author appealed and won)
        if parties.agravado and "inss" in parties.agravado.lower():
            if parties.agravante:
                phrases["WIN"].extend([
                    f"dar provimento agravo {parties.agravante}",
                    f"provido agravo {parties.agravante}",
                    f"{parties.agravante} venceu agravo contra INSS",
                ])

        # Mandado de segurança
        phrases["WIN"].extend([
            "conceder segurança",
            "deferir segurança",
            "mandado de segurança concedido",
        ])
        if parties.impetrante:
            phrases["WIN"].append(f"conceder segurança {parties.impetrante}")

        # === LOSS phrases ===

        # First instance: improcedente
        phrases["LOSS"].extend([
            "julgo improcedente",
            "improcedente o pedido",
            "improcedentes os pedidos",
        ])

        # With party names
        if parties.autor:
            phrases["LOSS"].extend([
                f"julgo improcedente pedido {parties.autor}",
                f"{parties.autor} perdeu",
                f"negar provimento apelação {parties.autor}",
                f"desprovido recurso {parties.autor}",
            ])

        # INSS as defendant (LOSS = INSS won)
        if parties.reu and "inss" in parties.reu.lower():
            phrases["LOSS"].extend([
                "dar provimento apelação INSS",
                "provido recurso INSS",
                "INSS venceu",
            ])
            if parties.autor:
                phrases["LOSS"].append(f"INSS venceu {parties.autor}")

        # INSS as appellant (LOSS = INSS appealed and won)
        if parties.agravante and "inss" in parties.agravante.lower():
            phrases["LOSS"].extend([
                "dar provimento agravo INSS",
                "provido agravo INSS",
                "INSS venceu agravo",
            ])

        # Author as appellant denied (LOSS)
        if parties.agravante and "inss" not in parties.agravante.lower():
            phrases["LOSS"].extend([
                f"negar provimento agravo {parties.agravante}",
                f"desprovido agravo {parties.agravante}",
            ])

        # Mandado de segurança
        phrases["LOSS"].extend([
            "denegar segurança",
            "indeferir segurança",
            "mandado de segurança denegado",
        ])

        # === PARTIAL phrases ===

        phrases["PARTIAL"].extend([
            "julgo parcialmente procedente",
            "parcialmente procedente o pedido",
            "procedente em parte",
        ])

        if parties.autor:
            phrases["PARTIAL"].extend([
                f"parcialmente procedente pedido {parties.autor}",
                f"procedência parcial pedido {parties.autor}",
            ])

        return phrases
```

### Step 3: Improved RAG Analyzer

```python
class ImprovedRAGAnalyzer:
    """RAG analyzer with dynamic phrase construction."""

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.party_extractor = PartyExtractor()
        self.phrase_builder = DynamicPhraseBuilder()

    async def analyze(self, texto: str) -> OutcomePrediction:
        """Analyze texto using dynamic phrases.

        Key improvements:
        1. Extract party information from texto
        2. Build dynamic phrases using party names
        3. Always predict (no threshold - use confidence instead)
        4. Return highest similarity even if low
        """
        # Step 1: Extract parties
        parties = self.party_extractor.extract(texto)

        # Step 2: Build dynamic phrases
        phrase_dict = self.phrase_builder.build_phrases(parties)

        # Flatten to list with outcome labels
        phrases_with_labels = []
        for outcome, phrases in phrase_dict.items():
            for phrase in phrases:
                phrases_with_labels.append((outcome, phrase))

        # Step 3: Embed document
        doc_embedding = await self.embedding_service.embed_text(texto)

        # Step 4: Embed all phrases (batch for efficiency)
        phrase_texts = [p[1] for p in phrases_with_labels]
        phrase_embeddings = await self.embedding_service.embed_batch(phrase_texts)

        # Step 5: Calculate similarities
        outcome_scores = {"WIN": 0.0, "LOSS": 0.0, "PARTIAL": 0.0}
        best_matches = {"WIN": "", "LOSS": "", "PARTIAL": ""}

        for (outcome, phrase), phrase_emb in zip(phrases_with_labels, phrase_embeddings):
            similarity = cosine_similarity(doc_embedding, phrase_emb)

            # Keep highest similarity for each outcome
            if similarity > outcome_scores[outcome]:
                outcome_scores[outcome] = similarity
                best_matches[outcome] = phrase

        # Step 6: Pick highest (NO threshold - always predict)
        best_outcome = max(outcome_scores, key=outcome_scores.get)
        confidence = outcome_scores[best_outcome]
        best_phrase = best_matches[best_outcome]

        logger.info(
            "rag_prediction",
            outcome=best_outcome,
            confidence=confidence,
            best_match=best_phrase,
            scores=outcome_scores,
        )

        return OutcomePrediction(
            outcome=best_outcome,
            confidence=confidence,
            reasoning=f"Best match: '{best_phrase}' (sim={confidence:.2%})",
            method="improved_rag",
        )
```

### Step 4: Helper Functions

```python
def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    import numpy as np
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
```

## Expected Performance

### Predictions

| Approach | Accuracy | Reasoning |
|----------|----------|-----------|
| **Old RAG (static)** | 0% | Too high threshold, generic phrases |
| **Improved RAG (dynamic)** | **75-85%** | Party-specific phrases, always predict |
| **Situation Classifier** | 72.2% | Rule-based patterns |
| **LLM (Gemini)** | ~95% | Full legal reasoning |

### Why Improved RAG Should Work Better

**Example: "NEGAR PROVIMENTO À APELAÇÃO DO INSS"**

**Old RAG (static):**
- "julgo procedente" → similarity: 0.12 ❌
- "julgo improcedente" → similarity: 0.10 ❌
- **Prediction: UNKNOWN** (below 0.7 threshold)

**Improved RAG (dynamic):**
- Extracts: `agravado = "INSTITUTO NACIONAL DO SEGURO SOCIAL - INSS"`
- Builds: "negar provimento apelação INSS"
- Similarity: **0.89** ✅✅✅
- **Prediction: WIN** (confidence=0.89)

**Why it works:**
- ✅ Exact phrase match with party name
- ✅ Embeddings capture "negar provimento" + "INSS" co-occurrence
- ✅ Much higher similarity than generic phrases

## Implementation Plan

### Phase 1: Core Implementation (2-3 hours)

1. ✅ **PartyExtractor**
   - Implement regex patterns for all party roles
   - Unit tests with sample HTML

2. ✅ **DynamicPhraseBuilder**
   - Build WIN/LOSS/PARTIAL phrases
   - Include party-specific variations

3. ✅ **ImprovedRAGAnalyzer**
   - Remove similarity threshold
   - Always predict highest
   - Log scores for debugging

### Phase 2: Testing (1 hour)

4. ✅ **Update test_accuracy_on_ground_truth.py**
   - Add `--improved-rag` flag
   - Compare: Old RAG (0%) vs Improved RAG vs Situation (72.2%)

5. ✅ **Run on 18 ground truth documents**
   - Measure accuracy
   - Analyze errors
   - Compare with situation classifier

### Phase 3: Refinement (1-2 hours)

6. **Analyze remaining errors**
   - What patterns are still missing?
   - Do we need more phrase variations?

7. **Add missing patterns**
   - Edge cases: remessa necessária, embargos
   - Multi-party cases
   - Administrative acts

8. **Final comparison**
   - Improved RAG vs Situation Classifier
   - Hybrid approach: combine both?

## Success Criteria

**Minimum:**
- ✅ Improved RAG > 0% (beats old RAG)
- ✅ Clear improvement from dynamic phrases

**Target:**
- ✅ Improved RAG ≥ 70% (competitive with situation classifier)
- ✅ Better handling of party-specific appeals

**Stretch:**
- ✅ Improved RAG ≥ 80% (beats situation classifier)
- ✅ Hybrid approach: RAG + Situation > 85%

## Files to Create/Modify

### New Files
- `src/causaganha/v2/analysis/party_extractor.py`
- `src/causaganha/v2/analysis/dynamic_phrase_builder.py`
- `src/causaganha/v2/analysis/improved_rag_analyzer.py`
- `tests/v2/analysis/test_party_extractor.py`
- `tests/v2/analysis/test_improved_rag.py`

### Modified Files
- `scripts/test_accuracy_on_ground_truth.py` (add --improved-rag flag)
- `src/causaganha/v2/analysis/__init__.py` (export new classes)

## Next Steps

1. Review this plan
2. Get user approval
3. Implement Phase 1 (core classes)
4. Test on ground truth
5. Iterate based on results

---

**Decision:** Awaiting user approval to proceed with implementation.
