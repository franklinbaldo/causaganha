"""Vulture whitelist — names referenced here are considered used.

Vulture parses this file statically; it does not execute it.
"""

# Enum members (accessed by value)
Outcome.PROCEDENTE  # noqa: F821
Outcome.IMPROCEDENTE  # noqa: F821
Outcome.PARCIALMENTE_PROCEDENTE  # noqa: F821
Outcome.UNKNOWN  # noqa: F821
DecisionType.SENTENCA  # noqa: F821
DecisionType.ACORDAO  # noqa: F821
DecisionType.DECISAO_INTERLOCUTORIA  # noqa: F821
DecisionType.UNKNOWN  # noqa: F821

# Pydantic validators / properties (called by pydantic internals)
AnalysisResult.plaintiff_won  # noqa: F821
AnalysisResult.normalize_enum  # noqa: F821
AnalysisResult.validate_state  # noqa: F821
LawyerInfo.clean_oab  # noqa: F821

# Pydantic model fields
PJeIntimation.numeroprocessocommascara  # noqa: F821
PJeIntimation.destinatarioadvogados  # noqa: F821
PJeIntimation.destinatarios  # noqa: F821
PJeIntimation.model_config  # noqa: F821
PJeAPIClient  # noqa: F821
PJeAPIClient.get_intimations_by_court  # noqa: F821

# Pydantic model fields on sub-models
PJeAdvogado.nome  # noqa: F821
PJeAdvogado.numero_oab  # noqa: F821
PJeAdvogado.uf_oab  # noqa: F821
PJeDestinatarioAdvogado.advogado  # noqa: F821
PJeDestinatario.nome  # noqa: F821

# __aexit__ parameters (required by protocol)
exc_type  # noqa: F821
exc_val  # noqa: F821
exc_tb  # noqa: F821

# CLI commands (registered via @app.command() decorator)
collect  # noqa: F821
analyze  # noqa: F821
export_parquet  # noqa: F821
export_status  # noqa: F821
groundtruth_status  # noqa: F821
groundtruth_init  # noqa: F821
groundtruth_sync  # noqa: F821
groundtruth_search  # noqa: F821
groundtruth_info  # noqa: F821
analyze_parquet_file  # noqa: F821
download_parquet  # noqa: F821
check_ia_exists  # noqa: F821
clear_parquet_cache  # noqa: F821
create_catalog  # noqa: F821
list_catalog_views  # noqa: F821
catalog_info  # noqa: F821
validate_catalog  # noqa: F821
download_catalog  # noqa: F821
backfill_status  # noqa: F821
query_catalog  # noqa: F821
run_cold_storage  # noqa: F821
restore_archived_data  # noqa: F821
generate_compliance_report  # noqa: F821
reset  # noqa: F821

# Config class fields (accessed as attributes at runtime via env vars)
Settings.GCP_PROJECT  # noqa: F821
Settings.GCP_REGION  # noqa: F821
Settings.TOPIC_INGEST  # noqa: F821
Settings.LOOKBACK_DAYS  # noqa: F821
Settings.PJE_API_URL  # noqa: F821
Settings.TOPIC_LLM  # noqa: F821
Settings.TASKS_QUEUE  # noqa: F821
Settings.FUNCTION_URL  # noqa: F821
Settings.EMBEDDING_PROVIDER  # noqa: F821
Settings.EMBEDDING_PROVIDER_PRIORITY  # noqa: F821
Settings.JINA_API_KEY  # noqa: F821
Settings.IA_ACCESS_KEY  # noqa: F821
Settings.IA_SECRET_KEY  # noqa: F821
Settings.PII_NAMESPACE_UUID  # noqa: F821
Settings.model_config  # noqa: F821
Settings.model_post_init  # noqa: F821

# Compliance report (used via template)
ComplianceReport.header  # noqa: F821

# Pipeline functions (used in scripts/experiments)
create_chunker_for_provider  # noqa: F821
process_decisions_batch  # noqa: F821
AnalysisStrategy.is_rag_enabled  # noqa: F821
AnalysisStrategy.is_llm_enabled  # noqa: F821
AnalysisStrategy.requires_fallback  # noqa: F821
AnalysisStrategy.NONE  # noqa: F821

# Archive service Protocol methods
ArchiveService.check_item_exists  # noqa: F821
ArchiveService.generate_metadata  # noqa: F821
InternetArchiveService.check_item_exists  # noqa: F821
InternetArchiveService.generate_metadata  # noqa: F821
LocalArchiveService.check_item_exists  # noqa: F821
LocalArchiveService.generate_metadata  # noqa: F821

# Pipeline methods
IAUploader.check_if_exists  # noqa: F821
ParquetExporter.export_day_all_tribunals  # noqa: F821
ParquetExporter._build_parquet_schema  # noqa: F821
ParquetExporter.get_yesterday  # noqa: F821
IADownloader.download_range  # noqa: F821

# Storage
FIELD_NUMERO_COMUNICACAO  # noqa: F821
FIELD_NUMERO_OAB  # noqa: F821
FIELD_UF_OAB  # noqa: F821
EmbeddingStorage.export_to_parquet  # noqa: F821
EmbeddingStorage.find_similar_texts  # noqa: F821
EmbeddingStorage.get_stats  # noqa: F821
get_embedding_storage  # noqa: F821

# RAG analyzer
RAGAnalyzer.calculate_cost  # noqa: F821

# Catalog
CatalogCreator.validations  # noqa: F821

# Constants
MAX_REASONABLE_FILE_SIZE  # noqa: F821

# djen_schema module-level Schema instances (used in scripts via import)
comunicacao  # noqa: F821
destinatario  # noqa: F821
destinatario_advogado  # noqa: F821
advogado  # noqa: F821
caderno  # noqa: F821
textos  # noqa: F821

# State
State.is_done  # noqa: F821
