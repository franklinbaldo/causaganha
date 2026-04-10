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

# Pydantic validators / properties (called by pydantic internals)
AnalysisResult.plaintiff_won
AnalysisResult.normalize_enum
AnalysisResult.validate_state
LawyerInfo.clean_oab

# Pydantic model fields
PJeIntimation.numeroprocessocommascara
PJeIntimation.destinatarioadvogados
PJeIntimation.destinatarios
PJeIntimation.model_config
PJeAPIClient
PJeAPIClient.get_intimations_by_court

# Pydantic model fields on sub-models
PJeAdvogado.nome
PJeAdvogado.numero_oab
PJeAdvogado.uf_oab
PJeDestinatarioAdvogado.advogado
PJeDestinatario.nome

# __aexit__ parameters (required by protocol)
exc_type
exc_val
exc_tb

# Signal handler parameter (required by signal.signal protocol)
frame

# Download segment parameter (used by caller)
index

# CLI commands (registered via @app.command() decorator)
collect
analyze
export_parquet
export_status
groundtruth_status
groundtruth_init
groundtruth_sync
groundtruth_search
groundtruth_info
analyze_parquet_file
download_parquet
check_ia_exists
clear_parquet_cache
create_catalog
list_catalog_views
catalog_info
validate_catalog
download_catalog
backfill_status
query_catalog
run_cold_storage
restore_archived_data
generate_compliance_report
reset

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

# Compliance report (used via template)
ComplianceReport.header

# Pipeline functions (used in scripts/experiments)
create_chunker_for_provider
process_decisions_batch
AnalysisStrategy.is_rag_enabled
AnalysisStrategy.is_llm_enabled
AnalysisStrategy.requires_fallback
AnalysisStrategy.NONE

# Archive service Protocol methods
ArchiveService.check_item_exists
ArchiveService.generate_metadata
LocalArchiveService.check_item_exists
LocalArchiveService.generate_metadata

# Pipeline methods
IAUploader.check_if_exists
ParquetExporter.export_day_all_tribunals
ParquetExporter._build_parquet_schema
ParquetExporter.get_yesterday
IADownloader.download_range

# Storage
FIELD_NUMERO_COMUNICACAO
FIELD_NUMERO_OAB
FIELD_UF_OAB
EmbeddingStorage.export_to_parquet
EmbeddingStorage.find_similar_texts
EmbeddingStorage.get_stats
get_embedding_storage

# RAG analyzer
RAGAnalyzer.calculate_cost

# Catalog
CatalogCreator.validations

# Constants
MAX_REASONABLE_FILE_SIZE

# djen_schema module-level Schema instances (used in scripts via import)
comunicacao
destinatario
destinatario_advogado
advogado
caderno
textos

# State
State.is_done
