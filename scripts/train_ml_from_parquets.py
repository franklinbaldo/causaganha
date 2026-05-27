#!/usr/bin/env python3
"""Train ML models (MLEnsemble and AnchorClassifier) using consolidated parquet data."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
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

    # Step 1: Load parquet files
    logger.info("loading_parquets")
    classif_df = pd.read_parquet(classif_file)
    textos_df = pd.read_parquet(textos_file)
    comunic_df = pd.read_parquet(comunic_file)

    logger.info(
        "parquets_loaded",
        classifications=len(classif_df),
        texts=len(textos_df),
        intimations=len(comunic_df)
    )

    # Step 2: Merge data
    # We want: numero_processo (from comunicacoes), texto (from textos),
    # outcome & confidence (from classificacoes)
    logger.info("merging_data")

    # Join classifications with texts on id
    merged_df = classif_df.merge(textos_df, left_on="texto_id", right_on="id")

    # Join with process numbers from communications
    # Deduplicate communications by texto_id to avoid duplicated records
    comunic_unique = comunic_df.drop_duplicates(subset=["texto_id"])[
        ["texto_id", "numero_processo"]
    ]
    final_df = merged_df.merge(comunic_unique, on="texto_id", how="left")

    # Drop rows without process number or text
    final_df = final_df.dropna(subset=["numero_processo", "texto"])

    # Map outcomes to canonical Portuguese ones
    final_df["mapped_outcome"] = final_df["outcome"].map(OUTCOME_MAPPING)

    # Drop rows with unmapped or unknown outcomes
    final_df = final_df.dropna(subset=["mapped_outcome"])
    final_df = final_df[final_df["mapped_outcome"] != "unknown"]

    logger.info("data_merged_and_filtered", final_count=len(final_df))
    if len(final_df) == 0:
        logger.error("no_valid_samples_for_training")
        return 1

    # Step 3: Compute Embeddings using LocalEmbedder
    logger.info("initializing_local_embedder")
    embedder = LocalEmbedder(model_name="intfloat/multilingual-e5-small", truncate_dim=None)

    logger.info("computing_embeddings_for_texts", total=len(final_df))
    texts = final_df["texto"].tolist()

    # Run embedding in batches
    embeddings = embedder.embed(texts, is_query=False, batch_size=32, normalize=True)
    logger.info("embeddings_computed", shape=embeddings.shape)

    # Step 4: Construct anchor_set.parquet
    logger.info("building_anchor_set")
    anchor_rows = []
    for idx, (_, row) in enumerate(final_df.iterrows()):
        texto = str(row["texto"])
        texto_truncado = texto[:1000]

        # Save embedding as float32 bytes for storage efficiency,
        # matching AnchorClassifier.add_anchor
        emb_bytes = embeddings[idx].astype(np.float32).tobytes()

        anchor_rows.append({
            "numero_processo": str(row["numero_processo"]),
            "texto_truncado": texto_truncado,
            "outcome": str(row["mapped_outcome"]),
            "confidence": float(row.get("confidence", 1.0)),
            "annotation_src": "auto",
            "embedding": emb_bytes
        })

    anchor_df = pd.DataFrame(anchor_rows)
    anchor_path.parent.mkdir(parents=True, exist_ok=True)
    anchor_df.to_parquet(anchor_path, index=False)
    logger.info("anchor_set_saved", path=str(anchor_path), rows=len(anchor_df))

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
        sample_processo=anchor_df.iloc[0]["numero_processo"],
        sample_true_outcome=anchor_df.iloc[0]["outcome"],
        ensemble_prediction=ens_pred,
        knn_prediction=clf_pred
    )

    logger.info("ml_training_pipeline_completed_successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
