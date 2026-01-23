#!/usr/bin/env python3
"""
Agent 7 - Outcome Labeling Script
Labels outcomes for merit decisions (lines 601-700)
"""

import json
import re
import duckdb
from datetime import datetime
from pathlib import Path

# Configuration
AGENT_ID = 7
START_LINE = 601
END_LINE = 700
DB_PATH = '/home/user/causaganha/data/causaganha_real.duckdb'
IDS_FILE = '/home/user/causaganha/data/merit_decision_ids.txt'
OUTPUT_FILE = '/home/user/causaganha/data/outcome_labels_agent_7.json'


def load_document_ids():
    """Load the 100 document IDs for this agent."""
    with open(IDS_FILE, 'r') as f:
        all_ids = [line.strip() for line in f.readlines()]

    # Get lines 601-700 (0-indexed: 600:700)
    my_ids = all_ids[600:700]
    print(f"Loaded {len(my_ids)} document IDs (lines {START_LINE}-{END_LINE})")
    return my_ids


def extract_outcome(texto, intimation_id):
    """
    Extract outcome from decision text.

    Returns:
        dict with outcome_normalized, confidence, outcome_phrase
    """
    if not texto:
        return {
            "outcome_normalized": "UNKNOWN",
            "confidence": "LOW",
            "outcome_phrase": "No text available"
        }

    # Normalize text for pattern matching
    texto_lower = texto.lower()

    # Pattern 1: Julgo procedente/improcedente
    if re.search(r'julgo\s+procedente', texto_lower):
        match = re.search(r'(julgo\s+procedente[^.]{0,80})', texto_lower)
        phrase = match.group(1) if match else "julgo procedente"
        return {
            "outcome_normalized": "WIN",
            "confidence": "HIGH",
            "outcome_phrase": phrase.strip()[:100]
        }

    if re.search(r'julgo\s+improcedente', texto_lower):
        match = re.search(r'(julgo\s+improcedente[^.]{0,80})', texto_lower)
        phrase = match.group(1) if match else "julgo improcedente"
        return {
            "outcome_normalized": "LOSS",
            "confidence": "HIGH",
            "outcome_phrase": phrase.strip()[:100]
        }

    if re.search(r'julgo\s+parcialmente\s+procedente', texto_lower):
        match = re.search(r'(julgo\s+parcialmente\s+procedente[^.]{0,80})', texto_lower)
        phrase = match.group(1) if match else "julgo parcialmente procedente"
        return {
            "outcome_normalized": "PARTIAL",
            "confidence": "HIGH",
            "outcome_phrase": phrase.strip()[:100]
        }

    # Pattern 2: Appeal decisions (dar/negar provimento)
    # Need to identify who appealed to determine outcome

    # Check for "dar provimento"
    if re.search(r'dar\s+provimento', texto_lower) or re.search(r'dou\s+provimento', texto_lower):
        # Try to identify appellant
        match = re.search(r'(d[aoãe][ro]?\s+provimento[^.]{0,100})', texto_lower)
        phrase = match.group(1) if match else "dar provimento"

        # Look for context to determine who appealed
        if re.search(r'(apela[çc][ãa]o|recurso)\s+(do|da|interposta?\s+pel[oa])\s+(autor|apelante|parte\s+autora)', texto_lower, re.IGNORECASE):
            # Author appealed and won
            return {
                "outcome_normalized": "WIN",
                "confidence": "HIGH",
                "outcome_phrase": phrase.strip()[:100]
            }
        elif re.search(r'(apela[çc][ãa]o|recurso)\s+(do|da|interposta?\s+pel[oa])\s+(r[eé]u|apelado|parte\s+r[eé]|inss|banco|empresa)', texto_lower, re.IGNORECASE):
            # Defendant appealed and won = Author lost
            return {
                "outcome_normalized": "LOSS",
                "confidence": "HIGH",
                "outcome_phrase": phrase.strip()[:100]
            }
        else:
            # Can't determine who appealed
            return {
                "outcome_normalized": "WIN",  # Default assumption
                "confidence": "MEDIUM",
                "outcome_phrase": phrase.strip()[:100]
            }

    # Check for "negar provimento"
    if re.search(r'negar\s+provimento', texto_lower) or re.search(r'nego\s+provimento', texto_lower) or re.search(r'negaram\s+provimento', texto_lower):
        match = re.search(r'(neg[oa][r]?\s+provimento[^.]{0,100})', texto_lower)
        phrase = match.group(1) if match else "negar provimento"

        # Look for context to determine who appealed
        if re.search(r'(apela[çc][ãa]o|recurso)\s+(do|da|interposta?\s+pel[oa])\s+(autor|apelante|parte\s+autora)', texto_lower, re.IGNORECASE):
            # Author appealed and lost
            return {
                "outcome_normalized": "LOSS",
                "confidence": "HIGH",
                "outcome_phrase": phrase.strip()[:100]
            }
        elif re.search(r'(apela[çc][ãa]o|recurso)\s+(do|da|interposta?\s+pel[oa])\s+(r[eé]u|apelado|parte\s+r[eé]|inss|banco|empresa)', texto_lower, re.IGNORECASE):
            # Defendant appealed and lost = Author won (original decision maintained)
            return {
                "outcome_normalized": "WIN",
                "confidence": "HIGH",
                "outcome_phrase": phrase.strip()[:100]
            }
        else:
            # Can't determine who appealed
            return {
                "outcome_normalized": "LOSS",  # Default assumption
                "confidence": "MEDIUM",
                "outcome_phrase": phrase.strip()[:100]
            }

    # Pattern 3: Condenar/Absolver
    if re.search(r'condena[r]?\s+(o|a)\s+r[eé]u', texto_lower):
        match = re.search(r'(condena[r]?\s+(o|a)\s+r[eé]u[^.]{0,80})', texto_lower)
        phrase = match.group(1) if match else "condenar o réu"
        return {
            "outcome_normalized": "WIN",
            "confidence": "HIGH",
            "outcome_phrase": phrase.strip()[:100]
        }

    if re.search(r'absolv[eo][r]?\s+(o|a)\s+r[eé]u', texto_lower):
        match = re.search(r'(absolv[eo][r]?\s+(o|a)\s+r[eé]u[^.]{0,80})', texto_lower)
        phrase = match.group(1) if match else "absolver o réu"
        return {
            "outcome_normalized": "LOSS",
            "confidence": "HIGH",
            "outcome_phrase": phrase.strip()[:100]
        }

    # Pattern 4: Extinção sem mérito
    if re.search(r'exting[ou][oi]r?\s+(o\s+processo\s+)?sem\s+(resolu[çc][ãa]o\s+(do|de)\s+)?m[eé]rito', texto_lower):
        match = re.search(r'(exting[ou][oi]r?[^.]{0,80})', texto_lower)
        phrase = match.group(1) if match else "extinguir sem mérito"
        return {
            "outcome_normalized": "UNKNOWN",
            "confidence": "HIGH",
            "outcome_phrase": phrase.strip()[:100]
        }

    # Pattern 5: Não conhecer
    if re.search(r'n[ãa]o\s+conhec[eo][r]?\s+(do|da)\s+(recurso|apela[çc][ãa]o)', texto_lower):
        match = re.search(r'(n[ãa]o\s+conhec[eo][r]?[^.]{0,80})', texto_lower)
        phrase = match.group(1) if match else "não conhecer do recurso"
        return {
            "outcome_normalized": "UNKNOWN",
            "confidence": "HIGH",
            "outcome_phrase": phrase.strip()[:100]
        }

    # Pattern 6: Acolher/Rejeitar pedido
    if re.search(r'acolh[eo][r]?\s+(o|os)\s+pedidos?', texto_lower):
        match = re.search(r'(acolh[eo][r]?\s+(o|os)\s+pedidos?[^.]{0,80})', texto_lower)
        phrase = match.group(1) if match else "acolher o pedido"
        return {
            "outcome_normalized": "WIN",
            "confidence": "MEDIUM",
            "outcome_phrase": phrase.strip()[:100]
        }

    if re.search(r'rejeit[oa][r]?\s+(o|os)\s+pedidos?', texto_lower):
        match = re.search(r'(rejeit[oa][r]?\s+(o|os)\s+pedidos?[^.]{0,80})', texto_lower)
        phrase = match.group(1) if match else "rejeitar o pedido"
        return {
            "outcome_normalized": "LOSS",
            "confidence": "MEDIUM",
            "outcome_phrase": phrase.strip()[:100]
        }

    # No clear pattern found
    # Try to find dispositivo section for manual review
    dispositivo_match = re.search(r'(dispos?itivo|ante\s+o\s+exposto|isto\s+posto)[^.]{0,200}', texto_lower)
    if dispositivo_match:
        phrase = dispositivo_match.group(0).strip()[:100]
    else:
        # Get first 100 chars as fallback
        phrase = texto[:100].strip()

    return {
        "outcome_normalized": "UNKNOWN",
        "confidence": "LOW",
        "outcome_phrase": phrase
    }


def label_documents(doc_ids):
    """Label all documents with outcomes."""
    conn = duckdb.connect(DB_PATH)

    labeled_docs = []

    for idx, intimation_id in enumerate(doc_ids, 1):
        try:
            # Query database
            result = conn.execute(
                "SELECT id, numero_processo, texto FROM intimations WHERE id = ?",
                [intimation_id]
            ).fetchone()

            if not result:
                print(f"[{idx}/100] ⚠️  Document {intimation_id} not found in database")
                labeled_docs.append({
                    "intimation_id": intimation_id,
                    "numero_processo": None,
                    "outcome_normalized": "UNKNOWN",
                    "confidence": "LOW",
                    "outcome_phrase": "Document not found in database"
                })
                continue

            doc_id, numero_processo, texto = result

            # Extract outcome
            outcome = extract_outcome(texto, intimation_id)

            # Build document entry
            doc_entry = {
                "intimation_id": intimation_id,
                "numero_processo": numero_processo,
                **outcome
            }

            labeled_docs.append(doc_entry)

            # Progress logging
            outcome_symbol = {
                "WIN": "✓",
                "LOSS": "✗",
                "PARTIAL": "~",
                "UNKNOWN": "?"
            }.get(outcome["outcome_normalized"], "?")

            print(f"[{idx}/100] {outcome_symbol} {intimation_id} → {outcome['outcome_normalized']} ({outcome['confidence']})")

        except Exception as e:
            print(f"[{idx}/100] ❌ Error processing {intimation_id}: {e}")
            labeled_docs.append({
                "intimation_id": intimation_id,
                "numero_processo": None,
                "outcome_normalized": "UNKNOWN",
                "confidence": "LOW",
                "outcome_phrase": f"Error: {str(e)}"
            })

    conn.close()
    return labeled_docs


def calculate_summary(labeled_docs):
    """Calculate summary statistics."""
    total = len(labeled_docs)

    # Confidence counts
    high_conf = sum(1 for doc in labeled_docs if doc["confidence"] == "HIGH")
    medium_conf = sum(1 for doc in labeled_docs if doc["confidence"] == "MEDIUM")
    low_conf = sum(1 for doc in labeled_docs if doc["confidence"] == "LOW")

    # Outcome distribution
    outcome_dist = {
        "WIN": sum(1 for doc in labeled_docs if doc["outcome_normalized"] == "WIN"),
        "LOSS": sum(1 for doc in labeled_docs if doc["outcome_normalized"] == "LOSS"),
        "PARTIAL": sum(1 for doc in labeled_docs if doc["outcome_normalized"] == "PARTIAL"),
        "UNKNOWN": sum(1 for doc in labeled_docs if doc["outcome_normalized"] == "UNKNOWN")
    }

    return {
        "total_labeled": total,
        "high_confidence": high_conf,
        "medium_confidence": medium_conf,
        "low_confidence": low_conf,
        "outcome_distribution": outcome_dist
    }


def main():
    """Main execution flow."""
    print(f"🤖 Agent {AGENT_ID} - Outcome Labeling")
    print(f"📄 Document range: Lines {START_LINE}-{END_LINE}")
    print(f"🎯 Task: Extract outcomes only (WIN/LOSS/PARTIAL)\n")

    # Load document IDs
    doc_ids = load_document_ids()

    # Label documents
    print("\n🏷️  Labeling documents...\n")
    labeled_docs = label_documents(doc_ids)

    # Calculate summary
    summary = calculate_summary(labeled_docs)

    # Build output structure
    output = {
        "agent_id": AGENT_ID,
        "docs_range": f"{START_LINE}-{END_LINE}",
        "total_docs": len(doc_ids),
        "labeling_date": datetime.now().strftime("%Y-%m-%d"),
        "method": "OUTCOME_ONLY",
        "documents": labeled_docs,
        "summary": summary
    }

    # Save to file
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Print summary
    print("\n" + "="*60)
    print("📊 LABELING SUMMARY")
    print("="*60)
    print(f"Total documents: {summary['total_labeled']}")
    print(f"\nConfidence levels:")
    print(f"  HIGH:   {summary['high_confidence']} ({summary['high_confidence']/summary['total_labeled']*100:.1f}%)")
    print(f"  MEDIUM: {summary['medium_confidence']} ({summary['medium_confidence']/summary['total_labeled']*100:.1f}%)")
    print(f"  LOW:    {summary['low_confidence']} ({summary['low_confidence']/summary['total_labeled']*100:.1f}%)")
    print(f"\nOutcome distribution:")
    for outcome, count in summary['outcome_distribution'].items():
        pct = count/summary['total_labeled']*100
        print(f"  {outcome:8s}: {count:3d} ({pct:5.1f}%)")
    print(f"\n✅ Output saved to: {OUTPUT_FILE}")
    print("="*60)


if __name__ == "__main__":
    main()
