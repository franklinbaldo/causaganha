#!/usr/bin/env python3
"""
Agent 5 - IMPROVED Rich Ground Truth Labeling
Handles both procedural orders and merit decisions properly
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from html import unescape
import time

def clean_html(text: str) -> str:
    """Remove HTML tags and clean text"""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
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

    # Patterns for parties - more robust
    author_patterns = [
        r'(?:AUTOR|REQUERENTE|APELANTE|AGRAVANTE|RECORRENTE)\s*(?:\(A\))?\s*[:\-]\s*([A-ZÀ-Ü][A-ZÀ-Ü\s\-\.&/]+?)(?:\s+(?:CPF|CNPJ|ADVOGADO|ADV\.|</)|$)',
    ]

    defendant_patterns = [
        r'(?:R[ÉE]U|REQUERIDO|APELADO|AGRAVADO|RECORRIDO)\s*(?:\(A\))?\s*[:\-]\s*([A-ZÀ-Ü][A-ZÀ-Ü\s\-\.&/]+?)(?:\s+(?:CPF|CNPJ|ADVOGADO|ADV\.|</)|$)',
    ]

    author = None
    for pattern in author_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            author = match.group(1).strip().upper()
            # Clean up
            author = re.sub(r'\s+', ' ', author)
            break

    defendant = None
    for pattern in defendant_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            defendant = match.group(1).strip().upper()
            defendant = re.sub(r'\s+', ' ', defendant)
            break

    parties_data["simplified"]["author"] = author
    parties_data["simplified"]["defendant"] = defendant

    # Build party objects if found
    if author:
        is_inss = 'INSS' in author or 'INSTITUTO NACIONAL' in author
        is_gov = is_inss or 'UNIAO' in author or 'FAZENDA' in author
        parties_data["parties"].append({
            "role": "AUTOR",
            "name": author,
            "normalized_name": author,
            "party_type": "AUTARQUIA_FEDERAL" if is_inss else "PESSOA_FISICA",
            "is_winner": None,
            "is_government": is_gov,
            "is_inss": is_inss
        })

    if defendant:
        is_inss = 'INSS' in defendant or 'INSTITUTO NACIONAL' in defendant
        is_gov = is_inss or 'UNIAO' in defendant or 'FAZENDA' in defendant
        parties_data["parties"].append({
            "role": "REU",
            "name": defendant,
            "normalized_name": defendant,
            "party_type": "AUTARQUIA_FEDERAL" if is_inss else "PESSOA_FISICA",
            "is_winner": None,
            "is_government": is_gov,
            "is_inss": is_inss
        })

    return parties_data

def extract_lawyers(text: str) -> Dict[str, List[Dict]]:
    """Extract lawyer information from text"""
    lawyers_list = []

    # More robust pattern for lawyers with OAB
    lawyer_pattern = r'ADVOGAD[OA](?:\(?[AS]?\)?)?[:\s]+([A-ZÀ-Ü][A-ZÀ-Ü\s\-\.]+?)(?:\s*[-\(]?\s*OAB[:/\s]*([A-Z]{2})\s*(\d+)\)?)?(?:\s|<|$)'

    matches = re.finditer(lawyer_pattern, text, re.IGNORECASE | re.MULTILINE)
    seen_lawyers = set()

    for match in matches:
        name = match.group(1).strip().upper()
        name = re.sub(r'\s+', ' ', name)
        oab_uf = match.group(2).upper() if match.group(2) else None
        oab_numero = match.group(3) if match.group(3) else None

        # Create unique key to avoid duplicates
        lawyer_key = f"{name}_{oab_uf}_{oab_numero}"
        if lawyer_key in seen_lawyers:
            continue
        seen_lawyers.add(lawyer_key)

        lawyer_data = {
            "name": name,
            "oab_numero": oab_numero,
            "oab_uf": oab_uf,
            "oab_full": f"OAB/{oab_uf} {oab_numero}" if oab_uf and oab_numero else None,
            "representing": None,
            "party_name": None,
            "side_won": None
        }
        lawyers_list.append(lawyer_data)

    # Check for public defenders/prosecutors
    if re.search(r'PROCURADORIA\s+FEDERAL', text, re.IGNORECASE):
        if not any(l["name"] == "PROCURADORIA FEDERAL" for l in lawyers_list):
            lawyers_list.append({
                "name": "PROCURADORIA FEDERAL",
                "oab_numero": None,
                "oab_uf": None,
                "oab_full": None,
                "representing": "REU",
                "party_name": "INSS",
                "side_won": None,
                "is_public_defender": True
            })

    if re.search(r'DEFENSORIA\s+P[ÚU]BLICA', text, re.IGNORECASE):
        if not any(l["name"] == "DEFENSORIA PUBLICA" for l in lawyers_list):
            lawyers_list.append({
                "name": "DEFENSORIA PUBLICA",
                "oab_numero": None,
                "oab_uf": None,
                "oab_full": None,
                "representing": "AUTOR",
                "party_name": None,
                "side_won": None,
                "is_public_defender": True
            })

    return {"lawyers": lawyers_list}

def analyze_outcome(text: str, is_procedural: bool) -> Dict[str, Any]:
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

    # If procedural document, mark as no merit outcome
    if is_procedural:
        outcome_data["primary_outcome"] = "PROCEDURAL_ORDER"
        outcome_data["outcome_normalized"] = "UNKNOWN"
        outcome_data["confidence"] = "HIGH"
        outcome_data["outcome_reasoning"] = "Procedural order - no merit decision"
        return outcome_data

    # Check for clear merit outcomes
    if re.search(r'JULGO\s+PROCEDENTE', text_upper):
        outcome_data["primary_outcome"] = "PROCEDENTE"
        outcome_data["outcome_normalized"] = "WIN"
        outcome_data["confidence"] = "HIGH"
        outcome_data["outcome_percentage"] = 100
        outcome_data["author_perspective"]["outcome"] = "WIN"
        outcome_data["author_perspective"]["got_what_requested"] = True
        outcome_data["defendant_perspective"]["outcome"] = "LOSS"
        outcome_data["defendant_perspective"]["succeeded_in_defense"] = False

        # Find exact phrase
        match = re.search(r'JULGO\s+PROCEDENTE[^.]{0,100}', text_upper)
        if match:
            outcome_data["outcome_reasoning"] = f"'{match.group(0)[:80]}...'"
        else:
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

    elif re.search(r'(?:DAR?|DEI)\s+PROVIMENTO', text_upper) and not re.search(r'NEGAR', text_upper):
        outcome_data["primary_outcome"] = "PROVIDO"
        outcome_data["outcome_normalized"] = "WIN"
        outcome_data["confidence"] = "HIGH"
        outcome_data["outcome_percentage"] = 100
        outcome_data["outcome_reasoning"] = "Appeal granted - 'DAR PROVIMENTO'"

    elif re.search(r'(?:NEGAR?|NEGUEI)\s+PROVIMENTO', text_upper):
        outcome_data["primary_outcome"] = "DESPROVIDO"
        outcome_data["outcome_normalized"] = "LOSS"
        outcome_data["confidence"] = "HIGH"
        outcome_data["outcome_percentage"] = 0
        outcome_data["outcome_reasoning"] = "Appeal denied - 'NEGAR PROVIMENTO'"

    elif re.search(r'PARCIALMENTE\s+PROVIDO', text_upper):
        outcome_data["primary_outcome"] = "PARCIALMENTE_PROVIDO"
        outcome_data["outcome_normalized"] = "PARTIAL"
        outcome_data["confidence"] = "HIGH"
        outcome_data["outcome_percentage"] = 50
        outcome_data["outcome_reasoning"] = "Appeal partially granted"

    elif re.search(r'N[ÃA]O\s+CONHEC', text_upper):
        outcome_data["primary_outcome"] = "NAO_CONHECIDO"
        outcome_data["outcome_normalized"] = "UNKNOWN"
        outcome_data["confidence"] = "HIGH"
        outcome_data["outcome_reasoning"] = "Appeal not examined on merits"

    elif re.search(r'EXTIN', text_upper):
        outcome_data["primary_outcome"] = "EXTINTO"
        outcome_data["outcome_normalized"] = "UNKNOWN"
        outcome_data["confidence"] = "MEDIUM"
        outcome_data["outcome_reasoning"] = "Case terminated without merit examination"

    return outcome_data

def classify_decision(text: str) -> tuple[Dict[str, str], bool]:
    """Classify decision type and return if it's procedural"""
    text_upper = text.upper()

    classification = {
        "decision_type": None,
        "instance": None,
        "decision_nature": None
    }

    is_procedural = False

    # Check for procedural orders first
    if re.search(r'ATO\s+ORDINAT[OÓ]RIO', text_upper):
        classification["decision_type"] = "ATO_ORDINATORIO"
        classification["decision_nature"] = "PROCESSUAL"
        is_procedural = True
    elif re.search(r'DESPACHO', text_upper):
        classification["decision_type"] = "DESPACHO"
        classification["decision_nature"] = "PROCESSUAL"
        is_procedural = True
    # Merit decisions
    elif re.search(r'ACÓRDÃO|ACORDAO', text_upper):
        classification["decision_type"] = "ACORDAO"
        classification["instance"] = "SEGUNDA_INSTANCIA"
    elif re.search(r'SENTENÇA|SENTENCA', text_upper):
        classification["decision_type"] = "SENTENCA"
        classification["instance"] = "PRIMEIRA_INSTANCIA"
    elif re.search(r'DECIS[ÃA]O\s+MONOCR[ÁA]TICA', text_upper):
        classification["decision_type"] = "DECISAO_MONOCRATICA"
        classification["instance"] = "SEGUNDA_INSTANCIA"
    else:
        # Default to procedural if uncertain
        classification["decision_type"] = "DOCUMENT_INCERTO"
        classification["decision_nature"] = "PROCESSUAL"
        is_procedural = True

    # Determine nature for merit decisions
    if not is_procedural and classification["decision_nature"] is None:
        if re.search(r'JULGO|PROCEDENTE|IMPROCEDENTE', text_upper):
            classification["decision_nature"] = "MERITO_FINAL"
        elif re.search(r'LIMINAR', text_upper):
            classification["decision_nature"] = "LIMINAR"
        else:
            classification["decision_nature"] = "PROCESSUAL"

    return classification, is_procedural

def extract_procedural_details(text: str) -> Dict[str, Any]:
    """Extract procedural information"""
    text_upper = text.upper()

    procedural = {
        "appeal_type": None,
        "who_appealed": None,
        "appeal_outcome": None,
        "decision_changed": None
    }

    if re.search(r'APELA[ÇC][ÃA]O', text_upper):
        procedural["appeal_type"] = "APELACAO"
    elif re.search(r'AGRAVO', text_upper):
        procedural["appeal_type"] = "AGRAVO"
    elif re.search(r'RECURSO\s+ESPECIAL', text_upper):
        procedural["appeal_type"] = "RECURSO_ESPECIAL"

    if re.search(r'APELANTE', text_upper):
        procedural["who_appealed"] = "AUTOR"

    if re.search(r'(?:DAR?|DEI)\s+PROVIMENTO', text_upper) and not re.search(r'NEGAR', text_upper):
        procedural["appeal_outcome"] = "PROVIDO"
        procedural["decision_changed"] = True
    elif re.search(r'(?:NEGAR?|NEGUEI)\s+PROVIMENTO', text_upper):
        procedural["appeal_outcome"] = "DESPROVIDO"
        procedural["decision_changed"] = False
    elif re.search(r'PARCIALMENTE\s+PROVIDO', text_upper):
        procedural["appeal_outcome"] = "PARCIALMENTE_PROVIDO"
        procedural["decision_changed"] = True

    return procedural

def assess_quality(text: str, outcome: Dict, parties: Dict, is_procedural: bool) -> Dict[str, Any]:
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

    # For procedural orders
    if is_procedural:
        quality["contains_outcome_phrase"] = False
        quality["ambiguous_outcome"] = False
        quality["labeling_difficulty"] = "EASY"
        quality["labeler_notes"] = "Procedural order - no merit decision expected"
        if parties["simplified"]["author"]:
            quality["text_quality"] = "HIGH"
    else:
        # For merit decisions
        if re.search(r'JULGO|PROVIMENTO|PROCEDENTE', clean_text.upper()):
            quality["contains_outcome_phrase"] = True

        if outcome["confidence"] == "LOW":
            quality["ambiguous_outcome"] = True

        # Check missing information
        if not parties["simplified"]["author"]:
            quality["missing_information"].append("author")
        if not parties["simplified"]["defendant"]:
            quality["missing_information"].append("defendant")
        if not outcome["primary_outcome"] or outcome["primary_outcome"] == "PROCEDURAL_ORDER":
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

    # Classify decision first to determine if procedural
    classification, is_procedural = classify_decision(clean_text)

    # Extract all fields
    parties = extract_parties(clean_text)
    lawyers = extract_lawyers(clean_text)
    outcome = analyze_outcome(clean_text, is_procedural)
    procedural = extract_procedural_details(clean_text)
    quality = assess_quality(text, outcome, parties, is_procedural)

    # Determine winners/losers (only for merit decisions)
    if not is_procedural:
        if outcome["author_perspective"]["outcome"] == "WIN":
            parties["simplified"]["winner"] = parties["simplified"]["author"]
            parties["simplified"]["loser"] = parties["simplified"]["defendant"]
        elif outcome["author_perspective"]["outcome"] == "LOSS":
            parties["simplified"]["winner"] = parties["simplified"]["defendant"]
            parties["simplified"]["loser"] = parties["simplified"]["author"]

        # Update party objects with winner info
        for party in parties["parties"]:
            if party["role"] == "AUTOR":
                party["is_winner"] = outcome["author_perspective"]["outcome"] == "WIN"
            elif party["role"] == "REU":
                party["is_winner"] = outcome["defendant_perspective"]["outcome"] == "WIN"

    # Update lawyers with side_won and representing
    for i, lawyer in enumerate(lawyers["lawyers"]):
        # Determine which side lawyer represents (if not already set)
        if lawyer.get("representing") is None:
            # Simple heuristic: first lawyer is for author
            if i == 0 and parties["simplified"]["author"]:
                lawyer["representing"] = "AUTOR"
                lawyer["party_name"] = parties["simplified"]["author"]
            elif parties["simplified"]["defendant"]:
                lawyer["representing"] = "REU"
                lawyer["party_name"] = parties["simplified"]["defendant"]

        # Set side_won
        if not is_procedural and lawyer.get("representing"):
            if lawyer["representing"] == "AUTOR":
                lawyer["side_won"] = outcome["author_perspective"]["outcome"] == "WIN"
            elif lawyer["representing"] == "REU":
                lawyer["side_won"] = outcome["defendant_perspective"]["outcome"] == "WIN"

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
    print("Agent 5 - IMPROVED Rich Ground Truth Labeling")
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
        # Show decision type for context
        dtype = labeled["decision_classification"]["decision_type"]
        outcome_type = labeled["outcome"]["primary_outcome"]
        print(f" ✓ [{dtype}] [{outcome_type}] ({elapsed:.2f}s)")

        # Save checkpoint every 10 documents
        if (i - 250) % 10 == 0:
            checkpoint_file = f'/tmp/agent_5_improved_checkpoint_{i}.json'
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(labeled_docs, f, ensure_ascii=False, indent=2)
            print(f"  ✓ Checkpoint saved")

    # Calculate summary statistics
    total_time = time.time() - start_overall
    high_conf = sum(1 for d in labeled_docs if d["outcome"]["confidence"] == "HIGH")
    medium_conf = sum(1 for d in labeled_docs if d["outcome"]["confidence"] == "MEDIUM")
    low_conf = sum(1 for d in labeled_docs if d["outcome"]["confidence"] == "LOW")
    ambiguous = sum(1 for d in labeled_docs if d["quality"]["ambiguous_outcome"])

    # Document type breakdown
    doc_types = {}
    for d in labeled_docs:
        dtype = d["decision_classification"]["decision_type"]
        doc_types[dtype] = doc_types.get(dtype, 0) + 1

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
            "average_time_seconds": int(total_time / len(labeled_docs)),
            "document_types": doc_types
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
    print()
    print("Document types:")
    for dtype, count in sorted(doc_types.items()):
        print(f"  {dtype}: {count}")
    print()
    print(f"Total time: {total_time:.1f}s")
    print(f"Average time per doc: {total_time/len(labeled_docs):.1f}s")
    print()
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    main()
