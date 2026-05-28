import json
import os
import random
import shutil
import sys

import duckdb
import httpx


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.causaganha.analysis.keyword_classifier import _DISPOSITIVO_MAX_CHARS, _DISPOSITIVO_RE


def download_parquet():
    # Because archive.org is returning 503, fallback to gold_benchmark.parquet if available in test data
    target_path = "data/test_parquets/textos.parquet"
    if os.path.exists(target_path):
        print("Dataset already downloaded.")
        return target_path

    gold_path = "data/benchmark/gold_benchmark.parquet"
    if os.path.exists(gold_path):
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        shutil.copy(gold_path, target_path)
        print("Copied gold benchmark as fallback due to Internet Archive 503 error.")
        return target_path

    url = "https://archive.org/download/causaganha-embeddings/textos.parquet"

    print("Downloading benchmark dataset from Internet Archive...")
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    try:
        with httpx.stream("GET", url, follow_redirects=True) as r:
            r.raise_for_status()
            with open(target_path, "wb") as f:
                f.writelines(r.iter_bytes())

        print("Download completed.")
    except Exception as e:
        print(f"Failed to download from IA: {e}")
        # fallback to gold_benchmark if download failed
        if os.path.exists(gold_path):
            shutil.copy(gold_path, target_path)
            print("Copied gold benchmark as fallback due to Internet Archive error.")

    return target_path

def process_data(parquet_path):
    con = duckdb.connect()
    # Ensure texto column exists
    query = f"SELECT texto FROM '{parquet_path}' WHERE texto IS NOT NULL"
    rows = con.execute(query).fetchall()

    dataset = []

    for row in rows:
        text = row[0]
        m = _DISPOSITIVO_RE.search(text)
        if m:
            start_idx = m.start()
            end_idx = min(start_idx + _DISPOSITIVO_MAX_CHARS, len(text))

            sample = {
                "text": text,
                "spans": [{"start": start_idx, "end": end_idx, "label": "dispositivo"}]
            }
            dataset.append(sample)

    print(f"Found {len(dataset)} examples with 'dispositivo' out of {len(rows)} documents.")

    # Shuffle and split
    random.seed(42)
    random.shuffle(dataset)

    n = len(dataset)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)

    train_data = dataset[:n_train]
    val_data = dataset[n_train:n_train+n_val]
    test_data = dataset[n_train+n_val:]

    output_dir = "data/privacy_filter"
    os.makedirs(output_dir, exist_ok=True)

    def write_jsonl(filename, data):
        with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
            f.writelines(json.dumps(item, ensure_ascii=False) + "\n" for item in data)

    write_jsonl("train.jsonl", train_data)
    write_jsonl("validation.jsonl", val_data)
    write_jsonl("test.jsonl", test_data)

    print(f"Wrote {len(train_data)} train, {len(val_data)} validation, and {len(test_data)} test samples.")

    # Write config
    config = {
        "category_version": "causaganha_v1",
        "span_class_names": ["O", "dispositivo"]
    }

    with open(os.path.join(output_dir, "label_space.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

if __name__ == "__main__":
    parquet_path = download_parquet()
    process_data(parquet_path)
