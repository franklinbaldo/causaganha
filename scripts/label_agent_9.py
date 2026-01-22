#!/usr/bin/env python3
"""
Agent 9: Ground Truth Labeling
Documents 451-500 (intimation_id OFFSET 450)
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from html import unescape
from html.parser import HTMLParser

class HTMLTextExtractor(HTMLParser):
    """Extract text content from HTML."""
    def __init__(self):
        super().__init__()
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def get_text(self):
        return ' '.join(self.text)

def clean_html(html_text: str) -> str:
    """Remove HTML tags and decode entities."""
    # First unescape HTML entities
    text = unescape(html_text)

    # Extract text using parser
    parser = HTMLTextExtractor()
    try:
        parser.feed(text)
        text = parser.get_text()
    except:
        # Fallback to simple regex if parser fails
        text = re.sub(r'<[^>]+>', ' ', text)

    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_parties(texto: str) -> Dict[str, Any]:
    """Extract party information from decision text."""
    parties_data = {
        "parties": [],
        "simplified": {
            "author": None,
            "defendant": None,
            "winner": None,
            "loser": None
        }
    }

    # Common patterns for party identification - more flexible
    author_patterns = [
        r'(?:APELANTE|AUTOR|REQUERENTE|RECORRENTE)\s*:\s*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][\wÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s\.\-]+?)(?=\s*(?:ADVOGADO|APELADO|RÉU|REQUERIDO|$))',
        r'(?:Apelante|Autor|Requerente|Recorrente)\s*:\s*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][\wÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s\.\-]+?)(?=\s*(?:Advogado|Apelado|Réu|Requerido))',
    ]

    defendant_patterns = [
        r'(?:APELADO|RÉU|REU|REQUERIDO|RECORRIDO)\s*:\s*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][\wÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s\.\-]+?)(?=\s*(?:ADVOGADO|APELANTE|AUTOR|$))',
        r'(?:Apelado|Réu|Requerido|Recorrido)\s*:\s*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][\wÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s\.\-]+?)(?=\s*(?:Advogado|Apelante|Autor))',
    ]

    # Try to find author
    author = None
    for pattern in author_patterns:
        match = re.search(pattern, texto, re.IGNORECASE | re.DOTALL)
        if match:
            author = match.group(1).strip()
            # Clean up
            author = re.sub(r'\s+', ' ', author)
            author = author.upper()
            break

    # Try to find defendant
    defendant = None
    for pattern in defendant_patterns:
        match = re.search(pattern, texto, re.IGNORECASE | re.DOTALL)
        if match:
            defendant = match.group(1).strip()
            # Clean up
            defendant = re.sub(r'\s+', ' ', defendant)
            defendant = defendant.upper()
            break

    # Detect INSS
    is_inss_defendant = False
    if defendant and 'INSS' in defendant.upper():
        is_inss_defendant = True

    parties_data["simplified"]["author"] = author
    parties_data["simplified"]["defendant"] = defendant

    return parties_data, is_inss_defendant

def extract_lawyers(texto: str) -> List[Dict[str, Any]]:
    """Extract lawyer information from decision text."""
    lawyers = []
    seen = set()  # Track unique lawyers

    # Patterns for lawyer extraction - more robust
    lawyer_pattern = r'ADVOGAD[OA](?:\(A\))?\s*:\s*([A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ][\wÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s\.\-]+?)\s*\(OAB\s+([A-Z]{2})\s*(\d+)\)'

    # Check for public defenders
    if re.search(r'Procuradoria\s+Federal', texto, re.IGNORECASE):
        lawyers.append({
            "name": "PROCURADORIA FEDERAL",
            "oab_numero": None,
            "oab_uf": None,
            "representing": "REU",
            "party_name": None,
            "side_won": None,
            "is_public_defender": True
        })
        seen.add("PROCURADORIA FEDERAL")

    if re.search(r'Defensoria\s+P[úu]blica', texto, re.IGNORECASE):
        lawyers.append({
            "name": "DEFENSORIA PUBLICA",
            "oab_numero": None,
            "oab_uf": None,
            "representing": "AUTOR",
            "party_name": None,
            "side_won": None,
            "is_public_defender": True
        })
        seen.add("DEFENSORIA PUBLICA")

    # Extract private lawyers with OAB
    matches = re.finditer(lawyer_pattern, texto.upper(), re.MULTILINE)
    for match in matches:
        name = match.group(1).strip()
        name = re.sub(r'\s+', ' ', name)  # Clean whitespace
        oab_uf = match.group(2)
        oab_numero = match.group(3)

        # Create unique key
        key = f"{name}_{oab_uf}_{oab_numero}"
        if key not in seen and name and not name.startswith('OAB'):
            lawyers.append({
                "name": name,
                "oab_numero": oab_numero,
                "oab_uf": oab_uf,
                "representing": None,  # Will be determined later
                "party_name": None,
                "side_won": None
            })
            seen.add(key)

    return lawyers

def extract_outcome(texto: str) -> Dict[str, Any]:
    """Extract outcome information from decision text."""
    texto_upper = texto.upper()

    # Initialize outcome data
    outcome_data = {
        "primary_outcome": "UNKNOWN",
        "outcome_detail": None,
        "outcome_normalized": "UNKNOWN",
        "confidence": "LOW",
        "outcome_percentage": None,
        "outcome_reasoning": "",
        "author_perspective": {
            "outcome": "UNKNOWN",
            "got_what_requested": None
        },
        "defendant_perspective": {
            "outcome": "UNKNOWN",
            "succeeded_in_defense": None
        }
    }

    # WIN patterns (PROCEDENTE for author)
    if re.search(r'JULG[OAR]+\s+PROCEDENTE(?!\s+EM\s+PARTE)', texto_upper):
        outcome_data["primary_outcome"] = "PROCEDENTE"
        outcome_data["outcome_normalized"] = "WIN"
        outcome_data["confidence"] = "HIGH"
        outcome_data["outcome_percentage"] = 100
        outcome_data["author_perspective"]["outcome"] = "WIN"
        outcome_data["author_perspective"]["got_what_requested"] = True
        outcome_data["defendant_perspective"]["outcome"] = "LOSS"
        outcome_data["defendant_perspective"]["succeeded_in_defense"] = False

        match = re.search(r'.{0,100}JULG[OAR]+\s+PROCEDENTE.{0,100}', texto_upper)
        if match:
            outcome_data["outcome_reasoning"] = match.group(0)

    # PARTIAL WIN patterns
    elif re.search(r'(?:JULG[OAR]+\s+)?PARCIALMENTE\s+PROCEDENTE', texto_upper):
        outcome_data["primary_outcome"] = "PARCIALMENTE_PROCEDENTE"
        outcome_data["outcome_normalized"] = "PARTIAL"
        outcome_data["confidence"] = "MEDIUM"
        outcome_data["outcome_percentage"] = 50
        outcome_data["author_perspective"]["outcome"] = "PARTIAL"
        outcome_data["defendant_perspective"]["outcome"] = "PARTIAL"

        match = re.search(r'.{0,100}PARCIALMENTE\s+PROCEDENTE.{0,100}', texto_upper)
        if match:
            outcome_data["outcome_reasoning"] = match.group(0)

    # LOSS patterns (IMPROCEDENTE for author)
    elif re.search(r'JULG[OAR]+\s+IMPROCEDENTE', texto_upper):
        outcome_data["primary_outcome"] = "IMPROCEDENTE"
        outcome_data["outcome_normalized"] = "LOSS"
        outcome_data["confidence"] = "HIGH"
        outcome_data["outcome_percentage"] = 0
        outcome_data["author_perspective"]["outcome"] = "LOSS"
        outcome_data["author_perspective"]["got_what_requested"] = False
        outcome_data["defendant_perspective"]["outcome"] = "WIN"
        outcome_data["defendant_perspective"]["succeeded_in_defense"] = True

        match = re.search(r'.{0,100}JULG[OAR]+\s+IMPROCEDENTE.{0,100}', texto_upper)
        if match:
            outcome_data["outcome_reasoning"] = match.group(0)

    # Appeal patterns
    elif re.search(r'DAR\s+PROVIMENTO|PROV[IE]R|CONHECIDO\s+E\s+PROVIDO', texto_upper):
        outcome_data["primary_outcome"] = "PROVIDO"
        outcome_data["outcome_normalized"] = "WIN"
        outcome_data["confidence"] = "HIGH"

        match = re.search(r'.{0,100}(?:DAR\s+PROVIMENTO|PROV[IE]R).{0,100}', texto_upper)
        if match:
            outcome_data["outcome_reasoning"] = match.group(0)

    elif re.search(r'NEGAR\s+PROVIMENTO|DESPROV[IE]', texto_upper):
        outcome_data["primary_outcome"] = "DESPROVIDO"
        outcome_data["outcome_normalized"] = "LOSS"
        outcome_data["confidence"] = "HIGH"

        match = re.search(r'.{0,100}(?:NEGAR\s+PROVIMENTO|DESPROV[IE]).{0,100}', texto_upper)
        if match:
            outcome_data["outcome_reasoning"] = match.group(0)

    # NOT KNOWN
    elif re.search(r'N[ÃA]O\s+CONHEC', texto_upper):
        outcome_data["primary_outcome"] = "NAO_CONHECIDO"
        outcome_data["outcome_normalized"] = "UNKNOWN"
        outcome_data["confidence"] = "MEDIUM"

    # EXTINCT
    elif re.search(r'EXTINT[OA]', texto_upper):
        outcome_data["primary_outcome"] = "EXTINTO"
        outcome_data["outcome_normalized"] = "UNKNOWN"
        outcome_data["confidence"] = "MEDIUM"

    return outcome_data

def extract_decision_classification(texto: str) -> Dict[str, Any]:
    """Extract decision classification from text."""
    texto_upper = texto.upper()

    classification = {
        "decision_type": "UNKNOWN",
        "instance": "UNKNOWN",
        "decision_nature": "MERITO_FINAL"
    }

    # Decision type
    if re.search(r'ACÓRDÃO|ACORDÃO', texto_upper):
        classification["decision_type"] = "ACORDAO"
        classification["instance"] = "SEGUNDA_INSTANCIA"
    elif re.search(r'SENTENÇA|SENTENCA', texto_upper):
        classification["decision_type"] = "SENTENCA"
        classification["instance"] = "PRIMEIRA_INSTANCIA"
    elif re.search(r'DECISÃO\s+MONOCRÁTICA|DECISAO\s+MONOCRATICA', texto_upper):
        classification["decision_type"] = "DECISAO_MONOCRATICA"
        classification["instance"] = "SEGUNDA_INSTANCIA"
    elif re.search(r'DESPACHO', texto_upper):
        classification["decision_type"] = "DESPACHO"
        classification["decision_nature"] = "PROCESSUAL"

    return classification

def extract_procedural(texto: str) -> Dict[str, Any]:
    """Extract procedural details from text."""
    texto_upper = texto.upper()

    procedural = {
        "appeal_type": None,
        "who_appealed": None,
        "appeal_outcome": None,
        "decision_changed": None
    }

    # Appeal type
    if re.search(r'APELAÇÃO|APELACAO', texto_upper):
        procedural["appeal_type"] = "APELACAO"
    elif re.search(r'AGRAVO', texto_upper):
        procedural["appeal_type"] = "AGRAVO"
    elif re.search(r'RECURSO\s+ESPECIAL', texto_upper):
        procedural["appeal_type"] = "RECURSO_ESPECIAL"

    # Appeal outcome
    if re.search(r'(?:DAR\s+)?PROVIMENTO|PROVID[OA]', texto_upper):
        if re.search(r'PARCIALMENTE\s+PROVID', texto_upper):
            procedural["appeal_outcome"] = "PARCIALMENTE_PROVIDO"
        else:
            procedural["appeal_outcome"] = "PROVIDO"
            procedural["decision_changed"] = True
    elif re.search(r'(?:NEGAR\s+)?(?:PROVIMENTO|DESPROVID)', texto_upper):
        procedural["appeal_outcome"] = "DESPROVIDO"
        procedural["decision_changed"] = False
    elif re.search(r'N[ÃA]O\s+CONHEC', texto_upper):
        procedural["appeal_outcome"] = "NAO_CONHECIDO"
        procedural["decision_changed"] = False

    return procedural

def extract_quality_metadata(texto: str, labeling_difficulty: str, labeler_notes: str) -> Dict[str, Any]:
    """Extract quality metadata."""
    text_length = len(texto)

    # Assess text quality based on length and completeness
    text_quality = "MEDIUM"
    if text_length > 2000:
        text_quality = "HIGH"
    elif text_length < 500:
        text_quality = "LOW"

    contains_outcome = bool(re.search(r'(?:JULG[OAR]+|PROVIMENTO|PROCEDENTE|IMPROCEDENTE)', texto.upper()))

    quality = {
        "text_length": text_length,
        "text_quality": text_quality,
        "contains_full_decision": text_length > 1000,
        "contains_outcome_phrase": contains_outcome,
        "outcome_phrase_location": "UNKNOWN",
        "ambiguous_outcome": labeling_difficulty in ["HARD", "MEDIUM"],
        "missing_information": [],
        "labeler_notes": labeler_notes,
        "labeling_difficulty": labeling_difficulty,
        "labeling_time_seconds": None
    }

    return quality

def label_document(doc: Dict[str, Any], doc_index: int) -> Dict[str, Any]:
    """Label a single document with rich structured data."""
    texto_raw = doc.get('texto', '')
    texto = clean_html(texto_raw)  # Clean HTML before processing

    # Extract all components
    parties_data, is_inss = extract_parties(texto)
    lawyers_data = extract_lawyers(texto)
    outcome_data = extract_outcome(texto)
    classification = extract_decision_classification(texto)
    procedural = extract_procedural(texto)

    # Determine labeling difficulty and notes
    difficulty = "MEDIUM"
    notes = ""

    # Check if this is an administrative order (Ato Ordinatório)
    is_ato_ordinatorio = 'ATO ORDINATÓRIO' in texto.upper() or 'ATO ORDINATORIO' in texto.upper()
    is_cumprimento = 'CUMPRIMENTO DE SENTENÇA' in texto.upper() or 'CUMPRIMENTO DE SENTENCA' in texto.upper()

    if is_ato_ordinatorio:
        notes = "Ato Ordinatório (administrative order) - no outcome to extract"
        difficulty = "EASY"  # Easy to label since it's just identifying it as administrative
        # Override outcome for administrative orders
        outcome_data["outcome_normalized"] = "UNKNOWN"
        outcome_data["primary_outcome"] = "ATO_ORDINATORIO"
        outcome_data["confidence"] = "HIGH"  # We're confident it's an administrative order
        classification["decision_type"] = "DESPACHO"
        classification["decision_nature"] = "PROCESSUAL"
    elif is_cumprimento:
        notes = "Cumprimento de Sentença (enforcement procedure)"

    if outcome_data["confidence"] == "HIGH" and parties_data["simplified"]["author"]:
        if not is_ato_ordinatorio:
            difficulty = "EASY"
    elif outcome_data["confidence"] == "LOW" and not is_ato_ordinatorio:
        difficulty = "HARD"
        if not notes:
            notes = "Unclear outcome from text"

    if not parties_data["simplified"]["author"]:
        if notes:
            notes += " | Missing party information"
        else:
            notes = "Missing party information"

    quality = extract_quality_metadata(texto, difficulty, notes)

    # Update winner/loser based on outcome
    if outcome_data["outcome_normalized"] == "WIN":
        parties_data["simplified"]["winner"] = parties_data["simplified"]["author"]
        parties_data["simplified"]["loser"] = parties_data["simplified"]["defendant"]
    elif outcome_data["outcome_normalized"] == "LOSS":
        parties_data["simplified"]["winner"] = parties_data["simplified"]["defendant"]
        parties_data["simplified"]["loser"] = parties_data["simplified"]["author"]

    # Update lawyer side_won
    for lawyer in lawyers_data:
        if lawyer.get("representing") == "AUTOR":
            lawyer["side_won"] = outcome_data["author_perspective"]["outcome"] == "WIN"
            lawyer["party_name"] = parties_data["simplified"]["author"]
        elif lawyer.get("representing") == "REU":
            lawyer["side_won"] = outcome_data["defendant_perspective"]["outcome"] == "WIN"
            lawyer["party_name"] = parties_data["simplified"]["defendant"]
        elif lawyer.get("is_public_defender"):
            # Procuradoria Federal usually represents INSS (defendant)
            if "PROCURADORIA" in lawyer["name"]:
                lawyer["representing"] = "REU"
                lawyer["side_won"] = outcome_data["defendant_perspective"]["outcome"] == "WIN"
                lawyer["party_name"] = parties_data["simplified"]["defendant"]
            # Defensoria Publica usually represents author
            elif "DEFENSORIA" in lawyer["name"]:
                lawyer["representing"] = "AUTOR"
                lawyer["side_won"] = outcome_data["author_perspective"]["outcome"] == "WIN"
                lawyer["party_name"] = parties_data["simplified"]["author"]

    # Build final labeled document
    labeled = {
        "doc_id": 451 + doc_index,  # Documents 451-500
        "intimation_id": str(doc['intimation_id']),
        "numero_processo": doc.get('numero_processo'),
        "data_disponibilizacao": doc.get('data_disponibilizacao'),
        "tribunal": doc.get('sigla_tribunal'),
        "orgao": doc.get('nome_orgao'),

        "decision_classification": classification,
        "outcome": outcome_data,
        "parties": parties_data,
        "lawyers": {"lawyers": lawyers_data},
        "procedural": procedural,
        "quality": quality
    }

    return labeled

def main():
    """Main labeling function for Agent 9."""
    # Load raw documents
    with open('/home/user/causaganha/data/agent_9_raw.json', 'r', encoding='utf-8') as f:
        documents = json.load(f)

    print(f"Labeling {len(documents)} documents for Agent 9...")

    # Label each document
    labeled_documents = []
    for idx, doc in enumerate(documents):
        print(f"Labeling document {idx+1}/50: {doc['intimation_id']}")
        labeled = label_document(doc, idx)
        labeled_documents.append(labeled)

    # Calculate summary statistics
    high_conf = sum(1 for d in labeled_documents if d["outcome"]["confidence"] == "HIGH")
    medium_conf = sum(1 for d in labeled_documents if d["outcome"]["confidence"] == "MEDIUM")
    low_conf = sum(1 for d in labeled_documents if d["outcome"]["confidence"] == "LOW")

    # Build final output
    output = {
        "agent_id": 9,
        "docs_range": "451-500",
        "total_docs": len(labeled_documents),
        "labeling_date": datetime.now().strftime("%Y-%m-%d"),
        "documents": labeled_documents,
        "summary": {
            "total_labeled": len(labeled_documents),
            "high_confidence": high_conf,
            "medium_confidence": medium_conf,
            "low_confidence": low_conf,
            "ambiguous_outcomes": sum(1 for d in labeled_documents if d["quality"]["ambiguous_outcome"])
        }
    }

    # Save to output file
    output_path = '/home/user/causaganha/data/ground_truth_rich_agent_9.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Agent 9 Labeling Complete!")
    print(f"{'='*60}")
    print(f"Total documents labeled: {output['summary']['total_labeled']}")
    print(f"High confidence: {output['summary']['high_confidence']}")
    print(f"Medium confidence: {output['summary']['medium_confidence']}")
    print(f"Low confidence: {output['summary']['low_confidence']}")
    print(f"Ambiguous outcomes: {output['summary']['ambiguous_outcomes']}")
    print(f"\nOutput saved to: {output_path}")

if __name__ == "__main__":
    main()
