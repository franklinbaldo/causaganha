# Improved RAG with Dynamic Phrase Construction (v2)

**Date:** 2026-01-22
**Status:** Planning - Revised
**Goal:** Improve RAG classification from 0% to 75-85%+ using all available structured data

## Data Availability Analysis

### What We Currently Have

**Parquet Files (Internet Archive):**
```
data/ia_cache/djen-parquet-2026-01-21-TRF4/
├── comunicacoes.parquet (262,717 rows)
│   └── Columns: id, numero_processo, tribunal, data_disponibilizacao,
│                 orgao, tipo, texto_id, classe, numero_comunicacao, status
└── textos.parquet (246,255 rows)
    └── Columns: texto_id, texto, tamanho
```

**DuckDB Tables:**
- `intimations` - stores comunicacoes data + texto (joined)
- No `destinatarios` or party information stored

**API Response (not stored):**
- `destinatarios: list[Destinatario]` - party names and polos (A/P/R)
- `destinatarioadvogados: list[DestinarioAdvogado]` - lawyer associations

###  Problem: Party Data Not Stored

The PJe API returns structured party information in the `destinatarios` field:

```python
class Destinatario(BaseModel):
    nome: str        # "JOÃO SILVA" or "INSS"
    polo: str        # 'A' (autor), 'P' (passive/reu), etc.
```

**But this data is NOT currently stored** in:
- ❌ DuckDB intimations table
- ❌ Parquet exports
- ❌ Any cache

**Only available in:** The HTML texto field (requires extraction)

## Revised Solution: Robust Party Extraction

Since structured party data isn't stored, we need to extract it reliably from the texto HTML field.

### Approach 1: Enhanced Regex Extraction (Immediate)

Build comprehensive regex patterns for all party roles and case types:

```python
class PartyExtractor:
    """Extract ALL party information from texto HTML."""

    # Pattern categories by document type
    PATTERNS = {
        # First instance (Sentença, Decisão)
        "first_instance": {
            "autor": [
                r"<td>AUTOR</td><td>:\s*([^<]+)</td>",
                r"<span class=\"tipo_parte\">autor</span>.*?<span class=\"nome_parte\">([^<]+)</span>",
            ],
            "reu": [
                r"<td>R[ÉE]U</td><td>:\s*([^<]+)</td>",
                r"<span class=\"tipo_parte\">r[ée]u</span>.*?<span class=\"nome_parte\">([^<]+)</span>",
            ],
            "requerente": [
                r"<td>REQUERENTE</td><td>:\s*([^<]+)</td>",
            ],
            "requerido": [
                r"<td>REQUERIDO</td><td>:\s*([^<]+)</td>",
            ],
        },

        # Agravo de Instrumento
        "agravo": {
            "agravante": [
                r"<span class=\"tipo_parte\">agravante</span>.*?<span class=\"nome_parte\">([^<]+)</span>",
                r"<td>AGRAVANTE</td><td>:\s*([^<]+)</td>",
            ],
            "agravado": [
                r"<span class=\"tipo_parte\">agravad[oa]</span>.*?<span class=\"nome_parte\">([^<]+)</span>",
                r"<td>AGRAVAD[OA]</td><td>:\s*([^<]+)</td>",
            ],
        },

        # Apelação
        "apelacao": {
            "apelante": [
                r"<span class=\"tipo_parte\">apelante</span>.*?<span class=\"nome_parte\">([^<]+)</span>",
                r"<td>APELANTE</td><td>:\s*([^<]+)</td>",
            ],
            "apelado": [
                r"<span class=\"tipo_parte\">apelad[oa]</span>.*?<span class=\"nome_parte\">([^<]+)</span>",
                r"<td>APELAD[OA]</td><td>:\s*([^<]+)</td>",
            ],
        },

        # Mandado de Segurança
        "mandado": {
            "impetrante": [
                r"<td>IMPETRANTE</td><td>:\s*([^<]+)</td>",
                r"<span class=\"tipo_parte\">impetrante</span>.*?<span class=\"nome_parte\">([^<]+)</span>",
            ],
            "impetrado": [
                r"<td>IMPETRAD[OA]</td><td>:\s*([^<]+)</td>",
                r"<span class=\"tipo_parte\">impetrad[oa]</span>.*?<span class=\"nome_parte\">([^<]+)</span>",
            ],
        },

        # Embargos / Recurso
        "recursos": {
            "embargante": [
                r"<td>EMBARGANTE</td><td>:\s*([^<]+)</td>",
            ],
            "embargado": [
                r"<td>EMBARGAD[OA]</td><td>:\s*([^<]+)</td>",
            ],
            "recorrente": [
                r"<td>RECORRENTE</td><td>:\s*([^<]+)</td>",
            ],
            "recorrido": [
                r"<td>RECORRID[OA]</td><td>:\s*([^<]+)</td>",
            ],
        },
    }

    def extract(self, texto: str) -> PartyInfo:
        """Extract all party roles with fallback patterns."""
        parties = {}

        # Try all pattern categories
        for category, roles in self.PATTERNS.items():
            for role, patterns in roles.items():
                for pattern in patterns:
                    matches = re.findall(
                        pattern,
                        texto,
                        re.IGNORECASE | re.DOTALL
                    )
                    if matches:
                        # Clean and normalize
                        party_name = matches[0].strip()
                        party_name = self._clean_party_name(party_name)
                        parties[role] = party_name
                        break  # First match wins

        return PartyInfo(**parties)

    def _clean_party_name(self, name: str) -> str:
        """Clean party name from HTML artifacts."""
        # Remove HTML entities
        name = name.replace("&nbsp;", " ")
        name = name.replace("&aacute;", "á")
        # etc...

        # Normalize whitespace
        name = " ".join(name.split())

        return name.upper()  # Normalize to uppercase
```

### Approach 2: BeautifulSoup HTML Parsing (Better)

Use proper HTML parsing instead of regex:

```python
from bs4 import BeautifulSoup

class HTMLPartyExtractor:
    """Extract parties using HTML parsing (more robust)."""

    def extract(self, texto: str) -> PartyInfo:
        """Parse HTML to extract party table."""
        soup = BeautifulSoup(texto, 'html.parser')
        parties = {}

        # Find all <table> elements
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    role = cells[0].get_text().strip().lower()
                    name = cells[1].get_text().strip()

                    # Clean role (remove ":")
                    role = role.replace(":", "").strip()

                    # Map to standardized role
                    if role in ['autor', 'requerente', 'impetrante']:
                        parties['autor'] = name
                    elif role in ['réu', 'reu', 'requerido', 'impetrado']:
                        parties['reu'] = name
                    elif role == 'agravante':
                        parties['agravante'] = name
                    elif role in ['agravado', 'agravada']:
                        parties['agravado'] = name
                    # etc...

        # Also check for <span> elements (appeal cases)
        spans = soup.find_all('span', class_='tipo_parte')
        for span in spans:
            role = span.get_text().strip().lower()
            # Find adjacent nome_parte span
            nome_span = span.find_next_sibling('span', class_='nome_parte')
            if nome_span:
                name = nome_span.get_text().strip()
                parties[role] = name

        return PartyInfo(**parties)
```

### Why BeautifulSoup > Regex

| Aspect | Regex | BeautifulSoup |
|--------|-------|---------------|
| **Robustness** | ❌ Breaks with HTML changes | ✅ Handles variations |
| **Nested tags** | ❌ Hard to match | ✅ Natural traversal |
| **Debugging** | ❌ Cryptic patterns | ✅ Clear structure |
| **Maintenance** | ❌ Pattern explosion | ✅ Simple logic |

## Revised Implementation Plan

### Phase 1: Party Extraction (1-2 hours)

**Option A: Enhanced Regex** (faster, good enough)
1. ✅ Implement PartyExtractor with comprehensive patterns
2. ✅ Test on 18 ground truth documents
3. ✅ Measure extraction accuracy (should be >95%)

**Option B: BeautifulSoup** (better, recommended)
1. ✅ Install beautifulsoup4: `uv add beautifulsoup4 lxml`
2. ✅ Implement HTMLPartyExtractor
3. ✅ Test on 18 ground truth documents
4. ✅ Compare with regex approach

### Phase 2: Dynamic Phrase Builder (1 hour)

Same as before - use extracted party data to build phrases:

```python
class DynamicPhraseBuilder:
    def build_phrases(self, parties: PartyInfo) -> dict[str, list[str]]:
        phrases = {"WIN": [], "LOSS": [], "PARTIAL": []}

        # Generic patterns
        phrases["WIN"].extend([
            "julgo procedente",
            "procedente o pedido",
        ])

        # Party-specific patterns
        if parties.autor:
            phrases["WIN"].append(f"julgo procedente pedido {parties.autor}")
            phrases["WIN"].append(f"{parties.autor} venceu")

        if parties.reu and "inss" in parties.reu.lower():
            phrases["WIN"].extend([
                "negar provimento apelação INSS",
                "desprovido recurso INSS",
                f"negar provimento apelação {parties.reu}",  # Exact name
            ])

        # Agravo-specific
        if parties.agravado and "inss" in parties.agravado.lower():
            phrases["WIN"].extend([
                f"dar provimento agravo {parties.agravante}",
                f"provido agravo {parties.agravante}",
            ])

        # ... similar for LOSS and PARTIAL

        return phrases
```

### Phase 3: Improved RAG Analyzer (30 min)

```python
class ImprovedRAGAnalyzer:
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.party_extractor = HTMLPartyExtractor()  # or PartyExtractor
        self.phrase_builder = DynamicPhraseBuilder()

    async def analyze(self, texto: str) -> OutcomePrediction:
        # 1. Extract parties
        parties = self.party_extractor.extract(texto)

        # 2. Build dynamic phrases
        phrase_dict = self.phrase_builder.build_phrases(parties)

        # 3. Embed and compare (NO threshold)
        outcome_scores = await self._calculate_similarities(texto, phrase_dict)

        # 4. Return highest (always predict)
        best_outcome = max(outcome_scores, key=outcome_scores.get)
        return OutcomePrediction(
            outcome=best_outcome,
            confidence=outcome_scores[best_outcome],
            reasoning=f"Best match (confidence={outcome_scores[best_outcome]:.2%})"
        )
```

### Phase 4: Testing & Evaluation (1 hour)

```bash
# Test party extraction accuracy
uv run python scripts/test_party_extraction.py --sample 18

# Test RAG classification
uv run python scripts/test_accuracy_on_ground_truth.py --provider local --improved-rag

# Compare approaches
uv run python scripts/test_accuracy_on_ground_truth.py --compare-all
```

**Expected Results:**

| Method | Accuracy | Notes |
|--------|----------|-------|
| Old RAG (static) | 0% | High threshold, generic phrases |
| **Improved RAG (dynamic)** | **75-85%** | Party extraction + dynamic phrases |
| Situation Classifier | 72.2% | Current baseline |
| Hybrid (RAG + Situation) | **80-90%** | Best of both |

## Future Enhancement: Store Party Data

**Recommendation:** Modify pipeline to store `destinatarios` in database:

```python
# In storage/migrations.py
CREATE TABLE IF NOT EXISTS parties (
    id INTEGER PRIMARY KEY,
    intimation_id BIGINT REFERENCES intimations(id),
    nome VARCHAR NOT NULL,
    polo VARCHAR(1),  -- 'A' (autor), 'P' (passive), 'R' (reu)
    tipo_parte VARCHAR,  -- 'autor', 'reu', 'agravante', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# In pipeline/collect.py
async def store_intimation_with_parties(intimation: Intimation, conn):
    # Store intimation
    await store_intimation(intimation, conn)

    # Store parties
    for dest in intimation.destinatarios:
        conn.execute("""
            INSERT INTO parties (intimation_id, nome, polo)
            VALUES (?, ?, ?)
        """, [intimation.id, dest.nome, dest.polo])
```

**Benefits:**
- ✅ No regex/HTML parsing needed
- ✅ Structured queries: `SELECT * FROM parties WHERE intimation_id = ?`
- ✅ Better data quality
- ✅ Easier analytics

**But for now:** HTML extraction is sufficient and works with existing data.

## Decision Points

**Immediate (next 4 hours):**
1. **Party Extraction:** BeautifulSoup (recommended) or Enhanced Regex?
2. **Testing:** Run on 18 ground truth docs to validate extraction
3. **Implementation:** Build improved RAG analyzer
4. **Comparison:** Measure against situation classifier

**Future (separate PR):**
1. Store `destinatarios` in database schema
2. Update parquet exports to include party data
3. Migrate existing data by re-extracting from texto

## Success Criteria

**Minimum:**
- ✅ Party extraction >90% accuracy on ground truth
- ✅ Improved RAG >60% (beats old 0%)

**Target:**
- ✅ Improved RAG ≥72% (matches situation classifier)
- ✅ Works on real-world cases

**Stretch:**
- ✅ Improved RAG ≥80% (beats situation classifier)
- ✅ Hybrid approach ≥85%

---

**Next Step:** User approval to proceed with BeautifulSoup approach?
