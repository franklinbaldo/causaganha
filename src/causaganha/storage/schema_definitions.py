"""Database schema definitions (refactored for maintainability)."""

import ibis


# Intimations table schema
INTIMATIONS_SCHEMA = ibis.schema({
    # Core identification
    "id": "int64",
    "numero_processo": "string",
    "data_disponibilizacao": "string",
    "sigla_tribunal": "string",

    # Metadata for tracking
    "created_at": "timestamp",
    "updated_at": "timestamp",

    # Communication details
    "tipo_comunicacao": "string",
    "nome_orgao": "string",
    "texto": "string",

    # Document information
    "link": "string",
    "tipo_documento": "string",
    "nome_classe": "string",
    "codigo_classe": "string",

    # Metadata
    "hash": "string",
    "status": "string",

    # Analysis tracking
    "analyzed": "boolean",
    "analysis_attempted_at": "timestamp",
    "analysis_error": "string",
    "analyzed_at": "timestamp",

    # Archive tracking (added via TDD)
    "ia_url": "string",
    "archived_at": "timestamp",

    # ML pipeline flags
    "needs_download": "boolean",
})


# Intimation lawyers table schema (extracted from API)
INTIMATION_LAWYERS_SCHEMA = ibis.schema({
    "intimation_id": "int64",
    "oab_number": "string",
    "oab_state": "string",
    "lawyer_name": "string",
    "polo": "string",
})

# Pipeline state table schema
PIPELINE_STATE_SCHEMA = ibis.schema({
    "task_id": "string",
    "step": "string",
    "timestamp": "timestamp",
})


# Analysis results table schema
ANALYSIS_RESULTS_SCHEMA = ibis.schema({
    "id": "int64",
    "intimation_id": "int64",
    "outcome": "string",
    "summary": "string",
    "judge_name": "string",
    "confidence_score": "float64",
    "analyzed_at": "timestamp",

    # Decision details
    "winner_lawyer_oab": "string",
    "winner_lawyer_state": "string",
    "winner_party_name": "string",
    "loser_lawyer_oab": "string",
    "loser_lawyer_state": "string",
    "loser_party_name": "string",
    "decision_type": "string",
    "decision_reasoning": "string",

    # Scoring tracking
    "scored": "boolean",
})


# Lawyer ratings table schema
LAWYER_RATINGS_SCHEMA = ibis.schema({
    "oab_number": "string",
    "oab_state": "string",
    "lawyer_name": "string",

    # OpenSkill rating
    "mu": "float64",
    "sigma": "float64",

    # Statistics
    "last_updated": "timestamp",
    "total_cases": "int64",
    "wins": "int64",
    "losses": "int64",
})
