#!/usr/bin/env python3
"""Train ML models (MLEnsemble and AnchorClassifier) using consolidated parquet data."""

import argparse
import sys
from pathlib import Path

import ibis
import numpy as np
import structlog

from causaganha.analysis.anchor_classifier import AnchorClassifier
from causaganha.analysis.local_embedder import LocalEmbedder
from causaganha.analysis.ml_ensemble import EmbeddingEnsemble


# Initialize logger
logger = structlog.get_logger()

# Outcomes mapping from parquet (english/caps) to canonical (portuguese/lowercase)
OUTCOME_MAPPING = {
    "WIN": "procedente",
    "LOSS": "improcedente",
    "PARTIAL": "parcialmente procedente",
    "SETTLEMENT": "acordo",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Train outcome ML model from parquets.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of decisions to train on (for testing/sampling).",
    )
    args = parser.parse_args()

    logger.info("starting_ml_training_pipeline")

    # Paths
    parquet_dir = Path("data/test_parquets")
    anchor_path = Path("data/anchor_set.parquet")
    ensemble_path = Path("data/ml_ensemble.joblib")

    classif_file = parquet_dir / "classificacoes.parquet"
    textos_file = parquet_dir / "textos.parquet"
    comunic_file = parquet_dir / "comunicacoes.parquet"

    # Check if files exist
    for f in [classif_file, textos_file, comunic_file]:
        if not f.exists():
            logger.error("parquet_file_missing", path=str(f))
            return 1

    # Step 1: Load parquet files using Ibis
    logger.info("loading_parquets")
    classif_t = ibis.read_parquet(classif_file)
    textos_t = ibis.read_parquet(textos_file)
    comunic_t = ibis.read_parquet(comunic_file)

    # Step 2: Merge data
    # We want: numero_processo (from comunicacoes), texto (from textos),
    # outcome & confidence (from classificacoes)
    logger.info("merging_data")

    # Deduplicate communications by texto_id to avoid duplicated records
    comunic_unique = comunic_t.select("texto_id", "numero_processo").distinct(on="texto_id")

    # Join classifications with texts on id
    merged_t = classif_t.join(textos_t, classif_t.texto_id == textos_t.id)

    # Join with process numbers from communications
    final_t = merged_t.join(comunic_unique, "texto_id", how="left")

    # Drop rows without process number or text
    final_t = final_t.filter(final_t.numero_processo.notnull() & final_t.texto.notnull())

    # Map outcomes to canonical Portuguese ones
    mapped_outcome = ibis.cases(
        (final_t.outcome == "WIN", "procedente"),
        (final_t.outcome == "LOSS", "improcedente"),
        (final_t.outcome == "PARTIAL", "parcialmente procedente"),
        (final_t.outcome == "SETTLEMENT", "acordo"),
        else_=ibis.null(),
    )
    final_t = final_t.mutate(mapped_outcome=mapped_outcome)

    # Drop rows with unmapped or unknown outcomes
    final_t = final_t.filter(
        final_t.mapped_outcome.notnull() & (final_t.mapped_outcome != "unknown")
    )

    if args.limit is not None:
        final_t = final_t.limit(args.limit)

    final_df = final_t.execute()

    logger.info("data_merged_and_filtered", final_count=len(final_df))
    if len(final_df) == 0:
        logger.error("no_valid_samples_for_training")
        return 1

    # Step 3: Compute Embeddings using LocalEmbedder
    # pplx-embed-v1 has 32K token context — full documents embed in one pass, no chunking.
    logger.info("initializing_local_embedder")
    embedder = LocalEmbedder()

    logger.info("extracting_texts_for_embeddings", total=len(final_df))
    texts = [str(row.texto) for row in final_df.itertuples(index=False)]

    logger.info("computing_embeddings_for_texts", total=len(texts))
    embeddings = embedder.embed(texts, is_query=False, batch_size=16, normalize=True)
    logger.info("embeddings_computed", shape=embeddings.shape)

    # Step 4: Construct anchor_set.parquet
    logger.info("building_anchor_set")
    anchor_rows = []
    for idx, row in enumerate(final_df.itertuples(index=False)):
        texto = str(row.texto)
        texto_truncado = texto[:1000]
        emb_bytes = embeddings[idx].astype(np.float32).tobytes()
        confidence = float(getattr(row, "confidence", 1.0))

        anchor_rows.append(
            {
                "numero_processo": str(row.numero_processo),
                "texto_truncado": texto_truncado,
                "outcome": str(row.mapped_outcome),
                "confidence": confidence,
                "annotation_src": "auto",
                "embedding": emb_bytes,
            }
        )

    # Save to parquet using Ibis memtable instead of PyArrow
    anchor_table = ibis.memtable(anchor_rows)
    anchor_path.parent.mkdir(parents=True, exist_ok=True)
    anchor_table.to_parquet(anchor_path)
    logger.info("anchor_set_saved", path=str(anchor_path), rows=len(anchor_rows))

    # Step 5: Train EmbeddingEnsemble
    logger.info("training_ml_ensemble")
    ensemble = EmbeddingEnsemble(ensemble_path=ensemble_path, anchor_path=anchor_path)
    ensemble.train()

    logger.info("saving_trained_ensemble")
    ensemble.save()
    logger.info("ensemble_saved", path=str(ensemble_path))

    # Step 6: Verify and Evaluate AnchorClassifier & MLEnsemble loading and prediction
    logger.info("verifying_trained_models")

    # Load Ensemble
    loaded_ensemble = EmbeddingEnsemble.load(ensemble_path)

    # Load AnchorClassifier
    classifier = AnchorClassifier(anchor_path=anchor_path, k=5)
    classifier.load()

    # Test on a sample embedding (first one from the training set)
    sample_emb = embeddings[0]

    # Predict with Ensemble
    ens_pred = loaded_ensemble.predict_proba(sample_emb)
    # Predict with AnchorClassifier
    clf_pred = classifier.classify(sample_emb)

    logger.info(
        "verification_successful",
        sample_processo=anchor_rows[0]["numero_processo"],
        sample_true_outcome=anchor_rows[0]["outcome"],
        ensemble_prediction=ens_pred,
        knn_prediction=clf_pred,
    )

    logger.info("ml_training_pipeline_completed_successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
