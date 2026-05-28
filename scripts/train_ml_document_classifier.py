#!/usr/bin/env python3
"""Train ML models to predict document types and procedural classes from embeddings."""

import sys
from pathlib import Path

import ibis
import structlog

from causaganha.analysis.local_embedder import LocalEmbedder
from causaganha.analysis.ml_document_classifier import (
    DEFAULT_DOC_TYPE_PATH,
    DEFAULT_PROC_CLASS_PATH,
    MLDocumentEnsemble,
)


# Initialize logger
logger = structlog.get_logger()


def main() -> int:
    logger.info("starting_ml_document_classifier_training_pipeline")

    # Paths
    parquet_dir = Path("data/test_parquets")
    classif_docs_file = parquet_dir / "classificacoes_documentos.parquet"
    textos_file = parquet_dir / "textos.parquet"

    # Check if files exist
    if not classif_docs_file.exists():
        logger.error(
            "classificacoes_documentos_missing",
            hint="Run scripts/classify_documents.py first.",
        )
        return 1

    if not textos_file.exists():
        logger.error("textos_parquet_missing")
        return 1

    # Step 1: Load parquet files
    logger.info("loading_parquets")
    classif_t = ibis.read_parquet(classif_docs_file)
    textos_t = ibis.read_parquet(textos_file)

    # Step 2: Merge data
    logger.info("merging_data")
    merged_t = (
        classif_t.join(textos_t, classif_t.id == textos_t.id)
        .select(
            classif_t.id,
            classif_t.document_type,
            classif_t.procedural_class,
            textos_t.texto,
        )
        .filter(textos_t.texto.notnull())
    )

    merged_df = merged_t.execute()

    logger.info("data_merged", final_count=len(merged_df))
    if len(merged_df) == 0:
        logger.error("no_valid_samples_for_training")
        return 1

    # Step 3: Compute Embeddings using LocalEmbedder
    logger.info("initializing_local_embedder")
    embedder = LocalEmbedder(model_name="intfloat/multilingual-e5-small", truncate_dim=None)

    logger.info("computing_embeddings_for_texts", total=len(merged_df))
    texts = merged_df["texto"].tolist()

    # Run embedding in batches
    embeddings = embedder.embed(texts, is_query=False, batch_size=32, normalize=True)
    logger.info("embeddings_computed", shape=embeddings.shape)

    # Step 4: Train Document Type Ensemble
    logger.info("training_document_type_ensemble")
    doc_type_ensemble = MLDocumentEnsemble(
        target_col="document_type", ensemble_path=DEFAULT_DOC_TYPE_PATH
    )
    doc_type_ensemble.train(merged_df, embeddings)
    doc_type_ensemble.save()

    # Step 5: Train Procedural Class Ensemble
    logger.info("training_procedural_class_ensemble")
    proc_class_ensemble = MLDocumentEnsemble(
        target_col="procedural_class", ensemble_path=DEFAULT_PROC_CLASS_PATH
    )
    proc_class_ensemble.train(merged_df, embeddings)
    proc_class_ensemble.save()

    # Step 6: Verify and Evaluate Predictions
    logger.info("verifying_trained_models")

    loaded_doc_type = MLDocumentEnsemble.load(DEFAULT_DOC_TYPE_PATH)
    loaded_proc_class = MLDocumentEnsemble.load(DEFAULT_PROC_CLASS_PATH)

    # Predict on the first sample
    sample_emb = embeddings[0]
    pred_doc = loaded_doc_type.predict(sample_emb)
    pred_proc = loaded_proc_class.predict(sample_emb)

    logger.info(
        "verification_successful",
        sample_true_doc_type=merged_df.iloc[0]["document_type"],
        sample_true_proc_class=merged_df.iloc[0]["procedural_class"],
        ensemble_doc_type_prediction=pred_doc,
        ensemble_proc_class_prediction=pred_proc,
    )

    logger.info("ml_document_classifier_training_pipeline_completed_successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
