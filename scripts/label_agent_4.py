#!/usr/bin/env python3
"""
Agent 4: Outcome labeling for documents 301-400
"""

import duckdb
import json
import re
from datetime import datetime
from pathlib import Path

# Document IDs for Agent 4 (lines 301-400)
DOCUMENT_IDS = [
    "499296398", "495550222", "495088037", "498342953", "495335463",
    "498128341", "495274273", "495305802", "496231316", "498336119",
    "495625935", "498343677", "495674191", "495388610", "503844875",
    "495630699", "495459890", "500402095", "495629457", "504277276",
    "505243605", "495461669", "500468280", "498336198", "498101420",
    "498330128", "498341132", "507723086", "494575877", "499438957",
    "495210865", "500541702", "495091061", "496975709", "499076929",
    "495609085", "506252821", "497857527", "495609661", "495084479",
    "507754413", "506358296", "494894970", "506280394", "495231372",
    "500349345", "498331390", "494938652", "495626446", "495332989",
    "494868465", "506360958", "503401141", "498054273", "495626108",
    "500236355", "497735314", "499296553", "498340818", "498310654",
    "496494857", "501116758", "502026857", "495082776", "504501167",
    "495487000", "498219206", "504064237", "495560751", "503216918",
    "496893249", "505886584", "507853919", "495034119", "495244992",
    "498951032", "504122848", "497952194", "506126260", "502350458",
    "495465853", "507771592", "495208295", "496902801", "498030984",
    "502523194", "495833810", "497206009", "499028448", "495626344",
    "495129687", "495386346", "499401933", "495481621", "495337822",
    "505207288", "501865336", "496018330", "495626227"
]

def extract_outcome(texto: str, intimation_id: str) -> dict:
    """Extract outcome from decision text."""

    # Normalize text for pattern matching
    texto_lower = texto.lower()

    # Patterns for WIN outcomes
    win_patterns = [
        (r"julgo\s+procedente(?!\s+em\s+parte)", "julgo procedente", "HIGH"),
        (r"dar\s+provimento\s+(?:à|a|ao)\s+(?:apela[cç][aã]o|recurso)(?!\s+(?:parcial|em\s+parte))", "dar provimento", "HIGH"),
        (r"condenar\s+o\s+r[eé]u", "condenar o réu", "HIGH"),
        (r"defiro\s+o\s+pedido", "defiro o pedido", "MEDIUM"),
        (r"procedência\s+do\s+pedido", "procedência do pedido", "MEDIUM"),
    ]

    # Patterns for LOSS outcomes
    loss_patterns = [
        (r"julgo\s+improcedente", "julgo improcedente", "HIGH"),
        (r"negar\s+provimento\s+(?:à|a|ao)\s+(?:apela[cç][aã]o|recurso)", "negar provimento", "HIGH"),
        (r"absolver\s+o\s+r[eé]u", "absolver o réu", "HIGH"),
        (r"indefiro\s+o\s+pedido", "indefiro o pedido", "MEDIUM"),
        (r"improcedência\s+do\s+pedido", "improcedência do pedido", "MEDIUM"),
    ]

    # Patterns for PARTIAL outcomes
    partial_patterns = [
        (r"julgo\s+parcialmente\s+procedente", "julgo parcialmente procedente", "HIGH"),
        (r"procedente\s+em\s+parte", "procedente em parte", "HIGH"),
        (r"dar\s+provimento\s+parcial", "dar provimento parcial", "HIGH"),
        (r"dar\s+parcial\s+provimento", "dar parcial provimento", "HIGH"),
    ]

    # Patterns for UNKNOWN outcomes (no merit)
    unknown_patterns = [
        (r"extingu[oi]\s+(?:o\s+processo\s+)?sem\s+(?:resolu[çc][ãa]o|julgamento)\s+(?:do|de)\s+m[ée]rito", "extinguir sem mérito", "HIGH"),
        (r"n[ãa]o\s+conhec[oe]", "não conhecer", "HIGH"),
        (r"inviabilidade\s+de\s+an[aá]lise\s+do\s+m[ée]rito", "inviabilidade de análise do mérito", "MEDIUM"),
    ]

    # Check patterns in order: PARTIAL > WIN > LOSS > UNKNOWN
    # (PARTIAL first because it contains "procedente" which would match WIN)

    for pattern, phrase, confidence in partial_patterns:
        match = re.search(pattern, texto_lower)
        if match:
            # Extract actual phrase from original text (preserving case)
            start = match.start()
            end = min(start + 100, len(texto))
            outcome_phrase = texto[start:end].strip()
            if len(outcome_phrase) > 100:
                outcome_phrase = outcome_phrase[:97] + "..."

            return {
                "intimation_id": intimation_id,
                "outcome_normalized": "PARTIAL",
                "confidence": confidence,
                "outcome_phrase": outcome_phrase
            }

    for pattern, phrase, confidence in win_patterns:
        match = re.search(pattern, texto_lower)
        if match:
            start = match.start()
            end = min(start + 100, len(texto))
            outcome_phrase = texto[start:end].strip()
            if len(outcome_phrase) > 100:
                outcome_phrase = outcome_phrase[:97] + "..."

            return {
                "intimation_id": intimation_id,
                "outcome_normalized": "WIN",
                "confidence": confidence,
                "outcome_phrase": outcome_phrase
            }

    for pattern, phrase, confidence in loss_patterns:
        match = re.search(pattern, texto_lower)
        if match:
            start = match.start()
            end = min(start + 100, len(texto))
            outcome_phrase = texto[start:end].strip()
            if len(outcome_phrase) > 100:
                outcome_phrase = outcome_phrase[:97] + "..."

            return {
                "intimation_id": intimation_id,
                "outcome_normalized": "LOSS",
                "confidence": confidence,
                "outcome_phrase": outcome_phrase
            }

    for pattern, phrase, confidence in unknown_patterns:
        match = re.search(pattern, texto_lower)
        if match:
            start = match.start()
            end = min(start + 100, len(texto))
            outcome_phrase = texto[start:end].strip()
            if len(outcome_phrase) > 100:
                outcome_phrase = outcome_phrase[:97] + "..."

            return {
                "intimation_id": intimation_id,
                "outcome_normalized": "UNKNOWN",
                "confidence": confidence,
                "outcome_phrase": outcome_phrase
            }

    # No clear pattern found
    return {
        "intimation_id": intimation_id,
        "outcome_normalized": "UNKNOWN",
        "confidence": "LOW",
        "outcome_phrase": "No clear outcome pattern found"
    }


def main():
    # Connect to database
    db_path = "/home/user/causaganha/data/causaganha_real.duckdb"
    db = duckdb.connect(db_path, read_only=True)

    documents = []
    processed = 0

    print(f"Processing {len(DOCUMENT_IDS)} documents for Agent 4...")

    for intimation_id in DOCUMENT_IDS:
        processed += 1

        # Query database
        result = db.execute(
            "SELECT id, numero_processo, texto FROM intimations WHERE id = ?",
            [intimation_id]
        ).fetchone()

        if not result:
            print(f"⚠️  Document {intimation_id} not found in database")
            documents.append({
                "intimation_id": intimation_id,
                "numero_processo": "UNKNOWN",
                "outcome_normalized": "UNKNOWN",
                "confidence": "LOW",
                "outcome_phrase": "Document not found in database"
            })
            continue

        doc_id, numero_processo, texto = result

        # Extract outcome
        outcome = extract_outcome(texto, intimation_id)
        outcome["numero_processo"] = numero_processo

        documents.append(outcome)

        if processed % 10 == 0:
            print(f"  Processed {processed}/{len(DOCUMENT_IDS)} documents...")

    db.close()

    # Calculate summary statistics
    outcome_dist = {"WIN": 0, "LOSS": 0, "PARTIAL": 0, "UNKNOWN": 0}
    confidence_dist = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for doc in documents:
        outcome_dist[doc["outcome_normalized"]] += 1
        confidence_dist[doc["confidence"]] += 1

    # Build output
    output = {
        "agent_id": 4,
        "docs_range": "301-400",
        "total_docs": len(DOCUMENT_IDS),
        "labeling_date": datetime.now().strftime("%Y-%m-%d"),
        "method": "OUTCOME_ONLY",
        "documents": documents,
        "summary": {
            "total_labeled": len(documents),
            "high_confidence": confidence_dist["HIGH"],
            "medium_confidence": confidence_dist["MEDIUM"],
            "low_confidence": confidence_dist["LOW"],
            "outcome_distribution": outcome_dist
        }
    }

    # Save to file
    output_path = Path("/home/user/causaganha/data/outcome_labels_agent_4.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Labeling complete!")
    print(f"📊 Summary:")
    print(f"   Total: {len(documents)}")
    print(f"   WIN: {outcome_dist['WIN']}")
    print(f"   LOSS: {outcome_dist['LOSS']}")
    print(f"   PARTIAL: {outcome_dist['PARTIAL']}")
    print(f"   UNKNOWN: {outcome_dist['UNKNOWN']}")
    print(f"\n   High confidence: {confidence_dist['HIGH']}")
    print(f"   Medium confidence: {confidence_dist['MEDIUM']}")
    print(f"   Low confidence: {confidence_dist['LOW']}")
    print(f"\n💾 Output saved to: {output_path}")


if __name__ == "__main__":
    main()
