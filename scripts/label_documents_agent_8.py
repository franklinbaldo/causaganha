#!/usr/bin/env python3
"""
Agent 8 Document Labeling Script
Labels documents 401-450 with rich structured data
"""

import json
import re
from datetime import datetime
from html.parser import HTMLParser
from typing import Dict, List, Optional, Any


class MLStripper(HTMLParser):
    """Strip HTML tags from text"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_html(html: str) -> str:
    """Remove HTML tags and return plain text"""
    s = MLStripper()
    s.feed(html)
    text = s.get_data()
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_name(name: str) -> str:
    """Normalize party/lawyer names"""
    if not name:
        return ""
    name = name.strip().upper()
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name)
    return name


def extract_oab_info(text: str) -> List[Dict[str, Any]]:
    """Extract OAB numbers and lawyer names from text"""
    lawyers = []

    # Pattern: ADVOGADO(A): NAME - OAB/UF NUMBER
    # or ADVOGADO(A): NAME
    adv_patterns = [
        r'ADVOGADO\(A\)\s*:\s*([A-Z\s]+?)(?:\s*-\s*OAB/([A-Z]{2})\s*(\d+))?(?:\n|<|$)',
        r'Advogado\(a\)\s*:\s*([A-Z\s]+?)(?:\s*-\s*OAB/([A-Z]{2})\s*(\d+))?(?:\n|<|$)',
        r'ADVOGADO\s*:\s*([A-Z\s]+?)(?:\s*-\s*OAB/([A-Z]{2})\s*(\d+))?(?:\n|<|$)',
    ]

    for pattern in adv_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            name = match.group(1).strip()
            uf = match.group(2) if len(match.groups()) >= 2 else None
            numero = match.group(3) if len(match.groups()) >= 3 else None

            if name and not any(word in name.upper() for word in ['PROCURADORIA', 'DEFENSORIA']):
                lawyers.append({
                    'name': normalize_name(name),
                    'oab_uf': uf,
                    'oab_numero': numero
                })

    # Check for public defenders/prosecutors
    if 'PROCURADORIA FEDERAL' in text.upper():
        lawyers.append({
            'name': 'PROCURADORIA FEDERAL',
            'oab_uf': None,
            'oab_numero': None,
            'is_public_defender': True
        })

    if 'DEFENSORIA PUBLICA' in text.upper() or 'DEFENSORIA PÚBLICA' in text.upper():
        lawyers.append({
            'name': 'DEFENSORIA PUBLICA',
            'oab_uf': None,
            'oab_numero': None,
            'is_public_defender': True
        })

    return lawyers


def extract_parties(text: str) -> Dict[str, Any]:
    """Extract party information from decision text"""
    parties_info = {
        'author': None,
        'defendant': None,
        'winner': None,
        'loser': None
    }

    # Common patterns for parties
    autor_patterns = [
        r'AUTOR\s*[:/]\s*([A-Z\s]+?)(?:\n|<|ADVOGADO)',
        r'APELANTE\s*[:/]\s*([A-Z\s]+?)(?:\n|<|ADVOGADO)',
        r'AGRAVANTE\s*[:/]\s*([A-Z\s]+?)(?:\n|<|ADVOGADO)',
        r'RECORRENTE\s*[:/]\s*([A-Z\s]+?)(?:\n|<|ADVOGADO)',
    ]

    reu_patterns = [
        r'R[ÉE]U\s*[:/]\s*([A-Z\s]+?)(?:\n|<|ADVOGADO)',
        r'APELADO\s*[:/]\s*([A-Z\s]+?)(?:\n|<|ADVOGADO)',
        r'AGRAVADO\s*[:/]\s*([A-Z\s]+?)(?:\n|<|ADVOGADO)',
        r'RECORRIDO\s*[:/]\s*([A-Z\s]+?)(?:\n|<|ADVOGADO)',
    ]

    # Try to find author
    for pattern in autor_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parties_info['author'] = normalize_name(match.group(1))
            break

    # Try to find defendant
    for pattern in reu_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parties_info['defendant'] = normalize_name(match.group(1))
            break

    return parties_info


def analyze_outcome(text: str, parties: Dict[str, str]) -> Dict[str, Any]:
    """Analyze decision outcome"""
    text_upper = text.upper()

    # Initialize outcome structure
    outcome = {
        'primary_outcome': None,
        'outcome_normalized': None,
        'confidence': 'LOW',
        'outcome_percentage': None,
        'outcome_reasoning': '',
        'author_perspective': {
            'outcome': None,
            'got_what_requested': None
        },
        'defendant_perspective': {
            'outcome': None,
            'succeeded_in_defense': None
        }
    }

    # WIN patterns (PROCEDENTE)
    if re.search(r'JULGO?\s+PROCEDENTE', text_upper):
        outcome['primary_outcome'] = 'PROCEDENTE'
        outcome['outcome_normalized'] = 'WIN'
        outcome['confidence'] = 'HIGH'
        outcome['outcome_percentage'] = 100
        outcome['author_perspective']['outcome'] = 'WIN'
        outcome['author_perspective']['got_what_requested'] = True
        outcome['defendant_perspective']['outcome'] = 'LOSS'
        outcome['defendant_perspective']['succeeded_in_defense'] = False
        outcome['outcome_reasoning'] = 'Pedido julgado procedente'

    # LOSS patterns (IMPROCEDENTE)
    elif re.search(r'JULGO?\s+IMPROCEDENTE', text_upper):
        outcome['primary_outcome'] = 'IMPROCEDENTE'
        outcome['outcome_normalized'] = 'LOSS'
        outcome['confidence'] = 'HIGH'
        outcome['outcome_percentage'] = 0
        outcome['author_perspective']['outcome'] = 'LOSS'
        outcome['author_perspective']['got_what_requested'] = False
        outcome['defendant_perspective']['outcome'] = 'WIN'
        outcome['defendant_perspective']['succeeded_in_defense'] = True
        outcome['outcome_reasoning'] = 'Pedido julgado improcedente'

    # PARTIAL patterns
    elif re.search(r'PARCIALMENTE\s+PROCEDENTE', text_upper):
        outcome['primary_outcome'] = 'PARCIALMENTE_PROCEDENTE'
        outcome['outcome_normalized'] = 'PARTIAL'
        outcome['confidence'] = 'MEDIUM'
        outcome['outcome_percentage'] = 50
        outcome['author_perspective']['outcome'] = 'PARTIAL'
        outcome['author_perspective']['got_what_requested'] = False
        outcome['defendant_perspective']['outcome'] = 'PARTIAL'
        outcome['defendant_perspective']['succeeded_in_defense'] = False
        outcome['outcome_reasoning'] = 'Pedido parcialmente procedente'

    # Appeal outcomes
    elif re.search(r'DAR?\s+PROVIMENTO', text_upper) or re.search(r'PROV[EI]DO', text_upper):
        # Check who appealed
        if 'APELANTE' in text_upper or 'RECORRENTE' in text_upper:
            outcome['primary_outcome'] = 'PROVIDO'
            outcome['outcome_normalized'] = 'WIN'
            outcome['confidence'] = 'MEDIUM'
            outcome['outcome_percentage'] = 100
            outcome['author_perspective']['outcome'] = 'WIN'
            outcome['defendant_perspective']['outcome'] = 'LOSS'
            outcome['outcome_reasoning'] = 'Recurso provido'

    elif re.search(r'NEGAR?\s+PROVIMENTO', text_upper) or re.search(r'DESPROV[EI]DO', text_upper):
        outcome['primary_outcome'] = 'DESPROVIDO'
        outcome['outcome_normalized'] = 'LOSS'
        outcome['confidence'] = 'MEDIUM'
        outcome['outcome_percentage'] = 0
        outcome['author_perspective']['outcome'] = 'LOSS'
        outcome['defendant_perspective']['outcome'] = 'WIN'
        outcome['outcome_reasoning'] = 'Recurso desprovido'

    # EXTINTO
    elif re.search(r'EXTINTO', text_upper):
        outcome['primary_outcome'] = 'EXTINTO'
        outcome['outcome_normalized'] = 'UNKNOWN'
        outcome['confidence'] = 'MEDIUM'
        outcome['outcome_reasoning'] = 'Processo extinto'

    # NAO CONHECIDO
    elif re.search(r'N[ÃA]O\s+CONHEC', text_upper):
        outcome['primary_outcome'] = 'NAO_CONHECIDO'
        outcome['outcome_normalized'] = 'UNKNOWN'
        outcome['confidence'] = 'MEDIUM'
        outcome['outcome_reasoning'] = 'Recurso não conhecido'

    # Determine winner/loser
    if parties['author'] and parties['defendant']:
        if outcome['author_perspective']['outcome'] == 'WIN':
            parties['winner'] = parties['author']
            parties['loser'] = parties['defendant']
        elif outcome['author_perspective']['outcome'] == 'LOSS':
            parties['winner'] = parties['defendant']
            parties['loser'] = parties['author']
        elif outcome['author_perspective']['outcome'] == 'PARTIAL':
            parties['winner'] = 'BOTH'
            parties['loser'] = 'NONE'

    return outcome


def classify_decision(text: str) -> Dict[str, str]:
    """Classify decision type"""
    text_upper = text.upper()

    classification = {
        'decision_type': None,
        'instance': None,
        'decision_nature': None
    }

    # Decision type
    if 'ACORDAO' in text_upper or 'ACÓRDÃO' in text_upper:
        classification['decision_type'] = 'ACORDAO'
        classification['instance'] = 'SEGUNDA_INSTANCIA'
    elif 'SENTENCA' in text_upper or 'SENTENÇA' in text_upper:
        classification['decision_type'] = 'SENTENCA'
        classification['instance'] = 'PRIMEIRA_INSTANCIA'
    elif 'DECISAO MONOCRATICA' in text_upper or 'DECISÃO MONOCRÁTICA' in text_upper:
        classification['decision_type'] = 'DECISAO_MONOCRATICA'
        classification['instance'] = 'SEGUNDA_INSTANCIA'
    elif 'DESPACHO' in text_upper:
        classification['decision_type'] = 'DESPACHO'

    # Decision nature
    if any(word in text_upper for word in ['PROCEDENTE', 'IMPROCEDENTE', 'JULGO']):
        classification['decision_nature'] = 'MERITO_FINAL'
    elif 'LIMINAR' in text_upper:
        classification['decision_nature'] = 'LIMINAR'
    else:
        classification['decision_nature'] = 'PROCESSUAL'

    return classification


def extract_procedural_details(text: str) -> Dict[str, Any]:
    """Extract procedural information"""
    text_upper = text.upper()

    procedural = {
        'appeal_type': None,
        'who_appealed': None,
        'appeal_outcome': None,
        'decision_changed': None
    }

    # Appeal type
    if 'APELACAO' in text_upper or 'APELAÇÃO' in text_upper:
        procedural['appeal_type'] = 'APELACAO'
    elif 'AGRAVO' in text_upper:
        procedural['appeal_type'] = 'AGRAVO'
    elif 'RECURSO ESPECIAL' in text_upper:
        procedural['appeal_type'] = 'RECURSO_ESPECIAL'
    elif 'EMBARGOS' in text_upper:
        procedural['appeal_type'] = 'EMBARGOS'

    # Who appealed
    if 'APELANTE' in text_upper:
        procedural['who_appealed'] = 'AUTOR'
    if 'APELADO' in text_upper and procedural['who_appealed'] == 'AUTOR':
        # Both appealed if both terms present
        procedural['who_appealed'] = 'AMBOS'
    elif 'APELADO' in text_upper:
        procedural['who_appealed'] = 'REU'

    # Appeal outcome
    if re.search(r'DAR?\s+PROVIMENTO', text_upper) or 'PROVIDO' in text_upper:
        procedural['appeal_outcome'] = 'PROVIDO'
        procedural['decision_changed'] = True
    elif re.search(r'NEGAR?\s+PROVIMENTO', text_upper) or 'DESPROVIDO' in text_upper:
        procedural['appeal_outcome'] = 'DESPROVIDO'
        procedural['decision_changed'] = False
    elif 'PARCIALMENTE PROVIDO' in text_upper:
        procedural['appeal_outcome'] = 'PARCIALMENTE_PROVIDO'
        procedural['decision_changed'] = True
    elif re.search(r'N[ÃA]O\s+CONHEC', text_upper):
        procedural['appeal_outcome'] = 'NAO_CONHECIDO'
        procedural['decision_changed'] = False

    return procedural


def assess_quality(text: str, outcome: Dict) -> Dict[str, Any]:
    """Assess document quality and labeling difficulty"""
    quality = {
        'text_length': len(text),
        'text_quality': 'MEDIUM',
        'contains_full_decision': True,
        'ambiguous_outcome': False,
        'labeling_difficulty': 'MEDIUM',
        'labeler_notes': ''
    }

    # Text quality based on length
    if len(text) < 500:
        quality['text_quality'] = 'LOW'
        quality['contains_full_decision'] = False
        quality['labeler_notes'] = 'Texto muito curto, pode estar incompleto'
    elif len(text) > 2000:
        quality['text_quality'] = 'HIGH'

    # Ambiguous outcome
    if outcome['confidence'] == 'LOW' or outcome['outcome_normalized'] is None:
        quality['ambiguous_outcome'] = True
        quality['labeling_difficulty'] = 'HARD'
    elif outcome['confidence'] == 'HIGH':
        quality['labeling_difficulty'] = 'EASY'

    return quality


def label_document(doc: Dict, doc_id: int) -> Dict[str, Any]:
    """Label a single document with rich structured data"""

    # Get plain text from HTML
    plain_text = strip_html(doc['texto'])

    # Extract parties
    parties = extract_parties(plain_text)

    # Analyze outcome
    outcome = analyze_outcome(plain_text, parties)

    # Extract lawyers
    lawyers_raw = extract_oab_info(plain_text)
    lawyers_list = []

    for lawyer in lawyers_raw:
        lawyer_entry = {
            'name': lawyer['name'],
            'oab_numero': lawyer['oab_numero'],
            'oab_uf': lawyer['oab_uf'],
            'representing': None,  # Will be determined
            'party_name': None,
            'side_won': None
        }

        # Determine which side they represented
        # This is a simplified heuristic - in real cases, need more context
        if lawyer.get('is_public_defender'):
            lawyer_entry['representing'] = 'REU'
            lawyer_entry['party_name'] = parties.get('defendant')
            lawyer_entry['side_won'] = (outcome['defendant_perspective']['outcome'] == 'WIN')
            lawyer_entry['is_public_defender'] = True
        else:
            # Assume first lawyer is for author (heuristic)
            lawyer_entry['representing'] = 'AUTOR'
            lawyer_entry['party_name'] = parties.get('author')
            lawyer_entry['side_won'] = (outcome['author_perspective']['outcome'] == 'WIN')

        lawyers_list.append(lawyer_entry)

    # Classify decision
    classification = classify_decision(plain_text)

    # Extract procedural details
    procedural = extract_procedural_details(plain_text)

    # Assess quality
    quality = assess_quality(plain_text, outcome)

    # Build complete document structure
    labeled_doc = {
        'doc_id': doc_id,
        'intimation_id': str(doc['intimation_id']),
        'numero_processo': doc['numero_processo'],
        'data_disponibilizacao': doc['data_disponibilizacao'],
        'tribunal': doc['sigla_tribunal'],
        'orgao': doc['nome_orgao'],

        'decision_classification': classification,

        'outcome': outcome,

        'parties': {
            'simplified': parties
        },

        'lawyers': {
            'lawyers': lawyers_list
        },

        'procedural': procedural,

        'quality': quality
    }

    return labeled_doc


def main():
    """Main labeling function"""
    print("Agent 8: Starting document labeling...")
    print("Documents: 401-450 (OFFSET 400)")

    # Load documents
    with open('/home/user/causaganha/data/temp_docs_agent_8.json', 'r', encoding='utf-8') as f:
        docs = json.load(f)

    print(f"Loaded {len(docs)} documents")

    # Label each document
    labeled_documents = []
    for i, doc in enumerate(docs, start=401):
        print(f"Labeling doc {i}/450... (intimation_id: {doc['intimation_id']})")
        labeled_doc = label_document(doc, i)
        labeled_documents.append(labeled_doc)

    # Calculate summary statistics
    high_conf = sum(1 for d in labeled_documents if d['outcome']['confidence'] == 'HIGH')
    medium_conf = sum(1 for d in labeled_documents if d['outcome']['confidence'] == 'MEDIUM')
    low_conf = sum(1 for d in labeled_documents if d['outcome']['confidence'] == 'LOW')
    ambiguous = sum(1 for d in labeled_documents if d['quality']['ambiguous_outcome'])

    # Build final output
    output = {
        'agent_id': 8,
        'docs_range': '401-450',
        'total_docs': len(labeled_documents),
        'labeling_date': datetime.now().date().isoformat(),
        'documents': labeled_documents,
        'summary': {
            'total_labeled': len(labeled_documents),
            'high_confidence': high_conf,
            'medium_confidence': medium_conf,
            'low_confidence': low_conf,
            'ambiguous_outcomes': ambiguous
        }
    }

    # Save output
    output_path = '/home/user/causaganha/data/ground_truth_rich_agent_8.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print("LABELING COMPLETE!")
    print(f"{'='*60}")
    print(f"Total documents labeled: {len(labeled_documents)}")
    print(f"High confidence: {high_conf}")
    print(f"Medium confidence: {medium_conf}")
    print(f"Low confidence: {low_conf}")
    print(f"Ambiguous outcomes: {ambiguous}")
    print(f"\nOutput saved to: {output_path}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
