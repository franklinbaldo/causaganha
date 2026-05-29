#!/usr/bin/env python3
"""Test script for DocumentMarkupService using openai/privacy-filter."""

import sys
from causaganha.analysis.document_markup import DocumentMarkupService


def main() -> int:
    print("Initializing DocumentMarkupService...")
    # Initialize service (this will download openai/privacy-filter on first run)
    service = DocumentMarkupService()

    # Read from test parquets benchmark textos.parquet
    import ibis
    from pathlib import Path
    
    textos_file = Path("data/test_parquets/textos.parquet")
    if not textos_file.exists():
        print(f"Error: {textos_file} does not exist. Run scripts/classify_documents.py first.")
        return 1
        
    t = ibis.read_parquet(textos_file)
    sample_row = t.filter(t.texto.notnull()).limit(1).execute()
    if len(sample_row) == 0:
        print("Error: No texts found in parquet.")
        return 1
        
    sample_text = sample_row.iloc[0]["texto"]

    print("\n--- ORIGINAL TEXT FROM BENCHMARK ---")
    print(sample_text[:1000] + "\n...")

    print("\nProcessing text to tag parties...")
    tagged = service.tag_parties(sample_text)

    print("\n--- TAGGED TEXT ---")
    print(tagged[:1200] + "\n...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
