#!/usr/bin/env python3
"""
Agent 5 - Rich Ground Truth Labeling
Documents 251-300 (OFFSET 250)
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from html import unescape
import time

def clean_html(text: str) -> str:
    """Remove HTML tags and clean text"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Unescape HTML entities
    text = unescape(text)
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_parties(text: str) -> Dict[str, Any]:
    """Extract party information from text"""
    parties_data = {
        "parties": [],
        "simplified": {
            "author": None,
            "defendant": None,
            "winner": None,
            "loser": None
        }
    }

    # Common patterns for parties
    author_patterns = [
        r'AUTOR[A]?\s*[:\-]\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s\-\.]+?)(?:\s*ADV|</|$|\n)',
        r'APELANTE\s*[:\-]\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s\-\.]+?)(?:\s*ADV|</|$|\n)',
        r'AGRAVANTE\s*[:\-]\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s\-\.]+?)(?:\s*ADV|</|$|\n)',
        r'REQUERENTE\s*[:\-]\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s\-\.]+?)(?:\s*ADV|</|$|\n)',
    ]

    defendant_patterns = [
        r'R[ÉE]U\s*[:\-]\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s\-\.]+?)(?:\s*ADV|</|$|\n)',
        r'APELAD[OA]\s*[:\-]\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s\-\.]+?)(?:\s*ADV|</|$|\n)',
        r'AGRAVAD[OA]\s*[:\-]\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s\-\.]+?)(?:\s*ADV|</|$|\n)',
        r'REQUERID[OA]\s*[:\-]\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s\-\.]+?)(?:\s*ADV|</|$|\n)',
    ]

    author = None
    for pattern in author_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            author = match.group(1).strip().upper()
            break

    defendant = None
    for pattern in defendant_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            defendant = match.group(1).strip().upper()
            break

    parties_data["simplified"]["author"] = author
    parties_data["simplified"]["defendant"] = defendant

    return parties_data

def extract_lawyers(text: str) -> Dict[str, List[Dict]]:
    """Extract lawyer information from text"""
    lawyers_list = []

    # Pattern for lawyers with OAB
    lawyer_pattern = r'ADVOGAD[OA]\(?[AS]?\)?\s*[:\-]\s*([A-ZÀÁÂÃÉÊÍÓÔÕÚÇ][A-ZÀÁÂÃÉÊÍÓÔÕÚÇ\s\-\.]+?)(?:\s*[-\(]?\s*OAB\s*/?\s*([A-Z]{2})\s*(\d+))?'

    matches = re.finditer(lawyer_pattern, text, re.IGNORECASE)
    for match in matches:
        name = match.group(1).strip().upper()
        oab_uf = match.group(2).upper() if match.group(2) else None
        oab_numero = match.group(3) if match.group(3) else None

        lawyer_data = {
            "name": name,
            "oab_numero": oab_numero,
            "oab_uf": oab_uf,
            "representing": None,  # Will be determined later
            "party_name": None,
            "side_won": None
        }
        lawyers_list.append(lawyer_data)

    # Check for public defenders
    if re.search(r'PROCURADORIA FEDERAL', text, re.IGNORECASE):
        lawyers_list.append({
            "name": "PROCURADORIA FEDERAL",
            "oab_numero": None,
            "oab_uf": None,
            "representing": "REU",
            "party_name": None,
            "side_won": None,
            "is_public_defender": True
        })

    if re.search(r'DEFENSORIA P[UÚ]BLICA', text, re.IGNORECASE):
        lawyers_list.append({
            "name": "DEFENSORIA PUBLICA",
            "oab_numero": None,
            "oab_uf": None,
            "representing": "AUTOR",
            "party_name": None,
            "side_won": None,
            "is_public_defender": True
        })

    return {"lawyers": lawyers_list}

def analyze_outcome(text: str) -> Dict[str, Any]:
    """Analyze decision outcome"""
    text_upper = text.upper()

    outcome_data = {
        "primary_outcome": None,
        "outcome_normalized": None,
        "confidence": "LOW",
        "outcome_percentage": None,
        "outcome_reasoning": "",
        "author_perspective": {
            "outcome": None,
            "got_what_requested": None
        },
        "defendant_perspective": {
            "outcome": None,
            "succeeded_in_defense": None
        }
    }

    # Check for clear WIN patterns
    if re.search(r'JULGO\s+PROCEDENTE', text_upper):
        outcome_data["primary_outcome"] = "PROCEDENTE"
        outcome_data["outcome_normalized"] = "WIN"
        outcome_data["confidence"] = "HIGH"
        outcome_data["outcome_percentage"] = 100
        outcome_data["author_perspective"]["outcome"] = "WIN"
        outcome_data["author_perspective"]["got_what_requested"] = True
        outcome_data["defendant_perspective"]["outcome"] = "LOSS"
        outcome_data["defendant_perspective"]["succeeded_in_defense"] = False
        outcome_data["outcome_reasoning"] = "Decision explicitly states 'JULGO PROCEDENTE'"

    elif re.search(r'JULGO\s+PARCIALMENTE\s+PROCEDENTE', text_upper):
        outcome_data["primary_outcome"] = "PARCIALMENTE_PROCEDENTE"
        outcome_data["outcome_normalized"] = "PARTIAL"
        outcome_data["confidence"] = "HIGH"
        outcome_data["outcome_percentage"] = 50
        outcome_data["author_perspective"]["outcome"] = "PARTIAL"
        outcome_data["author_perspective"]["got_what_requested"] = False
        outcome_data["defendant_perspective"]["outcome"] = "PARTIAL"
        outcome_data["defendant_perspective"]["succeeded_in_defense"] = False
        outcome_data["outcome_reasoning"] = "Decision states 'JULGO PARCIALMENTE PROCEDENTE'"

    elif re.search(r'JULGO\s+IMPROCEDENTE', text_upper):
        outcome_data["primary_outcome"] = "IMPROCEDENTE"
        outcome_data["outcome_normalized"] = "LOSS"
        outcome_data["confidence"] = "HIGH"
        outcome_data["outcome_percentage"] = 0
        outcome_data["author_perspective"]["outcome"] = "LOSS"
        outcome_data["author_perspective"]["got_what_requested"] = False
        outcome_data["defendant_perspective"]["outcome"] = "WIN"
        outcome_data["defendant_perspective"]["succeeded_in_defense"] = True
        outcome_data["outcome_reasoning"] = "Decision states 'JULGO IMPROCEDENTE'"

    elif re.search(r'DAR?\s+PROVIMENTO', text_upper):
        outcome_data["primary_outcome"] = "PROVIDO"
        outcome_data["outcome_normalized"] = "WIN"
        outcome_data["confidence"] = "MEDIUM"
        outcome_data["outcome_percentage"] = 100
        outcome_data["outcome_reasoning"] = "Appeal granted - 'DAR PROVIMENTO'"

    elif re.search(r'NEGAR?\s+PROVIMENTO', text_upper):
        outcome_data["primary_outcome"] = "DESPROVIDO"
        outcome_data["outcome_normalized"] = "LOSS"
        outcome_data["confidence"] = "MEDIUM"
        outcome_data["outcome_percentage"] = 0
        outcome_data["outcome_reasoning"] = "Appeal denied - 'NEGAR PROVIMENTO'"

    elif re.search(r'N[ÃA]O\s+CONHEC', text_upper):
        outcome_data["primary_outcome"] = "NAO_CONHECIDO"
        outcome_data["outcome_normalized"] = "UNKNOWN"
        outcome_data["confidence"] = "MEDIUM"
        outcome_data["outcome_reasoning"] = "Appeal not examined on merits"

    elif re.search(r'EXTIN', text_upper):
        outcome_data["primary_outcome"] = "EXTINTO"
        outcome_data["outcome_normalized"] = "UNKNOWN"
        outcome_data["confidence"] = "MEDIUM"
        outcome_data["outcome_reasoning"] = "Case terminated without merit examination"

    return outcome_data

def classify_decision(text: str) -> Dict[str, str]:
    """Classify decision type"""
    text_upper = text.upper()

    classification = {
        "decision_type": None,
        "instance": None,
        "decision_nature": None
    }

    if re.search(r'ACÓRDÃO|ACORDAO', text_upper):
        classification["decision_type"] = "ACORDAO"
        classification["instance"] = "SEGUNDA_INSTANCIA"
    elif re.search(r'SENTENÇA|SENTENCA', text_upper):
        classification["decision_type"] = "SENTENCA"
        classification["instance"] = "PRIMEIRA_INSTANCIA"
    elif re.search(r'DECISÃO MONOCRÁTICA|DECISAO MONOCRATICA', text_upper):
        classification["decision_type"] = "DECISAO_MONOCRATICA"
        classification["instance"] = "SEGUNDA_INSTANCIA"
    elif re.search(r'DESPACHO|ATO ORDINATÓRIO|ATO ORDINATORIO', text_upper):
        classification["decision_type"] = "DESPACHO"
        classification["decision_nature"] = "PROCESSUAL"

    # Determine nature
    if classification["decision_nature"] is None:
        if re.search(r'JULGO|PROCEDENTE|IMPROCEDENTE', text_upper):
            classification["decision_nature"] = "MERITO_FINAL"
        elif re.search(r'LIMINAR', text_upper):
            classification["decision_nature"] = "LIMINAR"

    return classification

def extract_procedural_details(text: str) -> Dict[str, Any]:
    """Extract procedural information"""
    text_upper = text.upper()

    procedural = {
        "appeal_type": None,
        "who_appealed": None,
        "appeal_outcome": None,
        "decision_changed": None
    }

    if re.search(r'APELAÇÃO|APELACAO', text_upper):
        procedural["appeal_type"] = "APELACAO"
    elif re.search(r'AGRAVO', text_upper):
        procedural["appeal_type"] = "AGRAVO"
    elif re.search(r'RECURSO ESPECIAL', text_upper):
        procedural["appeal_type"] = "RECURSO_ESPECIAL"

    if re.search(r'APELANTE', text_upper):
        procedural["who_appealed"] = "AUTOR"
    elif re.search(r'APELADO', text_upper) and procedural["appeal_type"]:
        # If we found APELADO, the other party appealed
        procedural["who_appealed"] = "REU"

    if re.search(r'PROVIDO|DAR PROVIMENTO', text_upper) and not re.search(r'DESPROVIDO|NEGAR', text_upper):
        procedural["appeal_outcome"] = "PROVIDO"
        procedural["decision_changed"] = True
    elif re.search(r'DESPROVIDO|NEGAR PROVIMENTO', text_upper):
        procedural["appeal_outcome"] = "DESPROVIDO"
        procedural["decision_changed"] = False
    elif re.search(r'PARCIALMENTE PROVIDO', text_upper):
        procedural["appeal_outcome"] = "PARCIALMENTE_PROVIDO"
        procedural["decision_changed"] = True

    return procedural

def assess_quality(text: str, outcome: Dict, parties: Dict) -> Dict[str, Any]:
    """Assess quality of the document and labeling"""
    clean_text = clean_html(text)

    quality = {
        "text_length": len(clean_text),
        "text_quality": "MEDIUM",
        "contains_full_decision": False,
        "contains_outcome_phrase": False,
        "ambiguous_outcome": False,
        "missing_information": [],
        "labeling_difficulty": "MEDIUM",
        "labeler_notes": ""
    }

    # Check text quality
    if len(clean_text) > 2000:
        quality["text_quality"] = "HIGH"
        quality["contains_full_decision"] = True
    elif len(clean_text) < 500:
        quality["text_quality"] = "LOW"

    # Check for outcome phrases
    if re.search(r'JULGO|PROVIMENTO|PROCEDENTE', clean_text.upper()):
        quality["contains_outcome_phrase"] = True

    # Check for ambiguous outcome
    if outcome["confidence"] == "LOW":
        quality["ambiguous_outcome"] = True

    # Check missing information
    if not parties["simplified"]["author"]:
        quality["missing_information"].append("author")
    if not parties["simplified"]["defendant"]:
        quality["missing_information"].append("defendant")
    if not outcome["primary_outcome"]:
        quality["missing_information"].append("outcome")

    # Determine difficulty
    if quality["missing_information"] or quality["ambiguous_outcome"]:
        quality["labeling_difficulty"] = "HARD"
    elif quality["contains_outcome_phrase"] and parties["simplified"]["author"]:
        quality["labeling_difficulty"] = "EASY"

    return quality

def label_document(doc: Dict, doc_num: int, start_time: float) -> Dict[str, Any]:
    """Label a single document with rich structured data"""
    text = doc["texto"]
    clean_text = clean_html(text)

    # Extract all fields
    outcome = analyze_outcome(clean_text)
    parties = extract_parties(clean_text)
    lawyers = extract_lawyers(clean_text)
    classification = classify_decision(clean_text)
    procedural = extract_procedural_details(clean_text)
    quality = assess_quality(text, outcome, parties)

    # Determine winners/losers
    if outcome["author_perspective"]["outcome"] == "WIN":
        parties["simplified"]["winner"] = parties["simplified"]["author"]
        parties["simplified"]["loser"] = parties["simplified"]["defendant"]
    elif outcome["author_perspective"]["outcome"] == "LOSS":
        parties["simplified"]["winner"] = parties["simplified"]["defendant"]
        parties["simplified"]["loser"] = parties["simplified"]["author"]

    # Update lawyers with side_won
    for lawyer in lawyers["lawyers"]:
        if lawyer.get("representing") == "AUTOR":
            lawyer["side_won"] = outcome["author_perspective"]["outcome"] == "WIN"
            lawyer["party_name"] = parties["simplified"]["author"]
        elif lawyer.get("representing") == "REU":
            lawyer["side_won"] = outcome["defendant_perspective"]["outcome"] == "WIN"
            lawyer["party_name"] = parties["simplified"]["defendant"]

    # Add labeling time
    quality["labeling_time_seconds"] = int(time.time() - start_time)

    # Construct labeled document
    labeled = {
        "doc_id": doc_num,
        "intimation_id": doc["intimation_id"],
        "numero_processo": doc["numero_processo"],
        "data_disponibilizacao": doc["data_disponibilizacao"],
        "tribunal": doc["sigla_tribunal"],
        "orgao": doc["nome_orgao"],

        "decision_classification": classification,
        "outcome": outcome,
        "parties": parties,
        "lawyers": lawyers,
        "procedural": procedural,
        "quality": quality
    }

    return labeled

def main():
    """Main labeling function"""
    print("Agent 5 - Rich Ground Truth Labeling")
    print("=" * 60)
    print("Documents: 251-300 (OFFSET 250)")
    print()

    # Load documents
    with open('/tmp/agent_5_docs.json', 'r', encoding='utf-8') as f:
        documents = json.load(f)

    print(f"Loaded {len(documents)} documents")
    print(f"First ID: {documents[0]['intimation_id']}")
    print(f"Last ID: {documents[-1]['intimation_id']}")
    print()

    # Label each document
    labeled_docs = []
    start_overall = time.time()

    for i, doc in enumerate(documents, start=251):
        print(f"Labeling document {i}/300... ({doc['intimation_id']})", end='', flush=True)
        start_doc = time.time()

        labeled = label_document(doc, i, start_doc)
        labeled_docs.append(labeled)

        elapsed = time.time() - start_doc
        print(f" ✓ ({elapsed:.1f}s)")

        # Save checkpoint every 10 documents
        if (i - 250) % 10 == 0:
            checkpoint_file = f'/tmp/agent_5_checkpoint_{i}.json'
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(labeled_docs, f, ensure_ascii=False, indent=2)
            print(f"  Checkpoint saved: {checkpoint_file}")

    # Calculate summary statistics
    total_time = time.time() - start_overall
    high_conf = sum(1 for d in labeled_docs if d["outcome"]["confidence"] == "HIGH")
    medium_conf = sum(1 for d in labeled_docs if d["outcome"]["confidence"] == "MEDIUM")
    low_conf = sum(1 for d in labeled_docs if d["outcome"]["confidence"] == "LOW")
    ambiguous = sum(1 for d in labeled_docs if d["quality"]["ambiguous_outcome"])

    # Prepare final output
    output = {
        "agent_id": 5,
        "docs_range": "251-300",
        "total_docs": len(labeled_docs),
        "labeling_date": datetime.now().strftime("%Y-%m-%d"),
        "documents": labeled_docs,
        "summary": {
            "total_labeled": len(labeled_docs),
            "high_confidence": high_conf,
            "medium_confidence": medium_conf,
            "low_confidence": low_conf,
            "ambiguous_outcomes": ambiguous,
            "average_time_seconds": int(total_time / len(labeled_docs))
        }
    }

    # Save final output
    output_file = '/home/user/causaganha/data/ground_truth_rich_agent_5.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print("LABELING COMPLETE")
    print("=" * 60)
    print(f"Total documents labeled: {len(labeled_docs)}")
    print(f"High confidence: {high_conf}")
    print(f"Medium confidence: {medium_conf}")
    print(f"Low confidence: {low_conf}")
    print(f"Ambiguous outcomes: {ambiguous}")
    print(f"Total time: {total_time:.1f}s")
    print(f"Average time per doc: {total_time/len(labeled_docs):.1f}s")
    print()
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    main()
