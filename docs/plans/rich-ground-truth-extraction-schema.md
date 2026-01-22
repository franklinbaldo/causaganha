# Rich Ground Truth Extraction Schema

**Status**: Draft
**Created**: 2026-01-22
**Purpose**: Define comprehensive data extraction schema for subagent ground truth labeling

## Overview

When dispatching 10 subagents to label 500 additional decisions (50 each), we should extract **rich structured data** beyond simple WIN/LOSS classification. This maximizes the value of manual labeling and creates a dataset useful for:

1. **Lawyer performance analysis** (core mission)
2. **Legal strategy patterns**
3. **Judicial behavior analysis**
4. **Advanced ML training data**
5. **Legal outcome prediction improvements**

## Extraction Schema

### 1. Core Identification

```json
{
  "doc_id": 51,
  "intimation_id": "494453143",
  "numero_processo": "50123456720254047100",
  "data_disponibilizacao": "2025-01-15",
  "tribunal": "TRF4",
  "orgao": "8ª TURMA"
}
```

**Fields:**
- `doc_id`: Sequential ID in ground truth dataset (51-550)
- `intimation_id`: Database primary key
- `numero_processo`: Case number (CNJ format)
- `data_disponibilizacao`: Publication date
- `tribunal`: Court identifier (TRF4, TJRO, etc.)
- `orgao`: Specific chamber/panel

---

### 2. Decision Classification

```json
{
  "decision_type": "ACORDAO",
  "decision_subtype": "APPELLATE_JUDGMENT",
  "instance": "SEGUNDA_INSTANCIA",
  "decision_nature": "MERITO_FINAL",
  "procedural_phase": "SENTENCA_CONFIRMADA"
}
```

**Fields:**
- `decision_type`: SENTENCA | ACORDAO | DECISAO_MONOCRATICA | DESPACHO
- `decision_subtype`: More specific (APPELLATE_JUDGMENT, INTERLOCUTORY, etc.)
- `instance`: PRIMEIRA_INSTANCIA | SEGUNDA_INSTANCIA | SUPERIOR
- `decision_nature`: MERITO_FINAL | LIMINAR | CAUTELAR | PROCESSUAL
- `procedural_phase`: What stage (e.g., SENTENCA_CONFIRMADA, SENTENCA_REFORMADA)

---

### 3. Outcome Analysis (Enhanced)

```json
{
  "primary_outcome": "PROCEDENTE",
  "outcome_detail": "TOTAL",
  "outcome_normalized": "WIN",
  "confidence": "HIGH",
  "outcome_percentage": 100,
  "outcome_reasoning": "Court granted all requests. 'Julgo procedente o pedido em sua totalidade'",

  "author_perspective": {
    "outcome": "WIN",
    "got_what_requested": true,
    "percentage_obtained": 100
  },

  "defendant_perspective": {
    "outcome": "LOSS",
    "succeeded_in_defense": false
  }
}
```

**Enhanced fields:**
- `primary_outcome`: PROCEDENTE | IMPROCEDENTE | PARCIALMENTE_PROCEDENTE | NAO_CONHECIDO | EXTINTO
- `outcome_detail`: TOTAL | PARCIAL_MAIOR | PARCIAL_MENOR | PARCIAL_50
- `outcome_normalized`: WIN | LOSS | PARTIAL | UNKNOWN (for ML)
- `confidence`: HIGH | MEDIUM | LOW (labeler's confidence)
- `outcome_percentage`: 0-100 (how much author won)
- `outcome_reasoning`: Brief explanation with key phrase
- `author_perspective`: Outcome from plaintiff's view
- `defendant_perspective`: Outcome from defendant's view

---

### 4. Parties Information (Rich)

```json
{
  "parties": [
    {
      "role": "AUTOR_APELANTE",
      "name": "MARIA DA SILVA SANTOS",
      "normalized_name": "MARIA DA SILVA SANTOS",
      "party_type": "PESSOA_FISICA",
      "is_winner": true,
      "cpf_cnpj": null,
      "is_government": false,
      "is_inss": false
    },
    {
      "role": "REU_APELADO",
      "name": "INSTITUTO NACIONAL DO SEGURO SOCIAL - INSS",
      "normalized_name": "INSS",
      "party_type": "AUTARQUIA_FEDERAL",
      "is_winner": false,
      "cpf_cnpj": null,
      "is_government": true,
      "is_inss": true
    }
  ],

  "simplified": {
    "author": "MARIA DA SILVA SANTOS",
    "defendant": "INSS",
    "winner": "MARIA DA SILVA SANTOS",
    "loser": "INSS"
  }
}
```

**Enhanced party tracking:**
- `role`: Precise procedural role (AUTOR_APELANTE, REU_APELADO, etc.)
- `normalized_name`: Cleaned name for matching
- `party_type`: PESSOA_FISICA | PESSOA_JURIDICA | AUTARQUIA_FEDERAL | EMPRESA_PRIVADA
- `is_winner`: Boolean outcome for this party
- `is_government`: Flag for government entities
- `is_inss`: Special flag (most common defendant in our dataset)

---

### 5. Lawyers Information (CRITICAL for ratings)

```json
{
  "lawyers": [
    {
      "name": "JOAO PEDRO OLIVEIRA",
      "oab_numero": "12345",
      "oab_uf": "RS",
      "oab_full": "OAB/RS 12345",
      "representing": "AUTOR",
      "party_name": "MARIA DA SILVA SANTOS",
      "side_won": true,
      "performance_score": "WIN"
    },
    {
      "name": "PROCURADORIA FEDERAL",
      "oab_numero": null,
      "oab_uf": null,
      "oab_full": null,
      "representing": "REU",
      "party_name": "INSS",
      "side_won": false,
      "performance_score": "LOSS",
      "is_public_defender": true
    }
  ]
}
```

**CRITICAL FIELDS for lawyer ratings:**
- `oab_numero` + `oab_uf`: Unique lawyer identifier
- `representing`: Which side (AUTOR | REU)
- `party_name`: Which specific party they represented
- `side_won`: Boolean - did their client win?
- `performance_score`: WIN | LOSS | PARTIAL (for rating calculation)
- `is_public_defender`: Flag for institutional lawyers

---

### 6. Legal Subject Matter

```json
{
  "legal_subject": {
    "primary_area": "PREVIDENCIARIO",
    "secondary_area": "APOSENTADORIA",
    "specific_issue": "TEMPO_DE_CONTRIBUICAO",
    "keywords": ["aposentadoria por tempo de contribuição", "tempo especial", "insalubridade"],
    "is_social_security": true,
    "involves_monetary_value": true
  }
}
```

**Subject classification:**
- `primary_area`: PREVIDENCIARIO | TRIBUTARIO | CIVIL | TRABALHISTA | CRIMINAL
- `secondary_area`: More specific sub-area
- `specific_issue`: Exact legal issue
- `keywords`: Important legal terms found
- `is_social_security`: Flag (most common in our dataset)
- `involves_monetary_value`: Flag for economic cases

---

### 7. Procedural Details

```json
{
  "procedural": {
    "appeal_type": "APELACAO",
    "who_appealed": "AUTOR",
    "appeal_outcome": "PROVIDO",
    "unanimous": true,
    "vote_breakdown": "3-0",
    "rapporteur": "DES. JOÃO BATISTA PINTO SILVEIRA",
    "judgment_date": "2025-01-10",
    "original_decision": "IMPROCEDENTE",
    "appellate_decision": "PROCEDENTE",
    "decision_changed": true
  }
}
```

**Procedural tracking:**
- `appeal_type`: APELACAO | AGRAVO | RECURSO_ESPECIAL | EMBARGOS
- `who_appealed`: AUTOR | REU | AMBOS
- `appeal_outcome`: PROVIDO | DESPROVIDO | PARCIALMENTE_PROVIDO | NAO_CONHECIDO
- `unanimous`: Boolean - unanimous decision?
- `vote_breakdown`: Vote count (3-0, 2-1, etc.)
- `rapporteur`: Judge/Rapporteur name
- `decision_changed`: Did appeal change outcome?

---

### 8. Monetary Information

```json
{
  "monetary": {
    "involves_money": true,
    "value_mentioned": "R$ 50.000,00",
    "value_normalized": 50000.00,
    "currency": "BRL",
    "payment_ordered": true,
    "payer": "INSS",
    "payee": "MARIA DA SILVA SANTOS",
    "includes_attorney_fees": true,
    "attorney_fee_percentage": 10,
    "attorney_fee_value": 5000.00
  }
}
```

**Economic impact:**
- `involves_money`: Boolean flag
- `value_mentioned`: Original text
- `value_normalized`: Numeric value
- `payment_ordered`: Was payment ordered?
- `includes_attorney_fees`: Boolean
- `attorney_fee_percentage`: Typical 10-20%
- `attorney_fee_value`: Calculated fee

---

### 9. Judicial Reasoning (Extracted)

```json
{
  "reasoning": {
    "key_legal_arguments": [
      "Tempo especial reconhecido com base em PPP",
      "Conversão de tempo especial em comum aplicada",
      "Direito adquirido às regras anteriores à reforma"
    ],
    "main_legal_basis": "Lei 8.213/91, Art. 57",
    "precedents_cited": ["REsp 1.310.034/PR", "Tema 1007 STF"],
    "constitutional_issues": false,
    "summary": "Court recognized special working time based on PPP document. Conversion to common time granted per pre-reform rules."
  }
}
```

**Legal analysis:**
- `key_legal_arguments`: Main points
- `main_legal_basis`: Primary law/article cited
- `precedents_cited`: Case law references
- `constitutional_issues`: Flag for constitutional questions
- `summary`: 2-3 sentence summary

---

### 10. Document Quality Metadata

```json
{
  "quality": {
    "text_length": 4500,
    "text_quality": "HIGH",
    "contains_full_decision": true,
    "contains_outcome_phrase": true,
    "outcome_phrase_location": "END",
    "ambiguous_outcome": false,
    "missing_information": [],
    "labeler_notes": "Clear decision, all information present",
    "labeling_difficulty": "EASY",
    "labeling_time_seconds": 180
  }
}
```

**Quality tracking:**
- `text_quality`: HIGH | MEDIUM | LOW (completeness)
- `contains_full_decision`: Boolean
- `outcome_phrase_location`: BEGIN | MIDDLE | END
- `ambiguous_outcome`: Flag for unclear outcomes
- `missing_information`: List of missing fields
- `labeling_difficulty`: EASY | MEDIUM | HARD
- `labeling_time_seconds`: How long it took

---

## Complete Example Document

```json
{
  "doc_id": 51,
  "intimation_id": "494453143",
  "numero_processo": "50123456720254047100",
  "data_disponibilizacao": "2025-01-15",
  "tribunal": "TRF4",
  "orgao": "8ª TURMA",

  "decision_classification": {
    "decision_type": "ACORDAO",
    "decision_subtype": "APPELLATE_JUDGMENT",
    "instance": "SEGUNDA_INSTANCIA",
    "decision_nature": "MERITO_FINAL",
    "procedural_phase": "SENTENCA_REFORMADA"
  },

  "outcome": {
    "primary_outcome": "PROCEDENTE",
    "outcome_detail": "TOTAL",
    "outcome_normalized": "WIN",
    "confidence": "HIGH",
    "outcome_percentage": 100,
    "outcome_reasoning": "Apelação provida para reformar sentença. 'Dar provimento à apelação para julgar procedente o pedido'",
    "author_perspective": {
      "outcome": "WIN",
      "got_what_requested": true,
      "percentage_obtained": 100
    },
    "defendant_perspective": {
      "outcome": "LOSS",
      "succeeded_in_defense": false
    }
  },

  "parties": {
    "parties": [
      {
        "role": "AUTOR_APELANTE",
        "name": "MARIA DA SILVA SANTOS",
        "normalized_name": "MARIA DA SILVA SANTOS",
        "party_type": "PESSOA_FISICA",
        "is_winner": true,
        "is_government": false,
        "is_inss": false
      },
      {
        "role": "REU_APELADO",
        "name": "INSTITUTO NACIONAL DO SEGURO SOCIAL - INSS",
        "normalized_name": "INSS",
        "party_type": "AUTARQUIA_FEDERAL",
        "is_winner": false,
        "is_government": true,
        "is_inss": true
      }
    ],
    "simplified": {
      "author": "MARIA DA SILVA SANTOS",
      "defendant": "INSS",
      "winner": "MARIA DA SILVA SANTOS",
      "loser": "INSS"
    }
  },

  "lawyers": {
    "lawyers": [
      {
        "name": "JOAO PEDRO OLIVEIRA",
        "oab_numero": "12345",
        "oab_uf": "RS",
        "oab_full": "OAB/RS 12345",
        "representing": "AUTOR",
        "party_name": "MARIA DA SILVA SANTOS",
        "side_won": true,
        "performance_score": "WIN"
      },
      {
        "name": "PROCURADORIA FEDERAL",
        "oab_numero": null,
        "oab_uf": null,
        "representing": "REU",
        "party_name": "INSS",
        "side_won": false,
        "performance_score": "LOSS",
        "is_public_defender": true
      }
    ]
  },

  "legal_subject": {
    "primary_area": "PREVIDENCIARIO",
    "secondary_area": "APOSENTADORIA",
    "specific_issue": "TEMPO_DE_CONTRIBUICAO",
    "keywords": ["aposentadoria", "tempo especial", "conversão"],
    "is_social_security": true,
    "involves_monetary_value": true
  },

  "procedural": {
    "appeal_type": "APELACAO",
    "who_appealed": "AUTOR",
    "appeal_outcome": "PROVIDO",
    "unanimous": true,
    "vote_breakdown": "3-0",
    "rapporteur": "DES. JOÃO BATISTA PINTO SILVEIRA",
    "judgment_date": "2025-01-10",
    "original_decision": "IMPROCEDENTE",
    "appellate_decision": "PROCEDENTE",
    "decision_changed": true
  },

  "monetary": {
    "involves_money": true,
    "value_mentioned": "R$ 50.000,00",
    "value_normalized": 50000.00,
    "currency": "BRL",
    "payment_ordered": true,
    "payer": "INSS",
    "payee": "MARIA DA SILVA SANTOS",
    "includes_attorney_fees": true,
    "attorney_fee_percentage": 10,
    "attorney_fee_value": 5000.00
  },

  "reasoning": {
    "key_legal_arguments": [
      "Tempo especial reconhecido com base em PPP",
      "Conversão aplicada conforme Lei 8.213/91",
      "Direito adquirido reconhecido"
    ],
    "main_legal_basis": "Lei 8.213/91, Art. 57",
    "precedents_cited": ["REsp 1.310.034/PR"],
    "constitutional_issues": false,
    "summary": "Court recognized special working time and granted retirement benefits. Original denial overturned on appeal."
  },

  "quality": {
    "text_length": 4500,
    "text_quality": "HIGH",
    "contains_full_decision": true,
    "contains_outcome_phrase": true,
    "outcome_phrase_location": "END",
    "ambiguous_outcome": false,
    "missing_information": [],
    "labeler_notes": "Clear appellate decision, all key information present",
    "labeling_difficulty": "EASY",
    "labeling_time_seconds": 180
  }
}
```

---

## Subagent Instructions Template

Each subagent will receive:

1. **Context**: "You are a Brazilian legal expert analyzing judicial decisions"
2. **Database access**: Query to fetch their 50 assigned documents
3. **Schema**: This complete extraction schema
4. **Example**: 2-3 fully labeled examples
5. **Output format**: JSON array of labeled documents
6. **Quality guidelines**: Minimum standards for each field

---

## Priority Levels (if time-constrained)

### P1 - CRITICAL (Must extract)
- Core identification
- Outcome analysis (primary_outcome, outcome_normalized, confidence)
- Parties (simplified.author, simplified.defendant, winner, loser)
- Lawyers (name, OAB, representing, side_won)

### P2 - HIGH (Should extract)
- Decision classification (decision_type, instance)
- Procedural details (appeal_type, who_appealed, appeal_outcome)
- Quality metadata (text_quality, ambiguous_outcome, labeling_difficulty)

### P3 - NICE TO HAVE (If time permits)
- Legal subject (primary_area, keywords)
- Monetary information (involves_money, value_normalized)
- Reasoning (key_legal_arguments, summary)

---

## Benefits of Rich Extraction

1. **Lawyer Ratings**: OAB + performance_score enables accurate lawyer rankings
2. **Legal Strategy**: Subject matter + arguments reveal winning strategies
3. **Judge Patterns**: Rapporteur + outcomes reveal judicial tendencies
4. **Economic Analysis**: Monetary values show financial impact
5. **ML Training**: Rich features improve outcome prediction models
6. **Product Features**: Multiple analysis dimensions for future features

---

## Next Steps

1. Create subagent prompt template using this schema
2. Generate example labeled documents (5-10 examples)
3. Dispatch 10 parallel subagents with 50 documents each
4. Aggregate results into `ground_truth_rich.json`
5. Validate completeness and quality
