#!/usr/bin/env python3
"""
Agent 6 - Outcome Labeling Task
Extracts outcomes from 100 merit decisions (lines 501-600)
"""

import duckdb
import json
import re
from datetime import date
from pathlib import Path

# Configuration
AGENT_ID = 6
START_LINE = 501
END_LINE = 600
DB_PATH = "/home/user/causaganha/data/causaganha_real.duckdb"
IDS_FILE = "/home/user/causaganha/data/merit_decision_ids.txt"
OUTPUT_FILE = "/home/user/causaganha/data/outcome_labels_agent_6.json"

# Outcome patterns (ordered by priority)
OUTCOME_PATTERNS = [
    # Clear wins
    (r"julgo\s+procedente", "WIN", "HIGH"),
    (r"dar\s+provimento\s+(?:à|ao)\s+(?:apela[çc][ãa]o|recurso)(?:\s+interposta?)?\s+(?:pelo|do|da)\s+(?:autor|apelante|recorrente|parte\s+autora)", "WIN", "HIGH"),
    (r"negar\s+provimento\s+(?:à|ao)\s+(?:apela[çc][ãa]o|recurso)(?:\s+interposta?)?\s+(?:pelo|do|da)\s+(?:r[ée]u|apelado|recorrido|parte\s+r[ée]|INSS|Banco)", "WIN", "HIGH"),
    (r"condenar\s+o\s+r[ée]u", "WIN", "HIGH"),

    # Clear losses
    (r"julgo\s+improcedente", "LOSS", "HIGH"),
    (r"negar\s+provimento\s+(?:à|ao)\s+(?:apela[çc][ãa]o|recurso)(?:\s+interposta?)?\s+(?:pelo|do|da)\s+(?:autor|apelante|recorrente|parte\s+autora)", "LOSS", "HIGH"),
    (r"dar\s+provimento\s+(?:à|ao)\s+(?:apela[çc][ãa]o|recurso)(?:\s+interposta?)?\s+(?:pelo|do|da)\s+(?:r[ée]u|apelado|recorrido|parte\s+r[ée]|INSS|Banco)", "LOSS", "HIGH"),
    (r"absolver\s+o\s+r[ée]u", "LOSS", "HIGH"),

    # Partial
    (r"julgo\s+parcialmente\s+procedente", "PARTIAL", "HIGH"),

    # Unknown/No merit
    (r"extinguir(?:\s+o\s+processo)?\s+sem\s+(?:resolu[çc][ãa]o\s+do?\s+)?m[ée]rito", "UNKNOWN", "HIGH"),
    (r"n[ãa]o\s+conhecer", "UNKNOWN", "MEDIUM"),

    # Generic provimento/desprovimento (lower confidence)
    (r"dar\s+provimento", "WIN", "MEDIUM"),
    (r"negar\s+provimento", "LOSS", "MEDIUM"),
    (r"desprovido", "LOSS", "MEDIUM"),
    (r"provido", "WIN", "MEDIUM"),
]

def extract_outcome(texto: str, intimation_id: str, numero_processo: str) -> dict:
    """Extract outcome from decision text."""
    if not texto:
        return {
            "intimation_id": intimation_id,
            "numero_processo": numero_processo,
            "outcome_normalized": "UNKNOWN",
            "confidence": "LOW",
            "outcome_phrase": "No text available"
        }

    # Normalize text for pattern matching
    texto_lower = texto.lower()

    # Try each pattern
    for pattern, outcome, confidence in OUTCOME_PATTERNS:
        match = re.search(pattern, texto_lower, re.IGNORECASE)
        if match:
            # Extract phrase with context
            start = max(0, match.start() - 20)
            end = min(len(texto), match.end() + 80)
            phrase = texto[start:end].strip()

            # Clean up phrase
            phrase = re.sub(r'\s+', ' ', phrase)
            if len(phrase) > 100:
                phrase = phrase[:97] + "..."

            return {
                "intimation_id": intimation_id,
                "numero_processo": numero_processo,
                "outcome_normalized": outcome,
                "confidence": confidence,
                "outcome_phrase": phrase
            }

    # No pattern matched - try to find any relevant snippet
    keywords = ["julgo", "sentença", "acórdão", "provimento", "procedente"]
    for keyword in keywords:
        if keyword in texto_lower:
            idx = texto_lower.find(keyword)
            start = max(0, idx - 20)
            end = min(len(texto), idx + 80)
            phrase = texto[start:end].strip()
            phrase = re.sub(r'\s+', ' ', phrase)
            if len(phrase) > 100:
                phrase = phrase[:97] + "..."

            return {
                "intimation_id": intimation_id,
                "numero_processo": numero_processo,
                "outcome_normalized": "UNKNOWN",
                "confidence": "LOW",
                "outcome_phrase": phrase
            }

    return {
        "intimation_id": intimation_id,
        "numero_processo": numero_processo,
        "outcome_normalized": "UNKNOWN",
        "confidence": "LOW",
        "outcome_phrase": "No clear outcome pattern found"
    }

def main():
    print(f"🎯 Agent {AGENT_ID} - Outcome Labeling Task")
    print(f"📄 Document range: {START_LINE}-{END_LINE}")
    print(f"💾 Database: {DB_PATH}")
    print(f"📤 Output: {OUTPUT_FILE}\n")

    # Load document IDs
    print("📖 Loading document IDs...")
    with open(IDS_FILE) as f:
        all_ids = [line.strip() for line in f.readlines()]

    # Get Agent 6's slice (lines 501-600 = indices 500-599)
    start_idx = START_LINE - 1
    end_idx = END_LINE
    my_ids = all_ids[start_idx:end_idx]

    print(f"✅ Loaded {len(my_ids)} document IDs\n")

    # Connect to database
    print("🔌 Connecting to database...")
    db = duckdb.connect(DB_PATH, read_only=True)

    # Process each document
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

    print("🔍 Processing documents...\n")
    for i, intimation_id in enumerate(my_ids, 1):
        print(f"[{i:3d}/100] Processing {intimation_id}...", end=" ")

        try:
            # Query database
            result = db.execute(
                "SELECT id, numero_processo, texto FROM intimations WHERE id = ?",
                [intimation_id]
            ).fetchone()

            if not result:
                print("❌ NOT FOUND")
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
            doc = extract_outcome(texto, intimation_id_db, numero_processo)
            documents.append(doc)

            # Update stats
            if doc["confidence"] == "HIGH":
                stats["high_confidence"] += 1
            elif doc["confidence"] == "MEDIUM":
                stats["medium_confidence"] += 1
            else:
                stats["low_confidence"] += 1

            stats["outcome_distribution"][doc["outcome_normalized"]] += 1

            print(f"✅ {doc['outcome_normalized']} ({doc['confidence']})")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            documents.append({
                "intimation_id": intimation_id,
                "numero_processo": "ERROR",
                "outcome_normalized": "UNKNOWN",
                "confidence": "LOW",
                "outcome_phrase": f"Error: {str(e)}"
            })
            stats["low_confidence"] += 1
            stats["outcome_distribution"]["UNKNOWN"] += 1

    db.close()

    # Create output
    output = {
        "agent_id": AGENT_ID,
        "docs_range": f"{START_LINE}-{END_LINE}",
        "total_docs": len(my_ids),
        "labeling_date": str(date.today()),
        "method": "OUTCOME_ONLY",
        "documents": documents,
        "summary": {
            "total_labeled": len(documents),
            "high_confidence": stats["high_confidence"],
            "medium_confidence": stats["medium_confidence"],
            "low_confidence": stats["low_confidence"],
            "outcome_distribution": stats["outcome_distribution"]
        }
    }

    # Save to file
    print(f"\n💾 Saving results to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"Total labeled:      {output['summary']['total_labeled']}")
    print(f"High confidence:    {stats['high_confidence']}")
    print(f"Medium confidence:  {stats['medium_confidence']}")
    print(f"Low confidence:     {stats['low_confidence']}")
    print("\nOutcome Distribution:")
    for outcome, count in stats["outcome_distribution"].items():
        pct = (count / len(documents)) * 100 if documents else 0
        print(f"  {outcome:8s}: {count:3d} ({pct:.1f}%)")
    print("="*60)
    print(f"\n✅ Done! Results saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
