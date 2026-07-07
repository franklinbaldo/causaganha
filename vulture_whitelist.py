"""Vulture whitelist — names referenced here are considered used.

Vulture parses this file statically; it does not execute it.
"""

# Enum members (accessed by value)
Outcome.PROCEDENTE
Outcome.IMPROCEDENTE
Outcome.PARCIALMENTE_PROCEDENTE
Outcome.UNKNOWN
DecisionType.SENTENCA
DecisionType.ACORDAO
DecisionType.DECISAO_INTERLOCUTORIA
DecisionType.UNKNOWN

# Config class fields (accessed as attributes at runtime via env vars)
Settings.GCP_PROJECT
Settings.GCP_REGION
Settings.TOPIC_INGEST
Settings.LOOKBACK_DAYS
Settings.PJE_API_URL
Settings.TOPIC_LLM
Settings.TASKS_QUEUE
Settings.FUNCTION_URL
Settings.EMBEDDING_PROVIDER
Settings.EMBEDDING_PROVIDER_PRIORITY
Settings.JINA_API_KEY
Settings.IA_ACCESS_KEY
Settings.IA_SECRET_KEY
Settings.PII_NAMESPACE_UUID
Settings.model_config
Settings.model_post_init

# Storage
FIELD_NUMERO_COMUNICACAO
FIELD_NUMERO_OAB
FIELD_UF_OAB

# djen_schema module-level Schema instances (used in scripts via import)
comunicacao
destinatario
destinatario_advogado
advogado
caderno
textos

# Kept-for-API-compat params explicitly documented as ignored
max_chars_per_doc

# Segmenter v7 exports (used by downstream scripts)
SPAN_CLASS_NAMES_V7
LABEL_SPACE_V7
SINGLE_ANCHOR_CATEGORIES
PAIRED_CATEGORIES
migrate_spans_v6_to_v7

# ref_normativa prepass exports
extract_ref_normativa
merge_with_opf_spans
REF_NORMATIVA_PATTERNS

# Reconstruction module exports
Region
validate_anchor_lengths
pair_inicio_fim
reconstruct_single_anchor_regions
reconstruct_regions
PAIRED_BASES_SET
