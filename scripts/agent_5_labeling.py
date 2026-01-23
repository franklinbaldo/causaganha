#!/usr/bin/env python3
"""
Agent 5: Outcome labeling for documents 401-500
Extracts ONLY outcomes (WIN/LOSS/PARTIAL) from merit decisions
"""

import duckdb
import json
import re
from datetime import datetime
from pathlib import Path

# My assigned document IDs (lines 401-500)
AGENT_ID = 5
START_LINE = 401
END_LINE = 500

# File paths
IDS_FILE = Path("/home/user/causaganha/data/merit_decision_ids.txt")
DB_FILE = Path("/home/user/causaganha/data/causaganha_real.duckdb")
OUTPUT_FILE = Path("/home/user/causaganha/data/outcome_labels_agent_5.json")

# Outcome patterns (ordered by priority)
OUTCOME_PATTERNS = [
    # Clear outcomes
    (r'julgo\s+procedente', 'WIN', 'HIGH'),
    (r'julgo\s+improcedente', 'LOSS', 'HIGH'),
    (r'julgo\s+parcialmente\s+procedente', 'PARTIAL', 'HIGH'),

    # Appeals - author perspective
    (r'dar\s+provimento\s+(?:à|ao)\s+(?:apelação|recurso)(?:\s+interposta?)?\s+pelo\s+(?:autor|recorrente|apelante)', 'WIN', 'HIGH'),
    (r'negar\s+provimento\s+(?:à|ao)\s+(?:apelação|recurso)(?:\s+interposta?)?\s+pelo\s+(?:réu|recorrido|apelado|INSS)', 'WIN', 'HIGH'),
    (r'dar\s+provimento\s+(?:à|ao)\s+(?:apelação|recurso)(?:\s+interposta?)?\s+pelo\s+(?:réu|recorrido|apelado|INSS)', 'LOSS', 'HIGH'),
    (r'negar\s+provimento\s+(?:à|ao)\s+(?:apelação|recurso)(?:\s+interposta?)?\s+pelo\s+(?:autor|recorrente|apelante)', 'LOSS', 'HIGH'),

    # Generic appeal outcomes (less specific)
    (r'dar\s+provimento', 'WIN', 'MEDIUM'),  # Need context
    (r'negar\s+provimento', 'LOSS', 'MEDIUM'),

    # Condemnation
    (r'condenar\s+(?:o|a)\s+(?:réu|ré|recorrido|parte)', 'WIN', 'HIGH'),
    (r'absolver\s+(?:o|a)\s+(?:réu|ré)', 'LOSS', 'HIGH'),

    # Procedural dismissals (no merit)
    (r'extinguir\s+(?:o\s+processo\s+)?sem\s+(?:resolução\s+(?:de|do)\s+)?mérito', 'UNKNOWN', 'HIGH'),
    (r'não\s+conhecer', 'UNKNOWN', 'HIGH'),
]


def extract_outcome(texto: str, intimation_id: str) -> dict:
    """Extract outcome from decision text using pattern matching."""

    if not texto:
        return {
            "outcome_normalized": "UNKNOWN",
            "confidence": "LOW",
            "outcome_phrase": "No text available"
        }

    # Normalize text for matching
    texto_lower = texto.lower()

    # Try each pattern
    for pattern, outcome, confidence in OUTCOME_PATTERNS:
        match = re.search(pattern, texto_lower, re.IGNORECASE)
        if match:
            # Extract phrase (max 100 chars)
            start = max(0, match.start() - 20)
            end = min(len(texto), match.end() + 80)
            phrase = texto[start:end].strip()

            # Clean up phrase
            phrase = re.sub(r'\s+', ' ', phrase)
            if len(phrase) > 100:
                phrase = phrase[:97] + "..."

            return {
                "outcome_normalized": outcome,
                "confidence": confidence,
                "outcome_phrase": phrase
            }

    # No pattern matched
    return {
        "outcome_normalized": "UNKNOWN",
        "confidence": "LOW",
        "outcome_phrase": "No clear outcome pattern found"
    }


def main():
    print(f"🤖 Agent {AGENT_ID}: Starting outcome labeling")
    print(f"📄 Documents: {START_LINE}-{END_LINE} (100 total)")

    # Load document IDs
    print("\n📋 Loading document IDs...")
    with open(IDS_FILE) as f:
        all_ids = [line.strip() for line in f.readlines()]

    # Get my slice (0-indexed)
    my_ids = all_ids[START_LINE - 1:END_LINE]
    print(f"✓ Loaded {len(my_ids)} IDs")

    # Connect to database
    print(f"\n🔌 Connecting to database: {DB_FILE}")
    db = duckdb.connect(str(DB_FILE), read_only=True)

    # Process each document
    print("\n🏷️  Labeling outcomes...\n")
    documents = []
    stats = {
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
        print(f"[{i:3d}/100] Processing {intimation_id}... ", end="", flush=True)

        try:
            # Query database
            result = db.execute(
                "SELECT id, numero_processo, texto FROM intimations WHERE id = ?",
                [intimation_id]
            ).fetchone()

            if not result:
                print(f"❌ NOT FOUND")
                documents.append({
                    "intimation_id": intimation_id,
                    "numero_processo": "UNKNOWN",
                    "outcome_normalized": "UNKNOWN",
                    "confidence": "LOW",
                    "outcome_phrase": "Document not found in database"
                })
                stats["low_confidence"] += 1
                stats["outcome_distribution"]["UNKNOWN"] += 1
                continue

            intimation_id_db, numero_processo, texto = result

            # Extract outcome
            outcome = extract_outcome(texto, intimation_id)

            # Build document record
            doc = {
                "intimation_id": intimation_id,
                "numero_processo": numero_processo,
                **outcome
            }
            documents.append(doc)

            # Update stats
            conf = outcome["confidence"]
            if conf == "HIGH":
                stats["high_confidence"] += 1
            elif conf == "MEDIUM":
                stats["medium_confidence"] += 1
            else:
                stats["low_confidence"] += 1

            stats["outcome_distribution"][outcome["outcome_normalized"]] += 1

            # Print result
            emoji = "✅" if conf == "HIGH" else "⚠️" if conf == "MEDIUM" else "❓"
            print(f"{emoji} {outcome['outcome_normalized']:7s} ({conf})")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            documents.append({
                "intimation_id": intimation_id,
                "numero_processo": "ERROR",
                "outcome_normalized": "UNKNOWN",
                "confidence": "LOW",
                "outcome_phrase": f"Error: {str(e)[:80]}"
            })
            stats["low_confidence"] += 1
            stats["outcome_distribution"]["UNKNOWN"] += 1

    db.close()

    # Build output JSON
    output = {
        "agent_id": AGENT_ID,
        "docs_range": f"{START_LINE}-{END_LINE}",
        "total_docs": len(my_ids),
        "labeling_date": datetime.now().strftime("%Y-%m-%d"),
        "method": "OUTCOME_ONLY",
        "documents": documents,
        "summary": {
            "total_labeled": len(documents),
            **stats
        }
    }

    # Save to file
    print(f"\n💾 Saving results to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"Total documents:     {stats['high_confidence'] + stats['medium_confidence'] + stats['low_confidence']}")
    print(f"High confidence:     {stats['high_confidence']}")
    print(f"Medium confidence:   {stats['medium_confidence']}")
    print(f"Low confidence:      {stats['low_confidence']}")
    print()
    print("Outcome distribution:")
    for outcome, count in stats['outcome_distribution'].items():
        pct = (count / len(documents) * 100) if documents else 0
        print(f"  {outcome:8s}: {count:3d} ({pct:5.1f}%)")
    print("="*60)
    print(f"\n✅ Complete! Results saved to:")
    print(f"   {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
