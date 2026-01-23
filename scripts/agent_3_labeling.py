#!/usr/bin/env python3
"""
Agent 3: Outcome-Only Labeling Script
Documents: Lines 201-300 from merit_decision_ids.txt
"""

import json
import re
from datetime import datetime
from pathlib import Path
import duckdb

# Paths
DB_PATH = "/home/user/causaganha/data/causaganha_real.duckdb"
IDS_FILE = "/home/user/causaganha/data/merit_decision_ids.txt"
OUTPUT_FILE = "/home/user/causaganha/data/outcome_labels_agent_3.json"

# Agent configuration
AGENT_ID = 3
START_LINE = 201
END_LINE = 300

# Outcome patterns (from instructions)
OUTCOME_PATTERNS = {
    "WIN": [
        r"julgo\s+procedente",
        r"dar\s+provimento\s+(?:à|a)\s+(?:apelação|recurso)(?:\s+interposta)?\s+pelo\s+(?:autor|recorrente|apelante)",
        r"negar\s+provimento\s+(?:à|ao|a)\s+(?:apelação|recurso)(?:\s+do)?\s+(?:réu|INSS|recorrido|apelado)",
        r"condenar\s+o\s+réu",
        r"provimento\s+ao\s+recurso\s+do\s+autor",
        r"procedência\s+(?:do|dos)\s+pedido",
        r"acolh[oe]\s+o\s+pedido",
        r"dar\s+provimento.*autor",
    ],
    "LOSS": [
        r"julgo\s+improcedente",
        r"dar\s+provimento\s+(?:à|a)\s+(?:apelação|recurso)(?:\s+interposta)?\s+pelo\s+(?:réu|INSS|recorrido|apelado)",
        r"negar\s+provimento\s+(?:à|ao|a)\s+(?:apelação|recurso)(?:\s+do)?\s+(?:autor|recorrente|apelante)",
        r"absolver\s+o\s+réu",
        r"improcedência\s+(?:do|dos)\s+pedido",
        r"rejeitar\s+o\s+pedido",
        r"dar\s+provimento.*(?:réu|INSS)",
    ],
    "PARTIAL": [
        r"julgo\s+parcialmente\s+procedente",
        r"procedência\s+parcial",
        r"acolho\s+parcialmente",
        r"provimento\s+parcial",
    ],
    "UNKNOWN": [
        r"extinguir\s+(?:o\s+processo\s+)?sem\s+(?:resolução\s+do\s+)?mérito",
        r"não\s+conhec[oe]",
        r"incompetência",
        r"ilegitimidade",
    ],
}


def extract_outcome(texto: str, intimation_id: str) -> dict:
    """Extract outcome from decision text."""
    texto_lower = texto.lower()

    # Try to find outcome patterns
    for outcome, patterns in OUTCOME_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, texto_lower, re.IGNORECASE)
            if match:
                # Extract phrase with context
                start = max(0, match.start() - 20)
                end = min(len(texto), match.end() + 80)
                phrase = texto[start:end].strip()

                # Clean up phrase (remove extra whitespace)
                phrase = re.sub(r'\s+', ' ', phrase)

                # Truncate to 100 chars
                if len(phrase) > 100:
                    phrase = phrase[:97] + "..."

                return {
                    "outcome_normalized": outcome,
                    "confidence": "HIGH",
                    "outcome_phrase": phrase,
                }

    # No clear pattern found
    return {
        "outcome_normalized": "UNKNOWN",
        "confidence": "LOW",
        "outcome_phrase": "No clear outcome pattern identified",
    }


def main():
    print(f"🤖 Agent {AGENT_ID}: Starting outcome labeling...")
    print(f"📋 Document range: {START_LINE}-{END_LINE}")

    # Load document IDs
    with open(IDS_FILE) as f:
        all_ids = [line.strip() for line in f.readlines()]

    # Get my slice (0-indexed)
    my_ids = all_ids[START_LINE - 1 : END_LINE]
    print(f"📄 Loaded {len(my_ids)} document IDs")

    # Connect to database
    db = duckdb.connect(DB_PATH, read_only=True)
    print(f"🗄️  Connected to database: {DB_PATH}")

    # Process each document
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
            "UNKNOWN": 0,
        },
    }

    for i, intimation_id in enumerate(my_ids, 1):
        print(f"[{i}/{len(my_ids)}] Processing intimation {intimation_id}...", end=" ")

        # Query database
        result = db.execute(
            "SELECT id, numero_processo, texto FROM intimations WHERE id = ?",
            [intimation_id]
        ).fetchone()

        if not result:
            print("❌ NOT FOUND")
            continue

        _, numero_processo, texto = result

        # Extract outcome
        outcome_data = extract_outcome(texto, intimation_id)

        # Build document entry
        doc = {
            "intimation_id": intimation_id,
            "numero_processo": numero_processo,
            **outcome_data,
        }

        documents.append(doc)

        # Update stats
        stats["total_labeled"] += 1
        stats["outcome_distribution"][outcome_data["outcome_normalized"]] += 1

        if outcome_data["confidence"] == "HIGH":
            stats["high_confidence"] += 1
        elif outcome_data["confidence"] == "MEDIUM":
            stats["medium_confidence"] += 1
        else:
            stats["low_confidence"] += 1

        print(f"✅ {outcome_data['outcome_normalized']} ({outcome_data['confidence']})")

    # Close database
    db.close()

    # Build output
    output = {
        "agent_id": AGENT_ID,
        "docs_range": f"{START_LINE}-{END_LINE}",
        "total_docs": len(my_ids),
        "labeling_date": datetime.now().strftime("%Y-%m-%d"),
        "method": "OUTCOME_ONLY",
        "documents": documents,
        "summary": stats,
    }

    # Save output
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved {len(documents)} labeled documents to {OUTPUT_FILE}")
    print(f"\n📊 Summary:")
    print(f"   Total labeled: {stats['total_labeled']}")
    print(f"   High confidence: {stats['high_confidence']}")
    print(f"   Medium confidence: {stats['medium_confidence']}")
    print(f"   Low confidence: {stats['low_confidence']}")
    print(f"\n📈 Outcome distribution:")
    for outcome, count in stats["outcome_distribution"].items():
        pct = (count / stats["total_labeled"] * 100) if stats["total_labeled"] > 0 else 0
        print(f"   {outcome}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    main()
