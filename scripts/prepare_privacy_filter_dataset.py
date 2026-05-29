#!/usr/bin/env python3
"""Prepare dataset for training openai/privacy-filter on dispositivo extraction."""

import json
import random
from pathlib import Path

import ibis
import structlog
from causaganha.analysis.keyword_classifier import KeywordClassifier

logger = structlog.get_logger()


def main() -> int:
    logger.info("starting_dataset_preparation")

    # Paths
    textos_file = Path("data/test_parquets/textos.parquet")
    output_dir = Path("data/privacy_filter")
    output_dir.mkdir(parents=True, exist_ok=True)

    if not textos_file.exists():
        logger.error("textos_parquet_missing", path=str(textos_file))
        return 1

    # Load texts
    logger.info("loading_textos_parquet")
    t = ibis.read_parquet(textos_file)
    df = t.filter(t.texto.notnull()).execute()

    logger.info("textos_loaded", count=len(df))

    kc = KeywordClassifier()
    records = []

    # Process and find dispositif spans
    for idx, row in df.iterrows():
        text = row["texto"]
        int_id = row["id"]

        # Run regex search for dispositivo
        dispositivo_text = kc.extract_dispositivo(text)
        if dispositivo_text:
            # Locate device start and end in original text
            start_idx = text.find(dispositivo_text)
            if start_idx != -1:
                end_idx = start_idx + len(dispositivo_text)
                
                # Format to JSONL token-classification span structure
                # The spans field must be a mapping (dict) of "label": [[start, end]]
                records.append({
                    "text": text,
                    "spans": {
                        "dispositivo": [[start_idx, end_idx]]
                    }
                })

    logger.info("dispositivo_spans_extracted", total_spans=len(records))

    if not records:
        logger.error("no_spans_found_to_train")
        return 1

    # Shuffle dataset
    random.seed(42)
    random.shuffle(records)

    # Splitting datasets: 80% train, 10% validation, 10% test
    n = len(records)
    train_end = int(n * 0.8)
    val_end = train_end + int(n * 0.1)

    train_data = records[:train_end]
    val_data = records[train_end:val_end]
    test_data = records[val_end:]

    logger.info(
        "splitting_datasets",
        train=len(train_data),
        val=len(val_data),
        test=len(test_data),
    )

    # Save to JSONL
    def save_jsonl(data: list, filename: str):
        filepath = output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        logger.info("saved_dataset_file", file=str(filepath))

    save_jsonl(train_data, "train.jsonl")
    save_jsonl(val_data, "validation.jsonl")
    save_jsonl(test_data, "test.jsonl")

    # Generate label_space.json
    label_space = {
        "category_version": "causaganha_v1",
        "span_class_names": ["O", "dispositivo"]
    }
    label_space_path = output_dir / "label_space.json"
    with open(label_space_path, "w", encoding="utf-8") as f:
        json.dump(label_space, f, indent=2, ensure_ascii=False)
    
    logger.info("label_space_generated", file=str(label_space_path))
    logger.info("dataset_preparation_completed_successfully")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
