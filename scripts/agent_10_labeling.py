#!/usr/bin/env python3
"""
Agent 10: Outcome-Only Labeling Task
Process documents 901-1000 from merit_decision_ids.txt
"""

import duckdb
import json
import re
from datetime import datetime
from pathlib import Path

# Configuration
AGENT_ID = 10
START_LINE = 901
END_LINE = 1000
DB_PATH = "/home/user/causaganha/data/causaganha_real.duckdb"
IDS_FILE = "/home/user/causaganha/data/merit_decision_ids.txt"
OUTPUT_FILE = "/home/user/causaganha/data/outcome_labels_agent_10.json"

# Outcome patterns (case-insensitive)
OUTCOME_PATTERNS = {
    'WIN': [
        r'julgo\s+procedente(?!\s+em\s+parte)',
        r'dar\s+provimento\s+(?:à|ao)\s+(?:apela[çc][ãa]o|recurso)(?!.*(?:do\s+r[ée]u|da\s+parte\s+r[ée]))',
        r'condenar\s+(?:o|a)\s+r[ée]u',
        r'negar\s+provimento\s+(?:à|ao)\s+(?:apela[çc][ãa]o|recurso)\s+(?:do|da)\s+(?:r[ée]u|INSS|parte\s+r[ée])',
        r'dar\s+provimento\s+(?:à|ao)\s+(?:apela[çc][ãa]o|recurso)\s+(?:do|da)\s+autor',
        r'manter\s+(?:a|o)\s+senten[çc]a\s+de\s+proced[eê]ncia',
    ],
    'LOSS': [
        r'julgo\s+improcedente',
        r'dar\s+provimento\s+(?:à|ao)\s+(?:apela[çc][ãa]o|recurso)\s+(?:do|da)\s+(?:r[ée]u|INSS|parte\s+r[ée])',
        r'absolver\s+(?:o|a)\s+r[ée]u',
        r'negar\s+provimento\s+(?:à|ao)\s+(?:apela[çc][ãa]o|recurso)\s+(?:do|da)\s+autor',
        r'reformar\s+(?:a|o)\s+senten[çc]a\s+de\s+proced[eê]ncia',
    ],
    'PARTIAL': [
        r'julgo\s+parcialmente\s+procedente',
        r'procedente\s+em\s+parte',
        r'dar\s+provimento\s+parcial',
        r'provimento\s+em\s+parte',
    ],
    'UNKNOWN': [
        r'extinguir\s+sem\s+(?:resolu[çc][ãa]o\s+de\s+)?m[ée]rito',
        r'n[ãa]o\s+conhecer',
        r'indefiro\s+a\s+inicial',
        r'extinto\s+o\s+processo',
    ],
}


def extract_outcome(texto: str, intimation_id: str) -> dict:
    """Extract outcome from decision text."""
    if not texto:
        return {
            "intimation_id": intimation_id,
            "outcome_normalized": "UNKNOWN",
            "confidence": "LOW",
            "outcome_phrase": "No text available"
        }

    texto_lower = texto.lower()

    # Try each outcome category
    for outcome, patterns in OUTCOME_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, texto_lower, re.IGNORECASE)
            if match:
                # Extract a broader context around the match
                start = max(0, match.start() - 20)
                end = min(len(texto), match.end() + 80)
                phrase = texto[start:end].strip()

                # Clean up the phrase
                phrase = re.sub(r'\s+', ' ', phrase)
                if len(phrase) > 100:
                    phrase = phrase[:97] + "..."

                confidence = "HIGH"
                return {
                    "intimation_id": intimation_id,
                    "outcome_normalized": outcome,
                    "confidence": confidence,
                    "outcome_phrase": phrase
                }

    # No clear pattern found
    # Try to find any dispositivo section
    dispositivo_match = re.search(
        r'(?:ante o exposto|diante do exposto|isto posto|dispositivo).*?(?:julgo|decido|determino)',
        texto_lower[:5000],  # Check first 5000 chars
        re.IGNORECASE | re.DOTALL
    )

    if dispositivo_match:
        start = max(0, dispositivo_match.start())
        end = min(len(texto), dispositivo_match.end() + 100)
        phrase = texto[start:end].strip()
        phrase = re.sub(r'\s+', ' ', phrase)
        if len(phrase) > 100:
            phrase = phrase[:97] + "..."

        return {
            "intimation_id": intimation_id,
            "outcome_normalized": "UNKNOWN",
            "confidence": "LOW",
            "outcome_phrase": phrase
        }

    return {
        "intimation_id": intimation_id,
        "outcome_normalized": "UNKNOWN",
        "confidence": "LOW",
        "outcome_phrase": "No clear outcome pattern found"
    }


def main():
    """Main execution function."""
    print(f"Agent {AGENT_ID}: Starting outcome labeling task")
    print(f"Documents: {START_LINE}-{END_LINE} (100 docs)")

    # Load document IDs
    print(f"\nLoading IDs from {IDS_FILE}...")
    with open(IDS_FILE) as f:
        all_ids = [line.strip() for line in f.readlines()]

    # Get my slice (0-indexed)
    start_idx = START_LINE - 1
    end_idx = END_LINE
    my_ids = all_ids[start_idx:end_idx]

    print(f"Loaded {len(my_ids)} document IDs")
    print(f"First ID: {my_ids[0]}")
    print(f"Last ID: {my_ids[-1]}")

    # Connect to database
    print(f"\nConnecting to database: {DB_PATH}")
    db = duckdb.connect(DB_PATH, read_only=True)

    # Process each document
    documents = []
    stats = {
        'total': 0,
        'high_confidence': 0,
        'medium_confidence': 0,
        'low_confidence': 0,
        'outcomes': {'WIN': 0, 'LOSS': 0, 'PARTIAL': 0, 'UNKNOWN': 0}
    }

    print(f"\nProcessing {len(my_ids)} documents...")
    for idx, intimation_id in enumerate(my_ids, 1):
        if idx % 10 == 0:
            print(f"  Progress: {idx}/{len(my_ids)}")

        # Query database
        result = db.execute(
            "SELECT id, numero_processo, texto FROM intimations WHERE id = ?",
            [intimation_id]
        ).fetchone()

        if not result:
            print(f"  WARNING: Document {intimation_id} not found in database!")
            documents.append({
                "intimation_id": intimation_id,
                "numero_processo": "NOT_FOUND",
                "outcome_normalized": "UNKNOWN",
                "confidence": "LOW",
                "outcome_phrase": "Document not found in database"
            })
            stats['low_confidence'] += 1
            stats['outcomes']['UNKNOWN'] += 1
            continue

        id_val, numero_processo, texto = result

        # Extract outcome
        outcome_data = extract_outcome(texto, intimation_id)
        outcome_data['numero_processo'] = numero_processo

        documents.append(outcome_data)

        # Update stats
        stats['total'] += 1
        stats['outcomes'][outcome_data['outcome_normalized']] += 1

        if outcome_data['confidence'] == 'HIGH':
            stats['high_confidence'] += 1
        elif outcome_data['confidence'] == 'MEDIUM':
            stats['medium_confidence'] += 1
        else:
            stats['low_confidence'] += 1

    db.close()

    # Create output structure
    output = {
        "agent_id": AGENT_ID,
        "docs_range": f"{START_LINE}-{END_LINE}",
        "total_docs": len(my_ids),
        "labeling_date": datetime.now().strftime("%Y-%m-%d"),
        "method": "OUTCOME_ONLY",
        "documents": documents,
        "summary": {
            "total_labeled": stats['total'],
            "high_confidence": stats['high_confidence'],
            "medium_confidence": stats['medium_confidence'],
            "low_confidence": stats['low_confidence'],
            "outcome_distribution": stats['outcomes']
        }
    }

    # Save to file
    print(f"\nSaving results to {OUTPUT_FILE}...")
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "="*60)
    print("LABELING COMPLETE!")
    print("="*60)
    print(f"Total documents labeled: {stats['total']}")
    print(f"\nConfidence distribution:")
    print(f"  HIGH:   {stats['high_confidence']} ({stats['high_confidence']/stats['total']*100:.1f}%)")
    print(f"  MEDIUM: {stats['medium_confidence']} ({stats['medium_confidence']/stats['total']*100:.1f}%)")
    print(f"  LOW:    {stats['low_confidence']} ({stats['low_confidence']/stats['total']*100:.1f}%)")
    print(f"\nOutcome distribution:")
    for outcome, count in stats['outcomes'].items():
        print(f"  {outcome:8s}: {count:3d} ({count/stats['total']*100:.1f}%)")
    print(f"\nOutput saved to: {OUTPUT_FILE}")
    print("="*60)


if __name__ == "__main__":
    main()
