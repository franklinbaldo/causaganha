#!/usr/bin/env python3
"""
Agent 2: Outcome-Only Labeling Script
Processes lines 101-200 from merit_decision_ids.txt
"""

import duckdb
import json
import re
from datetime import datetime
from pathlib import Path

# Configuration
AGENT_ID = 2
START_LINE = 101
END_LINE = 200
DB_PATH = "/home/user/causaganha/data/causaganha_real.duckdb"
IDS_FILE = "/home/user/causaganha/data/merit_decision_ids.txt"
OUTPUT_FILE = "/home/user/causaganha/data/outcome_labels_agent_2.json"

# Outcome patterns (compiled regex for efficiency)
OUTCOME_PATTERNS = [
    # Clear WIN patterns
    (r"julgo?\s+procedente(?!\s+(?:em\s+)?parte)", "WIN", "HIGH"),
    (r"condenar?\s+(?:o\s+)?(?:réu|reclamad[oa]|apelad[oa])", "WIN", "HIGH"),
    (r"(?:dar|dou)\s+provimento\s+(?:à|ao)\s+(?:apelação|recurso)(?:\s+(?:do|da)\s+(?:autor|reclamante|apelante))?", "WIN", "HIGH"),
    (r"negar?\s+provimento\s+(?:à|ao)\s+(?:apelação|recurso)\s+(?:do|da)\s+(?:réu|reclamad[oa]|INSS|apelad[oa])", "WIN", "HIGH"),
    (r"provimento\s+(?:à|ao)\s+(?:apelação|recurso)\s+(?:do|da)\s+autor", "WIN", "HIGH"),
    (r"mantém\s+a\s+sentença\s+(?:de\s+)?procedência", "WIN", "HIGH"),

    # Clear LOSS patterns
    (r"julgo?\s+improcedente", "LOSS", "HIGH"),
    (r"absolver?\s+(?:o\s+)?(?:réu|reclamad[oa])", "LOSS", "HIGH"),
    (r"(?:dar|dou)\s+provimento\s+(?:à|ao)\s+(?:apelação|recurso)\s+(?:do|da)\s+(?:réu|reclamad[oa]|INSS)", "LOSS", "HIGH"),
    (r"negar?\s+provimento\s+(?:à|ao)\s+(?:apelação|recurso)(?:\s+(?:do|da)\s+(?:autor|reclamante))?", "LOSS", "HIGH"),
    (r"reforma\w*\s+a\s+sentença", "LOSS", "MEDIUM"),

    # PARTIAL patterns
    (r"julgo?\s+parcialmente\s+procedente", "PARTIAL", "HIGH"),
    (r"(?:dar|dou)\s+(?:parcial\s+)?provimento\s+(?:à|ao)\s+(?:apelação|recurso)", "PARTIAL", "MEDIUM"),
    (r"procedente\s+em\s+parte", "PARTIAL", "HIGH"),

    # UNKNOWN patterns
    (r"extinguir?\s+(?:o\s+processo\s+)?sem\s+(?:resolução\s+(?:de\s+)?)?mérito", "UNKNOWN", "HIGH"),
    (r"não\s+conhec(?:er|o)", "UNKNOWN", "HIGH"),
    (r"julgo?\s+extint[oa]", "UNKNOWN", "MEDIUM"),
]


def extract_outcome(texto: str, intimation_id: str) -> dict:
    """Extract outcome from decision text using pattern matching."""
    if not texto:
        return {
            "intimation_id": intimation_id,
            "outcome_normalized": "UNKNOWN",
            "confidence": "LOW",
            "outcome_phrase": "Empty text"
        }

    # Normalize text for matching
    texto_lower = texto.lower()

    # Try each pattern
    for pattern, outcome, confidence in OUTCOME_PATTERNS:
        match = re.search(pattern, texto_lower)
        if match:
            # Extract the matched phrase (max 100 chars)
            phrase = match.group(0)[:100]

            # Find the phrase in original text to preserve capitalization
            original_start = texto_lower.find(phrase.lower())
            if original_start >= 0:
                # Get some context (up to 100 chars)
                context_start = max(0, original_start - 20)
                context_end = min(len(texto), original_start + 80)
                phrase = texto[context_start:context_end].strip()
                if context_start > 0:
                    phrase = "..." + phrase
                if context_end < len(texto):
                    phrase = phrase + "..."

            return {
                "intimation_id": intimation_id,
                "outcome_normalized": outcome,
                "confidence": confidence,
                "outcome_phrase": phrase[:100]
            }

    # No pattern matched
    return {
        "intimation_id": intimation_id,
        "outcome_normalized": "UNKNOWN",
        "confidence": "LOW",
        "outcome_phrase": "No clear outcome pattern found"
    }


def process_documents():
    """Main processing function."""
    print(f"Agent {AGENT_ID}: Starting outcome labeling...")
    print(f"Document range: lines {START_LINE}-{END_LINE}")

    # Load document IDs
    print(f"\n1. Loading document IDs from {IDS_FILE}...")
    with open(IDS_FILE) as f:
        all_ids = [line.strip() for line in f.readlines() if line.strip()]

    # Get my slice (0-indexed)
    my_ids = all_ids[START_LINE - 1:END_LINE]
    print(f"   Loaded {len(my_ids)} document IDs")

    # Connect to database
    print(f"\n2. Connecting to database: {DB_PATH}...")
    db = duckdb.connect(DB_PATH, read_only=True)

    # Process each document
    print(f"\n3. Processing documents...")
    documents = []
    stats = {
        "total_labeled": 0,
        "high_confidence": 0,
        "medium_confidence": 0,
        "low_confidence": 0,
        "outcome_distribution": {
            "WIN": 0,
            "LOSS": 0,
            "PARTIAL": 0,
            "UNKNOWN": 0
        }
    }

    for i, intimation_id in enumerate(my_ids, 1):
        print(f"   [{i}/{len(my_ids)}] Processing {intimation_id}...", end=" ")

        # Query database
        result = db.execute(
            "SELECT id, numero_processo, texto FROM intimations WHERE id = ?",
            [intimation_id]
        ).fetchone()

        if not result:
            print(f"NOT FOUND in database!")
            documents.append({
                "intimation_id": intimation_id,
                "numero_processo": "UNKNOWN",
                "outcome_normalized": "UNKNOWN",
                "confidence": "LOW",
                "outcome_phrase": "Document not found in database"
            })
            stats["total_labeled"] += 1
            stats["low_confidence"] += 1
            stats["outcome_distribution"]["UNKNOWN"] += 1
            continue

        intimation_id_db, numero_processo, texto = result

        # Extract outcome
        outcome = extract_outcome(texto, intimation_id)
        outcome["numero_processo"] = numero_processo

        # Update stats
        stats["total_labeled"] += 1
        stats["outcome_distribution"][outcome["outcome_normalized"]] += 1

        if outcome["confidence"] == "HIGH":
            stats["high_confidence"] += 1
        elif outcome["confidence"] == "MEDIUM":
            stats["medium_confidence"] += 1
        else:
            stats["low_confidence"] += 1

        documents.append(outcome)
        print(f"{outcome['outcome_normalized']} ({outcome['confidence']})")

    db.close()

    # Create output JSON
    print(f"\n4. Creating output JSON...")
    output = {
        "agent_id": AGENT_ID,
        "docs_range": f"{START_LINE}-{END_LINE}",
        "total_docs": len(my_ids),
        "labeling_date": datetime.now().strftime("%Y-%m-%d"),
        "method": "OUTCOME_ONLY",
        "documents": documents,
        "summary": stats
    }

    # Save to file
    print(f"\n5. Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Print summary
    print("\n" + "="*60)
    print("LABELING COMPLETE!")
    print("="*60)
    print(f"\nTotal labeled: {stats['total_labeled']}")
    print(f"\nConfidence distribution:")
    print(f"  HIGH:   {stats['high_confidence']:3d} ({stats['high_confidence']/stats['total_labeled']*100:.1f}%)")
    print(f"  MEDIUM: {stats['medium_confidence']:3d} ({stats['medium_confidence']/stats['total_labeled']*100:.1f}%)")
    print(f"  LOW:    {stats['low_confidence']:3d} ({stats['low_confidence']/stats['total_labeled']*100:.1f}%)")
    print(f"\nOutcome distribution:")
    for outcome, count in stats['outcome_distribution'].items():
        print(f"  {outcome:8s}: {count:3d} ({count/stats['total_labeled']*100:.1f}%)")
    print(f"\nOutput saved to: {OUTPUT_FILE}")
    print("="*60)


if __name__ == "__main__":
    process_documents()
