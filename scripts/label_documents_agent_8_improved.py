#!/usr/bin/env python3
"""
Agent 8 Document Labeling Script - IMPROVED VERSION
Labels documents 401-450 with rich structured data
Properly handles procedural documents and actual decisions
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
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_name(name: str) -> str:
    """Normalize party/lawyer names"""
    if not name:
        return ""
    name = name.strip().upper()
    name = re.sub(r'\s+', ' ', name)
    return name


def extract_lawyers_from_html(html: str) -> List[Dict[str, Any]]:
    """Extract lawyer information from HTML tables"""
    lawyers = []

    # Pattern for lawyer in table: <td>ADVOGADO(A)</td><td>: NAME (OAB UF123456)</td>
    pattern = r'ADVOGADO\(A\)\s*</td><td>\s*:\s*([^<(]+)(?:\(OAB\s+([A-Z]{2})(\d+)\))?'

    for match in re.finditer(pattern, html, re.IGNORECASE):
        name = match.group(1).strip()
        uf = match.group(2) if match.group(2) else None
        numero = match.group(3) if match.group(3) else None

        lawyers.append({
            'name': normalize_name(name),
            'oab_uf': uf,
            'oab_numero': numero,
            'is_public_defender': False
        })

    return lawyers


def is_procedural_document(text: str) -> tuple[bool, str]:
    """Check if document is procedural (not a decision)"""
    text_upper = text.upper()

    if 'SIGILOSO' in text_upper or 'PARA VISUALIZA' in text_upper:
        return True, 'PROCESSO_SIGILOSO'
    elif 'ATO ORDINATORIO' in text_upper or 'ATO ORDINATÓRIO' in text_upper:
        return True, 'ATO_ORDINATORIO'
    elif 'DESPACHO' in text_upper and 'SENTENCA' not in text_upper and 'ACORDAO' not in text_upper:
        return True, 'DESPACHO'

    return False, None


def label_document_manual(doc_id: int, intimation_id: str, numero_processo: str,
                          data_disp: str, tribunal: str, orgao: str,
                          html_text: str) -> Dict[str, Any]:
    """
    Manually label the 3 actual decisions (docs 410, 412, 425)
    """

    plain_text = strip_html(html_text)

    # Extract lawyers
    lawyers_list = extract_lawyers_from_html(html_text)

    # Doc 410 - GISELDA APARECIDA DE OLIVEIRA NEIVERTH
    if intimation_id == '494496961':
        return {
            'doc_id': doc_id,
            'intimation_id': intimation_id,
            'numero_processo': numero_processo,
            'data_disponibilizacao': data_disp,
            'tribunal': tribunal,
            'orgao': orgao,

            'decision_classification': {
                'decision_type': 'SENTENCA',
                'instance': 'PRIMEIRA_INSTANCIA',
                'decision_nature': 'PROCESSUAL',
                'procedural_phase': 'EXTINTO_SEM_MERITO'
            },

            'outcome': {
                'primary_outcome': 'EXTINTO',
                'outcome_detail': 'SEM_RESOLUCAO_MERITO',
                'outcome_normalized': 'LOSS',
                'confidence': 'HIGH',
                'outcome_percentage': 0,
                'outcome_reasoning': 'Petição inicial indeferida e processo extinto sem resolução de mérito (art. 485, I, CPC)',
                'author_perspective': {
                    'outcome': 'LOSS',
                    'got_what_requested': False,
                    'percentage_obtained': 0
                },
                'defendant_perspective': {
                    'outcome': 'WIN',
                    'succeeded_in_defense': True
                }
            },

            'parties': {
                'parties': [
                    {
                        'role': 'IMPETRANTE',
                        'name': 'GISELDA APARECIDA DE OLIVEIRA NEIVERTH',
                        'normalized_name': 'GISELDA APARECIDA DE OLIVEIRA NEIVERTH',
                        'party_type': 'PESSOA_FISICA',
                        'is_winner': False,
                        'is_government': False,
                        'is_inss': False
                    }
                ],
                'simplified': {
                    'author': 'GISELDA APARECIDA DE OLIVEIRA NEIVERTH',
                    'defendant': 'AUTORIDADE COATORA',
                    'winner': 'AUTORIDADE COATORA',
                    'loser': 'GISELDA APARECIDA DE OLIVEIRA NEIVERTH'
                }
            },

            'lawyers': {
                'lawyers': [
                    {
                        'name': 'ALESXANDRO DOS SANTOS VANDRES PASINI',
                        'oab_numero': '046428',
                        'oab_uf': 'PR',
                        'oab_full': 'OAB/PR 046428',
                        'representing': 'AUTOR',
                        'party_name': 'GISELDA APARECIDA DE OLIVEIRA NEIVERTH',
                        'side_won': False,
                        'performance_score': 'LOSS'
                    }
                ]
            },

            'legal_subject': {
                'primary_area': 'ADMINISTRATIVO',
                'secondary_area': 'MANDADO_DE_SEGURANCA',
                'specific_issue': 'INADMISSIBILIDADE',
                'keywords': ['mandado de segurança', 'extinção sem mérito', 'petição inicial'],
                'is_social_security': False,
                'involves_monetary_value': False
            },

            'procedural': {
                'appeal_type': None,
                'who_appealed': None,
                'appeal_outcome': None,
                'unanimous': None,
                'decision_changed': None
            },

            'quality': {
                'text_length': len(plain_text),
                'text_quality': 'HIGH',
                'contains_full_decision': True,
                'contains_outcome_phrase': True,
                'outcome_phrase_location': 'END',
                'ambiguous_outcome': False,
                'missing_information': ['defendant_details'],
                'labeling_difficulty': 'EASY',
                'labeler_notes': 'Mandado de Segurança - petição indeferida, extinto sem mérito'
            }
        }

    # Doc 412 - ANTONIO JOSE ALVES MOURA
    elif intimation_id == '494496965':
        return {
            'doc_id': doc_id,
            'intimation_id': intimation_id,
            'numero_processo': numero_processo,
            'data_disponibilizacao': data_disp,
            'tribunal': tribunal,
            'orgao': orgao,

            'decision_classification': {
                'decision_type': 'SENTENCA',
                'instance': 'PRIMEIRA_INSTANCIA',
                'decision_nature': 'MERITO_FINAL',
                'procedural_phase': 'IMPROCEDENTE'
            },

            'outcome': {
                'primary_outcome': 'IMPROCEDENTE',
                'outcome_detail': 'TOTAL',
                'outcome_normalized': 'LOSS',
                'confidence': 'HIGH',
                'outcome_percentage': 0,
                'outcome_reasoning': 'Pedido julgado improcedente, segurança denegada (art. 487, I, CPC)',
                'author_perspective': {
                    'outcome': 'LOSS',
                    'got_what_requested': False,
                    'percentage_obtained': 0
                },
                'defendant_perspective': {
                    'outcome': 'WIN',
                    'succeeded_in_defense': True
                }
            },

            'parties': {
                'parties': [
                    {
                        'role': 'IMPETRANTE',
                        'name': 'ANTONIO JOSE ALVES MOURA',
                        'normalized_name': 'ANTONIO JOSE ALVES MOURA',
                        'party_type': 'PESSOA_FISICA',
                        'is_winner': False,
                        'is_government': False,
                        'is_inss': False
                    }
                ],
                'simplified': {
                    'author': 'ANTONIO JOSE ALVES MOURA',
                    'defendant': 'AUTORIDADE COATORA',
                    'winner': 'AUTORIDADE COATORA',
                    'loser': 'ANTONIO JOSE ALVES MOURA'
                }
            },

            'lawyers': {
                'lawyers': [
                    {
                        'name': 'FERNANDA LUSZCZYNSKI',
                        'oab_numero': '077372',
                        'oab_uf': 'PR',
                        'oab_full': 'OAB/PR 077372',
                        'representing': 'AUTOR',
                        'party_name': 'ANTONIO JOSE ALVES MOURA',
                        'side_won': False,
                        'performance_score': 'LOSS'
                    }
                ]
            },

            'legal_subject': {
                'primary_area': 'ADMINISTRATIVO',
                'secondary_area': 'MANDADO_DE_SEGURANCA',
                'specific_issue': 'SEGURANCA_DENEGADA',
                'keywords': ['mandado de segurança', 'improcedente', 'denegação'],
                'is_social_security': False,
                'involves_monetary_value': False
            },

            'procedural': {
                'appeal_type': None,
                'who_appealed': None,
                'appeal_outcome': None,
                'unanimous': None,
                'decision_changed': None
            },

            'quality': {
                'text_length': len(plain_text),
                'text_quality': 'HIGH',
                'contains_full_decision': True,
                'contains_outcome_phrase': True,
                'outcome_phrase_location': 'END',
                'ambiguous_outcome': False,
                'missing_information': ['defendant_details'],
                'labeling_difficulty': 'EASY',
                'labeler_notes': 'Mandado de Segurança - pedido improcedente, segurança denegada'
            }
        }

    # Doc 425 - MELANI MENDES FARAH CARDOSO
    elif intimation_id == '494496994':
        return {
            'doc_id': doc_id,
            'intimation_id': intimation_id,
            'numero_processo': numero_processo,
            'data_disponibilizacao': data_disp,
            'tribunal': tribunal,
            'orgao': orgao,

            'decision_classification': {
                'decision_type': 'SENTENCA',
                'instance': 'PRIMEIRA_INSTANCIA',
                'decision_nature': 'PROCESSUAL',
                'procedural_phase': 'EXTINTO_SEM_MERITO'
            },

            'outcome': {
                'primary_outcome': 'EXTINTO',
                'outcome_detail': 'SEM_RESOLUCAO_MERITO',
                'outcome_normalized': 'LOSS',
                'confidence': 'HIGH',
                'outcome_percentage': 0,
                'outcome_reasoning': 'Processo extinto sem resolução de mérito (art. 485, VI, CPC), segurança denegada',
                'author_perspective': {
                    'outcome': 'LOSS',
                    'got_what_requested': False,
                    'percentage_obtained': 0
                },
                'defendant_perspective': {
                    'outcome': 'WIN',
                    'succeeded_in_defense': True
                }
            },

            'parties': {
                'parties': [
                    {
                        'role': 'IMPETRANTE',
                        'name': 'MELANI MENDES FARAH CARDOSO',
                        'normalized_name': 'MELANI MENDES FARAH CARDOSO',
                        'party_type': 'PESSOA_FISICA',
                        'is_winner': False,
                        'is_government': False,
                        'is_inss': False
                    }
                ],
                'simplified': {
                    'author': 'MELANI MENDES FARAH CARDOSO',
                    'defendant': 'AUTORIDADE COATORA',
                    'winner': 'AUTORIDADE COATORA',
                    'loser': 'MELANI MENDES FARAH CARDOSO'
                }
            },

            'lawyers': {
                'lawyers': [
                    {
                        'name': 'JOAO FELIPE ZILIO',
                        'oab_numero': '108981',
                        'oab_uf': 'PR',
                        'oab_full': 'OAB/PR 108981',
                        'representing': 'AUTOR',
                        'party_name': 'MELANI MENDES FARAH CARDOSO',
                        'side_won': False,
                        'performance_score': 'LOSS'
                    },
                    {
                        'name': 'JOAO VITOR BASQUERA',
                        'oab_numero': '119023',
                        'oab_uf': 'PR',
                        'oab_full': 'OAB/PR 119023',
                        'representing': 'AUTOR',
                        'party_name': 'MELANI MENDES FARAH CARDOSO',
                        'side_won': False,
                        'performance_score': 'LOSS'
                    }
                ]
            },

            'legal_subject': {
                'primary_area': 'ADMINISTRATIVO',
                'secondary_area': 'MANDADO_DE_SEGURANCA',
                'specific_issue': 'EXTINCAO_SEM_MERITO',
                'keywords': ['mandado de segurança', 'extinção sem mérito', 'denegação'],
                'is_social_security': False,
                'involves_monetary_value': False
            },

            'procedural': {
                'appeal_type': None,
                'who_appealed': None,
                'appeal_outcome': None,
                'unanimous': None,
                'decision_changed': None
            },

            'quality': {
                'text_length': len(plain_text),
                'text_quality': 'HIGH',
                'contains_full_decision': True,
                'contains_outcome_phrase': True,
                'outcome_phrase_location': 'END',
                'ambiguous_outcome': False,
                'missing_information': ['defendant_details'],
                'labeling_difficulty': 'EASY',
                'labeler_notes': 'Mandado de Segurança - extinto sem mérito, segurança denegada. Dois advogados para o impetrante.'
            }
        }

    # Should not reach here
    return None


def label_procedural_document(doc_id: int, intimation_id: str, numero_processo: str,
                               data_disp: str, tribunal: str, orgao: str,
                               html_text: str, proc_type: str) -> Dict[str, Any]:
    """Label procedural (non-decision) documents"""

    plain_text = strip_html(html_text)

    # Extract basic party info if available
    author_match = re.search(r'AUTOR\s*</td><td>\s*:\s*([^<]+)', html_text)
    author = normalize_name(author_match.group(1)) if author_match else None

    # Extract lawyers if available
    lawyers_list = extract_lawyers_from_html(html_text)
    lawyers_formatted = []
    for lawyer in lawyers_list:
        lawyers_formatted.append({
            'name': lawyer['name'],
            'oab_numero': lawyer['oab_numero'],
            'oab_uf': lawyer['oab_uf'],
            'oab_full': f"OAB/{lawyer['oab_uf']} {lawyer['oab_numero']}" if lawyer['oab_uf'] and lawyer['oab_numero'] else None,
            'representing': 'AUTOR' if author else None,
            'party_name': author,
            'side_won': None,  # Not applicable for procedural docs
            'performance_score': None
        })

    return {
        'doc_id': doc_id,
        'intimation_id': intimation_id,
        'numero_processo': numero_processo,
        'data_disponibilizacao': data_disp,
        'tribunal': tribunal,
        'orgao': orgao,

        'decision_classification': {
            'decision_type': proc_type,
            'instance': 'PRIMEIRA_INSTANCIA' if 'JUIZADO' in html_text.upper() else 'UNKNOWN',
            'decision_nature': 'PROCESSUAL',
            'procedural_phase': 'ANDAMENTO'
        },

        'outcome': {
            'primary_outcome': 'NAO_APLICAVEL',
            'outcome_detail': 'DOCUMENTO_PROCESSUAL',
            'outcome_normalized': 'UNKNOWN',
            'confidence': 'HIGH',
            'outcome_percentage': None,
            'outcome_reasoning': f'Documento processual ({proc_type}), não é uma decisão de mérito',
            'author_perspective': {
                'outcome': None,
                'got_what_requested': None,
                'percentage_obtained': None
            },
            'defendant_perspective': {
                'outcome': None,
                'succeeded_in_defense': None
            }
        },

        'parties': {
            'parties': [],
            'simplified': {
                'author': author,
                'defendant': None,
                'winner': None,
                'loser': None
            }
        },

        'lawyers': {
            'lawyers': lawyers_formatted
        },

        'legal_subject': {
            'primary_area': 'UNKNOWN',
            'secondary_area': None,
            'specific_issue': None,
            'keywords': [],
            'is_social_security': False,
            'involves_monetary_value': False
        },

        'procedural': {
            'appeal_type': None,
            'who_appealed': None,
            'appeal_outcome': None,
            'unanimous': None,
            'decision_changed': None
        },

        'quality': {
            'text_length': len(plain_text),
            'text_quality': 'MEDIUM' if len(plain_text) > 100 else 'LOW',
            'contains_full_decision': False,
            'contains_outcome_phrase': False,
            'outcome_phrase_location': None,
            'ambiguous_outcome': False,
            'missing_information': [],
            'labeling_difficulty': 'EASY',
            'labeler_notes': f'Documento processual ({proc_type}), não é uma decisão de mérito. Não há outcome WIN/LOSS aplicável.'
        }
    }


def main():
    """Main labeling function"""
    print("Agent 8: Starting IMPROVED document labeling...")
    print("Documents: 401-450 (OFFSET 400)")

    # Load documents
    with open('/home/user/causaganha/data/temp_docs_agent_8.json', 'r', encoding='utf-8') as f:
        docs = json.load(f)

    print(f"Loaded {len(docs)} documents")

    # IDs of actual decisions
    decision_ids = ['494496961', '494496965', '494496994']

    # Label each document
    labeled_documents = []
    stats = {
        'decisions': 0,
        'procedural': 0,
        'sealed': 0,
        'high_conf': 0,
        'medium_conf': 0,
        'low_conf': 0
    }

    for i, doc in enumerate(docs, start=401):
        intimation_id = str(doc['intimation_id'])

        print(f"Labeling doc {i}/450... (intimation_id: {intimation_id})")

        # Check if it's an actual decision
        if intimation_id in decision_ids:
            labeled_doc = label_document_manual(
                i, intimation_id, doc['numero_processo'],
                doc['data_disponibilizacao'], doc['sigla_tribunal'],
                doc['nome_orgao'], doc['texto']
            )
            stats['decisions'] += 1
            if labeled_doc['outcome']['confidence'] == 'HIGH':
                stats['high_conf'] += 1
        else:
            # Check if procedural
            plain_text = strip_html(doc['texto'])
            is_proc, proc_type = is_procedural_document(plain_text)

            if is_proc:
                labeled_doc = label_procedural_document(
                    i, intimation_id, doc['numero_processo'],
                    doc['data_disponibilizacao'], doc['sigla_tribunal'],
                    doc['nome_orgao'], doc['texto'], proc_type
                )
                if proc_type == 'PROCESSO_SIGILOSO':
                    stats['sealed'] += 1
                else:
                    stats['procedural'] += 1

        labeled_documents.append(labeled_doc)

    # Build final output
    output = {
        'agent_id': 8,
        'docs_range': '401-450',
        'total_docs': len(labeled_documents),
        'labeling_date': datetime.now().date().isoformat(),
        'documents': labeled_documents,
        'summary': {
            'total_labeled': len(labeled_documents),
            'actual_decisions': stats['decisions'],
            'procedural_documents': stats['procedural'],
            'sealed_processes': stats['sealed'],
            'high_confidence': stats['high_conf'],
            'medium_confidence': stats['medium_conf'],
            'low_confidence': stats['low_conf'],
            'notes': 'Batch contains only 3 actual decisions (Sentenças). Rest are procedural orders (Atos Ordinatórios) and sealed processes.'
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
    print(f"  - Actual decisions: {stats['decisions']}")
    print(f"  - Procedural documents: {stats['procedural']}")
    print(f"  - Sealed processes: {stats['sealed']}")
    print(f"\nConfidence levels (for decisions):")
    print(f"  - High confidence: {stats['high_conf']}")
    print(f"  - Medium confidence: {stats['medium_conf']}")
    print(f"  - Low confidence: {stats['low_conf']}")
    print(f"\nOutput saved to: {output_path}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
