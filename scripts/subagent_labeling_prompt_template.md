# Brazilian Legal Decision Labeling Task

You are an expert in Brazilian law specializing in analyzing judicial decisions. Your task is to extract structured information from 50 judicial decisions from Brazilian courts.

## Your Assignment

- **Documents**: 50 judicial decisions (doc_id {START_ID} to {END_ID})
- **Database**: `/home/user/causaganha/data/causaganha_real.duckdb`
- **Output**: JSON file with rich structured data
- **Time budget**: Approximately 3-5 minutes per document

## Task Overview

For each decision, extract:
1. ✅ **Outcome** (WIN/LOSS/PARTIAL) - P1 CRITICAL
2. ✅ **Parties** (Author, Defendant, Winner, Loser) - P1 CRITICAL
3. ✅ **Lawyers** (OAB number, which side, did they win?) - P1 CRITICAL
4. ✅ **Decision type** (Sentença, Acórdão, etc.) - P2 HIGH
5. ✅ **Procedural details** (Appeal type, outcome) - P2 HIGH
6. ⚠️ **Legal subject** (if clear) - P3 OPTIONAL
7. ⚠️ **Monetary values** (if mentioned) - P3 OPTIONAL
8. ⚠️ **Legal reasoning** (brief summary) - P3 OPTIONAL

---

## Extraction Schema

### 1. Core Identification (Auto-provided)

```json
{
  "doc_id": 51,
  "intimation_id": "494453143",
  "numero_processo": "50123456720254047100"
}
```

### 2. **Outcome Analysis** (P1 - CRITICAL)

```json
{
  "outcome": {
    "primary_outcome": "PROCEDENTE | IMPROCEDENTE | PARCIALMENTE_PROCEDENTE | NAO_CONHECIDO | EXTINTO",
    "outcome_normalized": "WIN | LOSS | PARTIAL | UNKNOWN",
    "confidence": "HIGH | MEDIUM | LOW",
    "outcome_percentage": 0-100,
    "outcome_reasoning": "Brief explanation with key phrase from text",

    "author_perspective": {
      "outcome": "WIN | LOSS | PARTIAL",
      "got_what_requested": true/false
    },

    "defendant_perspective": {
      "outcome": "WIN | LOSS | PARTIAL",
      "succeeded_in_defense": true/false
    }
  }
}
```

**Key decision rules:**
- PROCEDENTE (all requests granted) → `WIN` for author, `LOSS` for defendant
- IMPROCEDENTE (all requests denied) → `LOSS` for author, `WIN` for defendant
- PARCIALMENTE PROCEDENTE → `PARTIAL` for both
- Look for phrases like: "julgo procedente", "julgo improcedente", "dar provimento", "negar provimento"
- If author appealed and got "PROVIDO" → author WON
- If defendant appealed and got "DESPROVIDO" → defendant WON (author's original win confirmed)

### 3. **Parties** (P1 - CRITICAL)

```json
{
  "parties": {
    "simplified": {
      "author": "FULL NAME AS WRITTEN",
      "defendant": "FULL NAME AS WRITTEN",
      "winner": "NAME OF WINNING PARTY",
      "loser": "NAME OF LOSING PARTY"
    }
  }
}
```

**Extraction rules:**
- Extract names EXACTLY as written (don't abbreviate)
- Common patterns: "Apelante: MARIA SILVA" / "Apelado: INSS"
- Winner = party whose outcome was favorable
- If PARTIAL → winner = party who got more (or "BOTH" if unclear)

### 4. **Lawyers** (P1 - CRITICAL for ratings!)

```json
{
  "lawyers": {
    "lawyers": [
      {
        "name": "FULL NAME",
        "oab_numero": "12345",
        "oab_uf": "RS",
        "representing": "AUTOR | REU",
        "party_name": "WHICH PARTY THEY REPRESENTED",
        "side_won": true/false
      }
    ]
  }
}
```

**Extraction rules:**
- Look for: "Advogado: JOÃO SILVA - OAB/RS 12345"
- Extract OAB number and state separately
- If "Procuradoria Federal" or "Defensoria Pública" → oab_numero: null
- `representing`: Match lawyer to AUTOR or REU side
- `side_won`: Did their client win? (critical for lawyer ratings)
- If multiple lawyers per side, list all

### 5. **Decision Classification** (P2 - HIGH)

```json
{
  "decision_classification": {
    "decision_type": "SENTENCA | ACORDAO | DECISAO_MONOCRATICA | DESPACHO",
    "instance": "PRIMEIRA_INSTANCIA | SEGUNDA_INSTANCIA",
    "decision_nature": "MERITO_FINAL | LIMINAR | PROCESSUAL"
  }
}
```

**Decision rules:**
- SENTENCA = First instance final judgment
- ACORDAO = Appellate court collegial decision
- DECISAO_MONOCRATICA = Single judge decision (appellate)
- DESPACHO = Procedural order (no merit)

### 6. **Procedural Details** (P2 - HIGH)

```json
{
  "procedural": {
    "appeal_type": "APELACAO | AGRAVO | RECURSO_ESPECIAL",
    "who_appealed": "AUTOR | REU | AMBOS",
    "appeal_outcome": "PROVIDO | DESPROVIDO | PARCIALMENTE_PROVIDO | NAO_CONHECIDO",
    "decision_changed": true/false
  }
}
```

**Important patterns:**
- "DAR PROVIMENTO" = Appeal granted (appellant wins)
- "NEGAR PROVIMENTO" = Appeal denied (appellee wins)
- "PARCIALMENTE PROVIDO" = Partial grant
- `decision_changed`: Did appeal change the original outcome?

### 7. **Quality Metadata** (P2 - HIGH)

```json
{
  "quality": {
    "text_quality": "HIGH | MEDIUM | LOW",
    "ambiguous_outcome": false,
    "labeling_difficulty": "EASY | MEDIUM | HARD",
    "labeler_notes": "Any relevant notes or issues"
  }
}
```

### 8-10. **Optional Fields** (P3 - If time permits)

Legal subject, monetary values, and reasoning - see full schema in `rich-ground-truth-extraction-schema.md`.

---

## Complete Example

**Input text** (simplified):
```
APELAÇÃO CÍVEL Nº 5012345-67.2025.4.04.7100
Apelante: MARIA DA SILVA SANTOS
Apelado: INSTITUTO NACIONAL DO SEGURO SOCIAL - INSS
Advogado da Apelante: João Pedro Oliveira - OAB/RS 12345

ACÓRDÃO

A 8ª Turma decidiu, por unanimidade, DAR PROVIMENTO À APELAÇÃO
para reformar a sentença e julgar PROCEDENTE o pedido inicial.

A autora comprovou tempo especial de trabalho. A aposentadoria
deve ser concedida. Condeno o INSS ao pagamento de honorários
advocatícios de 10% sobre o valor da condenação.
```

**Output JSON**:
```json
{
  "doc_id": 51,
  "intimation_id": "494453143",
  "numero_processo": "50123456720254047100",

  "outcome": {
    "primary_outcome": "PROCEDENTE",
    "outcome_normalized": "WIN",
    "confidence": "HIGH",
    "outcome_percentage": 100,
    "outcome_reasoning": "Apelação provida para reformar sentença. 'DAR PROVIMENTO À APELAÇÃO para julgar PROCEDENTE'",

    "author_perspective": {
      "outcome": "WIN",
      "got_what_requested": true
    },

    "defendant_perspective": {
      "outcome": "LOSS",
      "succeeded_in_defense": false
    }
  },

  "parties": {
    "simplified": {
      "author": "MARIA DA SILVA SANTOS",
      "defendant": "INSTITUTO NACIONAL DO SEGURO SOCIAL - INSS",
      "winner": "MARIA DA SILVA SANTOS",
      "loser": "INSTITUTO NACIONAL DO SEGURO SOCIAL - INSS"
    }
  },

  "lawyers": {
    "lawyers": [
      {
        "name": "JOAO PEDRO OLIVEIRA",
        "oab_numero": "12345",
        "oab_uf": "RS",
        "representing": "AUTOR",
        "party_name": "MARIA DA SILVA SANTOS",
        "side_won": true
      },
      {
        "name": "PROCURADORIA FEDERAL",
        "oab_numero": null,
        "oab_uf": null,
        "representing": "REU",
        "party_name": "INSTITUTO NACIONAL DO SEGURO SOCIAL - INSS",
        "side_won": false,
        "is_public_defender": true
      }
    ]
  },

  "decision_classification": {
    "decision_type": "ACORDAO",
    "instance": "SEGUNDA_INSTANCIA",
    "decision_nature": "MERITO_FINAL"
  },

  "procedural": {
    "appeal_type": "APELACAO",
    "who_appealed": "AUTOR",
    "appeal_outcome": "PROVIDO",
    "decision_changed": true
  },

  "quality": {
    "text_quality": "HIGH",
    "ambiguous_outcome": false,
    "labeling_difficulty": "EASY",
    "labeler_notes": "Clear appellate decision with full information"
  }
}
```

---

## Database Query

Use this query to fetch your assigned documents:

```sql
SELECT
    id as intimation_id,
    numero_processo,
    texto,
    data_disponibilizacao,
    sigla_tribunal,
    nome_orgao
FROM intimations
WHERE texto IS NOT NULL
ORDER BY id
LIMIT 50 OFFSET {OFFSET}
```

Where `{OFFSET}` = (your_agent_id - 1) * 50

- Agent 1: OFFSET 50 (docs 51-100)
- Agent 2: OFFSET 100 (docs 101-150)
- ...
- Agent 10: OFFSET 500 (docs 501-550)

---

## Output Format

Save your results as JSON:

```json
{
  "agent_id": 1,
  "docs_range": "51-100",
  "total_docs": 50,
  "labeling_date": "2026-01-22",
  "documents": [
    { /* doc 51 */ },
    { /* doc 52 */ },
    ...
    { /* doc 100 */ }
  ],
  "summary": {
    "total_labeled": 50,
    "high_confidence": 42,
    "medium_confidence": 6,
    "low_confidence": 2,
    "ambiguous_outcomes": 3,
    "average_time_seconds": 215
  }
}
```

---

## Quality Guidelines

✅ **MUST DO:**
- Extract ALL P1 fields (outcome, parties, lawyers)
- Use exact names as written in text
- Be accurate with OAB numbers
- Mark confidence LOW if unclear
- Add notes for ambiguous cases

❌ **DON'T:**
- Guess missing information (use null)
- Abbreviate party names
- Skip difficult documents (mark as LOW confidence instead)
- Spend more than 10 minutes per document

---

## Common Patterns to Look For

### WIN patterns (for author):
- "julgo procedente o pedido"
- "dar provimento à apelação"
- "reformar a sentença para julgar procedente"
- "condenar o réu"

### LOSS patterns (for author):
- "julgo improcedente o pedido"
- "negar provimento à apelação"
- "manter a sentença"
- "não conhecer do recurso"

### PARTIAL patterns:
- "julgo parcialmente procedente"
- "dar parcial provimento"
- "acolher em parte"

### Party identification:
- "Apelante:", "Apelado:", "Agravante:", "Agravado:"
- "Autor:", "Réu:"
- "Recorrente:", "Recorrido:"

### Lawyer identification:
- "Advogado(a): [NAME] - OAB/[UF] [NUMBER]"
- "Procuradoria Federal" (INSS cases - no OAB)
- "Defensoria Pública" (no OAB)

---

## Example: Tricky Case (LOSS with appeal)

**Text**: "NEGAR PROVIMENTO À APELAÇÃO DO INSS. Manter sentença que julgou procedente."

**Analysis:**
- Author won in first instance (PROCEDENTE)
- INSS (defendant) appealed
- Appeal denied (DESPROVIDO for INSS)
- **Result**: Author WON (original victory confirmed)

**Output**:
```json
{
  "outcome": {
    "primary_outcome": "PROCEDENTE",
    "outcome_normalized": "WIN",
    "author_perspective": {"outcome": "WIN"},
    "defendant_perspective": {"outcome": "LOSS"}
  },
  "procedural": {
    "who_appealed": "REU",
    "appeal_outcome": "DESPROVIDO",
    "decision_changed": false
  }
}
```

---

## Start Labeling!

1. Query database for your 50 documents
2. For each document, extract fields following schema
3. Save progress every 10 documents
4. Generate final JSON output
5. Report completion with summary statistics

**Good luck! 🎯**
