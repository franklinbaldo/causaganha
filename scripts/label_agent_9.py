#!/usr/bin/env python3
"""
Agent 9: Outcome labeling for lines 801-900 of merit_decision_ids.txt
SIMPLIFIED VERSION: Extract ONLY outcomes (party/lawyer data already in parquets)
"""

import duckdb
import json
import re
from datetime import datetime
from pathlib import Path

# Configuration
AGENT_ID = 9
START_LINE = 801
END_LINE = 900
DB_PATH = "/home/user/causaganha/data/causaganha_real.duckdb"
IDS_FILE = "/home/user/causaganha/data/merit_decision_ids.txt"
OUTPUT_FILE = "/home/user/causaganha/data/outcome_labels_agent_9.json"

# Outcome patterns (case-insensitive)
OUTCOME_PATTERNS = {
    'WIN': [
        r'julgo\s+procedente(?!\s+em\s+parte)',
        r'dar\s+provimento\s+(?:à|ao)\s+(?:apelação|apelacao|recurso)(?:\s+interposta)?(?:\s+pelo?\s+(?:autor|apelante|recorrente))?',
        r'condenar\s+o\s+(?:réu|reu|recorrido|apelado)',
        r'negar\s+provimento\s+(?:à|ao)\s+(?:apelação|apelacao|recurso)(?:\s+interposta)?(?:\s+pelo?\s+(?:réu|reu|recorrido|apelado|INSS))',
        r'manter\s+a\s+sentença(?:\s+de\s+procedência)?',
    ],
    'LOSS': [
        r'julgo\s+improcedente',
        r'dar\s+provimento\s+(?:à|ao)\s+(?:apelação|apelacao|recurso)(?:\s+interposta)?(?:\s+pelo?\s+(?:réu|reu|recorrido|apelado|INSS))',
        r'absolver\s+o\s+(?:réu|reu)',
        r'negar\s+provimento\s+(?:à|ao)\s+(?:apelação|apelacao|recurso)(?:\s+interposta)?(?:\s+pelo?\s+(?:autor|apelante|recorrente))',
    ],
    'PARTIAL': [
        r'julgo\s+parcialmente\s+procedente',
        r'dar\s+parcial\s+provimento',
        r'procedência\s+parcial',
        r'procedencia\s+parcial',
    ],
    'UNKNOWN': [
        r'extinguir\s+(?:o\s+processo\s+)?sem\s+(?:resolução\s+(?:de|do)\s+)?mérito',
        r'extinguir\s+(?:o\s+processo\s+)?sem\s+(?:resolucao\s+(?:de|do)\s+)?merito',
        r'não\s+conhecer\s+(?:do\s+recurso|da\s+apelação)',
        r'nao\s+conhecer\s+(?:do\s+recurso|da\s+apelacao)',
        r'inépcia\s+da\s+inicial',
        r'inepcia\s+da\s+inicial',
    ]
}

def extract_outcome(texto: str, intimation_id: str) -> dict:
    """
    Extract outcome from decision text.
    Returns dict with outcome_normalized, confidence, and outcome_phrase.
    """
    texto_lower = texto.lower()

    # Try each pattern
    for outcome, patterns in OUTCOME_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, texto_lower, re.IGNORECASE)
            if match:
                # Extract phrase with context (±50 chars)
                start = max(0, match.start() - 20)
                end = min(len(texto), match.end() + 80)
                phrase = texto[start:end].strip()

                # Clean up phrase (remove excessive whitespace, line breaks)
                phrase = re.sub(r'\s+', ' ', phrase)
                phrase = phrase[:100]  # Max 100 chars

                # Determine confidence
                confidence = "HIGH"
                if outcome == "UNKNOWN":
                    confidence = "MEDIUM"

                return {
                    "outcome_normalized": outcome,
                    "confidence": confidence,
                    "outcome_phrase": phrase
                }

    # No pattern matched
    # Try to find any dispositivo section for LOW confidence guess
    dispositivo_match = re.search(
        r'(?:ante|diante)\s+(?:o\s+)?exposto|(?:isto\s+posto|pelo\s+exposto)|dispositivo',
        texto_lower
    )

    if dispositivo_match:
        start = dispositivo_match.start()
        end = min(len(texto), start + 200)
        phrase = texto[start:end].strip()
        phrase = re.sub(r'\s+', ' ', phrase)[:100]

        return {
            "outcome_normalized": "UNKNOWN",
            "confidence": "LOW",
            "outcome_phrase": phrase
        }

    return {
        "outcome_normalized": "UNKNOWN",
        "confidence": "LOW",
        "outcome_phrase": "No clear dispositivo found"
    }

def main():
    print(f"🤖 Agent {AGENT_ID} starting outcome labeling...")
    print(f"📄 Documents: lines {START_LINE}-{END_LINE}")

    # Load document IDs
    with open(IDS_FILE) as f:
        all_ids = [line.strip() for line in f.readlines()]

    # Get my slice (0-indexed)
    start_idx = START_LINE - 1
    end_idx = END_LINE
    my_ids = all_ids[start_idx:end_idx]

    print(f"✅ Loaded {len(my_ids)} document IDs")

    # Connect to database
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

    for idx, intimation_id in enumerate(my_ids, 1):
        print(f"\n[{idx}/{len(my_ids)}] Processing {intimation_id}...", end=" ")

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
            outcome_data = extract_outcome(texto, intimation_id)

            # Build document entry
            doc = {
                "intimation_id": intimation_id,
                "numero_processo": numero_processo,
                **outcome_data
            }
            documents.append(doc)

            # Update stats
            conf = outcome_data["confidence"].lower() + "_confidence"
            stats[conf] += 1
            stats["outcome_distribution"][outcome_data["outcome_normalized"]] += 1

            print(f"✅ {outcome_data['outcome_normalized']} ({outcome_data['confidence']})")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            documents.append({
                "intimation_id": intimation_id,
                "numero_processo": "ERROR",
                "outcome_normalized": "UNKNOWN",
                "confidence": "LOW",
                "outcome_phrase": f"Error processing: {str(e)}"
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
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n\n✅ Labeling complete!")
    print(f"📊 Summary:")
    print(f"   - Total labeled: {len(documents)}")
    print(f"   - High confidence: {stats['high_confidence']}")
    print(f"   - Medium confidence: {stats['medium_confidence']}")
    print(f"   - Low confidence: {stats['low_confidence']}")
    print(f"\n📈 Outcome distribution:")
    for outcome, count in stats['outcome_distribution'].items():
        pct = (count / len(documents)) * 100 if documents else 0
        print(f"   - {outcome}: {count} ({pct:.1f}%)")
    print(f"\n💾 Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
