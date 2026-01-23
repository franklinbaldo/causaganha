#!/usr/bin/env python3
"""
Agent 1: Outcome Labeling Script
Processes lines 1-100 from merit_decision_ids.txt
"""
import json
import re
from datetime import datetime
from pathlib import Path
import duckdb

# Configuration
AGENT_ID = 1
START_LINE = 1
END_LINE = 100
DB_PATH = "/home/user/causaganha/data/causaganha_real.duckdb"
IDS_FILE = "/home/user/causaganha/data/merit_decision_ids.txt"
OUTPUT_FILE = "/home/user/causaganha/data/outcome_labels_agent_1.json"


def load_document_ids():
    """Load document IDs for this agent's range."""
    with open(IDS_FILE) as f:
        all_ids = [line.strip() for line in f.readlines()]

    # Lines 1-100 (0-indexed: 0-99)
    my_ids = all_ids[START_LINE - 1:END_LINE]
    print(f"Loaded {len(my_ids)} document IDs (lines {START_LINE}-{END_LINE})")
    return my_ids


def extract_outcome(texto: str) -> dict:
    """
    Extract outcome from decision text.

    Returns dict with:
    - outcome_normalized: WIN|LOSS|PARTIAL|UNKNOWN
    - confidence: HIGH|MEDIUM|LOW
    - outcome_phrase: Key phrase from text (max 100 chars)
    """
    if not texto:
        return {
            "outcome_normalized": "UNKNOWN",
            "confidence": "LOW",
            "outcome_phrase": "Texto vazio"
        }

    texto_lower = texto.lower()

    # High confidence patterns
    patterns_high = [
        # Sentença patterns
        (r"julgo\s+procedente(?:\s+o\s+pedido)?", "WIN"),
        (r"julgo\s+improcedente(?:\s+(?:a\s+demanda|o\s+pedido))?", "LOSS"),
        (r"julgo\s+parcialmente\s+procedente", "PARTIAL"),

        # Appeal patterns (more context needed)
        (r"dar\s+provimento\s+(?:à|ao)\s+(?:apelação|recurso)", "WIN"),  # Usually
        (r"negar\s+provimento\s+(?:à|ao)\s+(?:apelação|recurso)", "LOSS"),  # Usually
        (r"dar\s+parcial\s+provimento", "PARTIAL"),

        # Condemnation patterns
        (r"condenar\s+o\s+(?:réu|recorrido|apelado)", "WIN"),
        (r"absolver\s+o\s+(?:réu|recorrido)", "LOSS"),

        # Extinction without merit
        (r"extingo\s+(?:o\s+processo\s+)?sem\s+(?:resolução\s+de\s+)?mérito", "UNKNOWN"),
        (r"não\s+conhec(?:er|o)\s+(?:do\s+recurso|da\s+apelação)", "UNKNOWN"),
    ]

    for pattern, outcome in patterns_high:
        match = re.search(pattern, texto_lower)
        if match:
            # Extract phrase with some context (up to 100 chars)
            start = max(0, match.start() - 20)
            end = min(len(texto), match.end() + 50)
            phrase = texto[start:end].strip()

            # Clean up phrase
            phrase = re.sub(r'\s+', ' ', phrase)
            if len(phrase) > 100:
                phrase = phrase[:97] + "..."

            return {
                "outcome_normalized": outcome,
                "confidence": "HIGH",
                "outcome_phrase": phrase
            }

    # Medium confidence patterns (less specific)
    patterns_medium = [
        (r"procedente", "WIN"),
        (r"improcedente", "LOSS"),
        (r"parcialmente", "PARTIAL"),
        (r"provimento", "WIN"),  # Ambiguous without context
    ]

    for pattern, outcome in patterns_medium:
        if pattern in texto_lower:
            # Find the match for phrase extraction
            match = re.search(pattern, texto_lower)
            if match:
                start = max(0, match.start() - 20)
                end = min(len(texto), match.end() + 50)
                phrase = texto[start:end].strip()
                phrase = re.sub(r'\s+', ' ', phrase)
                if len(phrase) > 100:
                    phrase = phrase[:97] + "..."

                return {
                    "outcome_normalized": outcome,
                    "confidence": "MEDIUM",
                    "outcome_phrase": phrase
                }

    # No clear outcome found
    return {
        "outcome_normalized": "UNKNOWN",
        "confidence": "LOW",
        "outcome_phrase": "Padrão de resultado não identificado"
    }


def process_documents(doc_ids: list) -> list:
    """Process all documents and extract outcomes."""
    print(f"\nConnecting to database: {DB_PATH}")
    db = duckdb.connect(DB_PATH, read_only=True)

    documents = []
    processed = 0

    for idx, intimation_id in enumerate(doc_ids, 1):
        try:
            # Query database for text
            result = db.execute(
                "SELECT id, numero_processo, texto FROM intimations WHERE id = ?",
                [intimation_id]
            ).fetchone()

            if not result:
                print(f"  [{idx}/100] ❌ ID {intimation_id} not found in database")
                documents.append({
                    "intimation_id": intimation_id,
                    "numero_processo": None,
                    "outcome_normalized": "UNKNOWN",
                    "confidence": "LOW",
                    "outcome_phrase": "Documento não encontrado no banco"
                })
                continue

            intimation_id_db, numero_processo, texto = result

            # Extract outcome
            outcome_data = extract_outcome(texto)

            # Build document result
            doc_result = {
                "intimation_id": intimation_id,
                "numero_processo": numero_processo,
                **outcome_data
            }

            documents.append(doc_result)
            processed += 1

            # Progress indicator
            status = "✓" if outcome_data["confidence"] == "HIGH" else "○"
            print(f"  [{idx}/100] {status} {intimation_id}: {outcome_data['outcome_normalized']} ({outcome_data['confidence']})")

        except Exception as e:
            print(f"  [{idx}/100] ❌ Error processing {intimation_id}: {e}")
            documents.append({
                "intimation_id": intimation_id,
                "numero_processo": None,
                "outcome_normalized": "UNKNOWN",
                "confidence": "LOW",
                "outcome_phrase": f"Erro: {str(e)}"
            })

    db.close()
    print(f"\nProcessed {processed}/{len(doc_ids)} documents successfully")
    return documents


def calculate_summary(documents: list) -> dict:
    """Calculate summary statistics."""
    summary = {
        "total_labeled": len(documents),
        "high_confidence": sum(1 for d in documents if d["confidence"] == "HIGH"),
        "medium_confidence": sum(1 for d in documents if d["confidence"] == "MEDIUM"),
        "low_confidence": sum(1 for d in documents if d["confidence"] == "LOW"),
        "outcome_distribution": {
            "WIN": sum(1 for d in documents if d["outcome_normalized"] == "WIN"),
            "LOSS": sum(1 for d in documents if d["outcome_normalized"] == "LOSS"),
            "PARTIAL": sum(1 for d in documents if d["outcome_normalized"] == "PARTIAL"),
            "UNKNOWN": sum(1 for d in documents if d["outcome_normalized"] == "UNKNOWN"),
        }
    }
    return summary


def main():
    print("=" * 60)
    print(f"Agent {AGENT_ID}: Outcome Labeling Task")
    print(f"Range: Lines {START_LINE}-{END_LINE}")
    print("=" * 60)

    # Load document IDs
    doc_ids = load_document_ids()

    # Process documents
    documents = process_documents(doc_ids)

    # Calculate summary
    summary = calculate_summary(documents)

    # Build output JSON
    output = {
        "agent_id": AGENT_ID,
        "docs_range": f"{START_LINE}-{END_LINE}",
        "total_docs": len(doc_ids),
        "labeling_date": datetime.now().strftime("%Y-%m-%d"),
        "method": "OUTCOME_ONLY",
        "documents": documents,
        "summary": summary
    }

    # Save to file
    print(f"\nSaving results to: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total labeled: {summary['total_labeled']}")
    print(f"High confidence: {summary['high_confidence']}")
    print(f"Medium confidence: {summary['medium_confidence']}")
    print(f"Low confidence: {summary['low_confidence']}")
    print("\nOutcome Distribution:")
    for outcome, count in summary['outcome_distribution'].items():
        pct = (count / summary['total_labeled'] * 100) if summary['total_labeled'] > 0 else 0
        print(f"  {outcome}: {count} ({pct:.1f}%)")
    print("=" * 60)
    print(f"\n✓ Complete! Results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
