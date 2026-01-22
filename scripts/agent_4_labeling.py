#!/usr/bin/env python3
"""
Agent 4 - Ground Truth Labeling Script
Documents: 201-250 (intimation_id range based on OFFSET 200)
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any


class BrazilianLegalLabeler:
    """Expert labeler for Brazilian judicial decisions"""

    def __init__(self):
        self.doc_id_start = 201

    def normalize_name(self, name: str) -> str:
        """Normalize party/lawyer names"""
        if not name:
            return ""
        # Remove extra spaces, convert to uppercase
        return " ".join(name.upper().split())

    def extract_oab_info(self, text: str) -> List[Dict[str, Any]]:
        """Extract lawyer OAB information from text"""
        lawyers = []

        # Pattern 1: "Advogado: NAME - OAB/UF NUMBER"
        pattern1 = r'Advogado[a]?[:\s]+([A-ZÀÁÂÃÇÉÊÍÓÔÕÚ\s]+?)(?:\s*-\s*OAB/([A-Z]{2})\s*(\d+))?(?:\n|$|\.)'

        # Pattern 2: "OAB/UF NUMBER - NAME"
        pattern2 = r'OAB/([A-Z]{2})\s*(\d+)\s*-\s*([A-ZÀÁÂÃÇÉÊÍÓÔÕÚ\s]+?)(?:\n|$|\.)'

        # Pattern 3: Just "OAB/UF NUMBER" in context
        pattern3 = r'OAB/([A-Z]{2})\s*(\d+)'

        for match in re.finditer(pattern1, text, re.MULTILINE | re.IGNORECASE):
            name = self.normalize_name(match.group(1))
            oab_uf = match.group(2) if match.group(2) else None
            oab_num = match.group(3) if match.group(3) else None
            if name:
                lawyers.append({
                    'name': name,
                    'oab_numero': oab_num,
                    'oab_uf': oab_uf
                })

        # Check for public defenders (Procuradoria, Defensoria)
        if re.search(r'PROCURADORIA FEDERAL', text, re.IGNORECASE):
            lawyers.append({
                'name': 'PROCURADORIA FEDERAL',
                'oab_numero': None,
                'oab_uf': None,
                'is_public_defender': True
            })

        if re.search(r'DEFENSORIA P[UÚ]BLICA', text, re.IGNORECASE):
            lawyers.append({
                'name': 'DEFENSORIA PÚBLICA',
                'oab_numero': None,
                'oab_uf': None,
                'is_public_defender': True
            })

        return lawyers

    def extract_parties(self, text: str) -> Dict[str, Optional[str]]:
        """Extract party names from text"""
        parties = {
            'author': None,
            'defendant': None
        }

        # Common patterns for parties
        patterns = [
            (r'Apelante[:\s]+([A-ZÀÁÂÃÇÉÊÍÓÔÕÚ][A-ZÀÁÂÃÇÉÊÍÓÔÕÚ\s\-\.]+?)(?:\n|Apelad)', 'apelante'),
            (r'Apelado[:\s]+([A-ZÀÁÂÃÇÉÊÍÓÔÕÚ][A-ZÀÁÂÃÇÉÊÍÓÔÕÚ\s\-\.]+?)(?:\n|Advogad)', 'apelado'),
            (r'Autor[:\s]+([A-ZÀÁÂÃÇÉÊÍÓÔÕÚ][A-ZÀÁÂÃÇÉÊÍÓÔÕÚ\s\-\.]+?)(?:\n|R[ée]u)', 'autor'),
            (r'R[ée]u[:\s]+([A-ZÀÁÂÃÇÉÊÍÓÔÕÚ][A-ZÀÁÂÃÇÉÊÍÓÔÕÚ\s\-\.]+?)(?:\n|Advogad)', 'reu'),
            (r'Recorrente[:\s]+([A-ZÀÁÂÃÇÉÊÍÓÔÕÚ][A-ZÀÁÂÃÇÉÊÍÓÔÕÚ\s\-\.]+?)(?:\n|Recorrid)', 'recorrente'),
            (r'Recorrido[:\s]+([A-ZÀÁÂÃÇÉÊÍÓÔÕÚ][A-ZÀÁÂÃÇÉÊÍÓÔÕÚ\s\-\.]+?)(?:\n|Advogad)', 'recorrido'),
        ]

        extracted = {}
        for pattern, role in patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                name = self.normalize_name(match.group(1).strip())
                # Clean up common artifacts
                name = re.sub(r'\s+', ' ', name)
                name = name.replace('.', '').strip()
                extracted[role] = name

        # Map to author/defendant
        if 'apelante' in extracted:
            # In appeal, apelante could be either author or defendant
            # Need to check if they won or lost originally
            parties['author'] = extracted.get('apelante') or extracted.get('autor')
            parties['defendant'] = extracted.get('apelado') or extracted.get('reu')
        elif 'autor' in extracted:
            parties['author'] = extracted['autor']
            parties['defendant'] = extracted.get('reu')
        elif 'recorrente' in extracted:
            parties['author'] = extracted.get('recorrente')
            parties['defendant'] = extracted.get('recorrido')

        return parties

    def extract_outcome(self, text: str, parties: Dict) -> Dict[str, Any]:
        """Extract outcome information"""
        text_lower = text.lower()

        # Outcome patterns (most specific to least specific)
        outcome_patterns = {
            'PROCEDENTE': [
                r'julgo?\s+procedente',
                r'dar\s+provimento.*?apela[çc][ãa]o.*?para\s+julgar\s+procedente',
                r'procedente\s+o\s+pedido',
            ],
            'IMPROCEDENTE': [
                r'julgo?\s+improcedente',
                r'negar\s+provimento',
                r'improcedente\s+o\s+pedido',
                r'n[ãa]o\s+conhec'
            ],
            'PARCIALMENTE_PROCEDENTE': [
                r'parcialmente\s+procedente',
                r'julgo?\s+procedente\s+em\s+parte',
                r'parcial\s+provimento'
            ],
            'NAO_CONHECIDO': [
                r'n[ãa]o\s+conhec',
                r'n[ãa]o\s+se\s+conhece'
            ],
            'EXTINTO': [
                r'extinto\s+(?:o\s+)?processo',
                r'extin[çc][ãa]o\s+(?:do\s+)?processo'
            ]
        }

        primary_outcome = None
        confidence = "LOW"
        outcome_reasoning = ""

        # Search for outcome patterns
        for outcome, patterns in outcome_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    primary_outcome = outcome
                    confidence = "HIGH"
                    # Extract surrounding context for reasoning
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    outcome_reasoning = text[start:end].replace('\n', ' ').strip()
                    break
            if primary_outcome:
                break

        # Determine normalized outcome
        outcome_normalized = "UNKNOWN"
        outcome_percentage = 50

        if primary_outcome == "PROCEDENTE":
            outcome_normalized = "WIN"
            outcome_percentage = 100
        elif primary_outcome == "IMPROCEDENTE":
            outcome_normalized = "LOSS"
            outcome_percentage = 0
        elif primary_outcome == "PARCIALMENTE_PROCEDENTE":
            outcome_normalized = "PARTIAL"
            outcome_percentage = 50
        elif primary_outcome in ["NAO_CONHECIDO", "EXTINTO"]:
            outcome_normalized = "UNKNOWN"
            outcome_percentage = 0

        # Determine perspective outcomes
        if outcome_normalized == "WIN":
            author_outcome = "WIN"
            defendant_outcome = "LOSS"
            got_what_requested = True
            succeeded_in_defense = False
        elif outcome_normalized == "LOSS":
            author_outcome = "LOSS"
            defendant_outcome = "WIN"
            got_what_requested = False
            succeeded_in_defense = True
        elif outcome_normalized == "PARTIAL":
            author_outcome = "PARTIAL"
            defendant_outcome = "PARTIAL"
            got_what_requested = False
            succeeded_in_defense = False
        else:
            author_outcome = "UNKNOWN"
            defendant_outcome = "UNKNOWN"
            got_what_requested = False
            succeeded_in_defense = False

        return {
            'primary_outcome': primary_outcome,
            'outcome_normalized': outcome_normalized,
            'confidence': confidence,
            'outcome_percentage': outcome_percentage,
            'outcome_reasoning': outcome_reasoning[:200] if outcome_reasoning else "No clear outcome phrase found",
            'author_perspective': {
                'outcome': author_outcome,
                'got_what_requested': got_what_requested
            },
            'defendant_perspective': {
                'outcome': defendant_outcome,
                'succeeded_in_defense': succeeded_in_defense
            }
        }

    def extract_decision_classification(self, text: str) -> Dict[str, Optional[str]]:
        """Extract decision type classification"""
        text_lower = text.lower()

        decision_type = None
        if re.search(r'ac[óo]rd[ãa]o', text_lower):
            decision_type = "ACORDAO"
        elif re.search(r'senten[çc]a', text_lower):
            decision_type = "SENTENCA"
        elif re.search(r'decis[ãa]o\s+monocr[áa]tica', text_lower):
            decision_type = "DECISAO_MONOCRATICA"
        elif re.search(r'despacho', text_lower):
            decision_type = "DESPACHO"

        # Determine instance
        instance = None
        if decision_type == "ACORDAO" or decision_type == "DECISAO_MONOCRATICA":
            instance = "SEGUNDA_INSTANCIA"
        elif decision_type == "SENTENCA":
            instance = "PRIMEIRA_INSTANCIA"

        # Determine nature
        decision_nature = None
        if re.search(r'liminar|liminarmente', text_lower):
            decision_nature = "LIMINAR"
        elif re.search(r'm[ée]rito', text_lower):
            decision_nature = "MERITO_FINAL"
        elif decision_type in ["ACORDAO", "SENTENCA"]:
            decision_nature = "MERITO_FINAL"
        else:
            decision_nature = "PROCESSUAL"

        return {
            'decision_type': decision_type,
            'instance': instance,
            'decision_nature': decision_nature
        }

    def extract_procedural_details(self, text: str) -> Dict[str, Any]:
        """Extract procedural information"""
        text_lower = text.lower()

        # Appeal type
        appeal_type = None
        if re.search(r'apela[çc][ãa]o', text_lower):
            appeal_type = "APELACAO"
        elif re.search(r'agravo', text_lower):
            appeal_type = "AGRAVO"
        elif re.search(r'recurso\s+especial', text_lower):
            appeal_type = "RECURSO_ESPECIAL"
        elif re.search(r'embargos', text_lower):
            appeal_type = "EMBARGOS"

        # Who appealed
        who_appealed = None
        if re.search(r'apelante.*?autor', text_lower):
            who_appealed = "AUTOR"
        elif re.search(r'apelante.*?r[ée]u', text_lower):
            who_appealed = "REU"

        # Appeal outcome
        appeal_outcome = None
        if re.search(r'dar\s+provimento|prov[êe]r|provido', text_lower):
            if re.search(r'parcial', text_lower):
                appeal_outcome = "PARCIALMENTE_PROVIDO"
            else:
                appeal_outcome = "PROVIDO"
        elif re.search(r'negar\s+provimento|desprov|negado', text_lower):
            appeal_outcome = "DESPROVIDO"
        elif re.search(r'n[ãa]o\s+conhec', text_lower):
            appeal_outcome = "NAO_CONHECIDO"

        # Decision changed
        decision_changed = False
        if appeal_outcome in ["PROVIDO", "PARCIALMENTE_PROVIDO"]:
            decision_changed = True

        return {
            'appeal_type': appeal_type,
            'who_appealed': who_appealed,
            'appeal_outcome': appeal_outcome,
            'decision_changed': decision_changed
        }

    def assess_quality(self, text: str, outcome: Dict) -> Dict[str, Any]:
        """Assess document quality"""
        text_length = len(text)

        # Text quality
        if text_length > 3000:
            text_quality = "HIGH"
        elif text_length > 1000:
            text_quality = "MEDIUM"
        else:
            text_quality = "LOW"

        # Labeling difficulty
        if outcome['confidence'] == "HIGH" and text_length > 2000:
            labeling_difficulty = "EASY"
        elif outcome['confidence'] == "MEDIUM":
            labeling_difficulty = "MEDIUM"
        else:
            labeling_difficulty = "HARD"

        # Ambiguous outcome
        ambiguous_outcome = (outcome['confidence'] == "LOW")

        return {
            'text_quality': text_quality,
            'ambiguous_outcome': ambiguous_outcome,
            'labeling_difficulty': labeling_difficulty,
            'labeler_notes': f"Text length: {text_length} chars. Outcome confidence: {outcome['confidence']}"
        }

    def label_document(self, doc: Dict, doc_id: int) -> Dict[str, Any]:
        """Label a single document with rich structured data"""
        texto = doc.get('texto', '')

        # Extract all information
        parties_info = self.extract_parties(texto)
        outcome_info = self.extract_outcome(texto, parties_info)
        lawyers_raw = self.extract_oab_info(texto)
        decision_class = self.extract_decision_classification(texto)
        procedural = self.extract_procedural_details(texto)
        quality = self.assess_quality(texto, outcome_info)

        # Determine winner/loser
        winner = None
        loser = None
        if outcome_info['outcome_normalized'] == "WIN":
            winner = parties_info['author']
            loser = parties_info['defendant']
        elif outcome_info['outcome_normalized'] == "LOSS":
            winner = parties_info['defendant']
            loser = parties_info['author']
        elif outcome_info['outcome_normalized'] == "PARTIAL":
            winner = "BOTH"
            loser = None

        # Build lawyers list with side_won
        lawyers = []
        for lawyer in lawyers_raw:
            # Determine which side they represented
            representing = None
            party_name = None
            side_won = None

            # Simple heuristic: check proximity to party names in text
            if parties_info['author'] and lawyer['name'] in texto:
                # Check if lawyer appears near author name
                author_pos = texto.find(parties_info['author'])
                lawyer_pos = texto.find(lawyer['name'])
                if author_pos > 0 and lawyer_pos > 0:
                    if abs(author_pos - lawyer_pos) < 500:
                        representing = "AUTOR"
                        party_name = parties_info['author']
                        side_won = (outcome_info['author_perspective']['outcome'] == "WIN")

            if not representing and parties_info['defendant']:
                # Check defendant
                defendant_pos = texto.find(parties_info['defendant']) if parties_info['defendant'] else -1
                lawyer_pos = texto.find(lawyer['name'])
                if defendant_pos > 0 and lawyer_pos > 0:
                    if abs(defendant_pos - lawyer_pos) < 500:
                        representing = "REU"
                        party_name = parties_info['defendant']
                        side_won = (outcome_info['defendant_perspective']['outcome'] == "WIN")

            # For public defenders (INSS cases), usually represent defendant
            if lawyer.get('is_public_defender') and 'PROCURADORIA FEDERAL' in lawyer['name']:
                representing = "REU"
                party_name = parties_info['defendant']
                side_won = (outcome_info['defendant_perspective']['outcome'] == "WIN")

            lawyers.append({
                'name': lawyer['name'],
                'oab_numero': lawyer['oab_numero'],
                'oab_uf': lawyer['oab_uf'],
                'representing': representing,
                'party_name': party_name,
                'side_won': side_won,
                **({'is_public_defender': True} if lawyer.get('is_public_defender') else {})
            })

        # Build complete labeled document
        labeled_doc = {
            'doc_id': doc_id,
            'intimation_id': str(doc['intimation_id']),
            'numero_processo': doc.get('numero_processo'),
            'data_disponibilizacao': doc.get('data_disponibilizacao'),
            'tribunal': doc.get('sigla_tribunal'),
            'orgao': doc.get('nome_orgao'),

            # P1 - CRITICAL
            'outcome': outcome_info,
            'parties': {
                'simplified': {
                    'author': parties_info['author'],
                    'defendant': parties_info['defendant'],
                    'winner': winner,
                    'loser': loser
                }
            },
            'lawyers': {
                'lawyers': lawyers
            },

            # P2 - HIGH
            'decision_classification': decision_class,
            'procedural': procedural,
            'quality': quality
        }

        return labeled_doc

    def label_all_documents(self, input_file: str, output_file: str):
        """Label all documents and save to output file"""
        # Load documents
        with open(input_file, 'r', encoding='utf-8') as f:
            docs = json.load(f)

        print(f"Labeling {len(docs)} documents...")

        labeled_documents = []
        for i, doc in enumerate(docs):
            doc_id = self.doc_id_start + i
            print(f"Labeling doc {doc_id} (intimation_id: {doc['intimation_id']})...")

            labeled_doc = self.label_document(doc, doc_id)
            labeled_documents.append(labeled_doc)

        # Calculate summary statistics
        high_conf = sum(1 for d in labeled_documents if d['outcome']['confidence'] == 'HIGH')
        medium_conf = sum(1 for d in labeled_documents if d['outcome']['confidence'] == 'MEDIUM')
        low_conf = sum(1 for d in labeled_documents if d['outcome']['confidence'] == 'LOW')

        # Build final output
        output = {
            'agent_id': 4,
            'docs_range': '201-250',
            'total_docs': len(labeled_documents),
            'labeling_date': datetime.now().strftime('%Y-%m-%d'),
            'documents': labeled_documents,
            'summary': {
                'total_labeled': len(labeled_documents),
                'high_confidence': high_conf,
                'medium_confidence': medium_conf,
                'low_confidence': low_conf,
                'ambiguous_outcomes': sum(1 for d in labeled_documents if d['quality']['ambiguous_outcome'])
            }
        }

        # Save output
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n✓ Labeling complete!")
        print(f"  Total documents: {len(labeled_documents)}")
        print(f"  High confidence: {high_conf}")
        print(f"  Medium confidence: {medium_conf}")
        print(f"  Low confidence: {low_conf}")
        print(f"  Output saved to: {output_file}")


if __name__ == '__main__':
    labeler = BrazilianLegalLabeler()
    labeler.label_all_documents(
        input_file='/home/user/causaganha/data/agent_4_raw_docs.json',
        output_file='/home/user/causaganha/data/ground_truth_rich_agent_4.json'
    )
