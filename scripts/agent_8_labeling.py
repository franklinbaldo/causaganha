#!/usr/bin/env python3
"""
Agent 8: Outcome-Only Labeling for Lines 701-800
Extracts ONLY outcomes (WIN/LOSS/PARTIAL) from merit decisions
"""

import duckdb
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple

# Document IDs for Agent 8 (lines 701-800)
MY_IDS = [
    "507618488", "498876842", "505366769", "499129499", "502107097",
    "498325831", "507666340", "507772485", "494875305", "499028682",
    "498342839", "496018347", "495748148", "504170129", "495085396",
    "504123339", "494938675", "496473635", "498335270", "499262053",
    "498319178", "505206285", "499329107", "494773170", "501804150",
    "498311830", "507425982", "499738084", "495838792", "498340603",
    "501589960", "498340769", "496902754", "495675725", "494939486",
    "495467124", "495529913", "498319346", "499263765", "497810841",
    "498937682", "507772219", "502325776", "503283708", "495626907",
    "495087515", "494734044", "494939174", "506048182", "495464705",
    "498054358", "495086845", "505253660", "501374959", "504917354",
    "495484774", "498791704", "498343151", "496663773", "496697447",
    "505186121", "507770591", "500040184", "495243806", "503256408",
    "502328024", "498319791", "495128826", "507781100", "501550841",
    "495465782", "496477612", "507724889", "497615986", "498194377",
    "498336154", "498368612", "495087802", "499388866", "498331330",
    "498331361", "505148429", "502213600", "495583657", "506335564",
    "498342989", "500420165", "495561731", "498876783", "495156370",
    "495604939", "496562406", "498320490", "501305940", "495384864",
    "496976434", "498343384", "498058586", "502387637"
]

# Outcome patterns (case-insensitive)
PATTERNS = {
    'WIN': [
        r'julgo\s+procedente(?!\s+em\s+parte)',
        r'dar\s+provimento\s+(?:à|ao)\s+(?:apelação|recurso)(?!\s+do\s+(?:réu|recorrido|INSS|instituto))',
        r'negar\s+provimento\s+(?:à|ao)\s+(?:apelação|recurso)\s+(?:do|da)\s+(?:réu|recorrido|INSS|instituto)',
        r'condenar\s+o\s+réu',
        r'procedência\s+do\s+pedido',
        r'acolho\s+o\s+pedido',
    ],
    'LOSS': [
        r'julgo\s+improcedente',
        r'dar\s+provimento\s+(?:à|ao)\s+(?:apelação|recurso)\s+(?:do|da)\s+(?:réu|recorrido|INSS|instituto)',
        r'negar\s+provimento\s+(?:à|ao)\s+(?:apelação|recurso)(?!\s+do\s+(?:réu|recorrido|INSS|instituto))',
        r'absolver\s+o\s+réu',
        r'improcedência\s+do\s+pedido',
        r'rejeito\s+o\s+pedido',
    ],
    'PARTIAL': [
        r'julgo\s+parcialmente\s+procedente',
        r'procedente\s+em\s+parte',
        r'acolho\s+parcialmente',
        r'dar\s+parcial\s+provimento',
    ],
    'UNKNOWN': [
        r'extingo\s+(?:o\s+processo\s+)?sem\s+(?:resolução\s+de?\s+)?mérito',
        r'não\s+conhec(?:o|er)',
        r'declaro\s+a\s+extinção',
    ]
}


def extract_outcome(texto: str, intimation_id: str) -> Dict:
    """Extract outcome from decision text"""
    texto_lower = texto.lower()

    # Try each pattern category
    for outcome_type, patterns in PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, texto_lower, re.IGNORECASE)
            if match:
                # Extract phrase with context (max 100 chars)
                start = max(0, match.start() - 20)
                end = min(len(texto), match.end() + 80)
                phrase = texto[start:end].strip()

                # Clean up phrase
                phrase = ' '.join(phrase.split())  # Normalize whitespace
                if len(phrase) > 100:
                    phrase = phrase[:97] + "..."

                # Determine confidence
                if outcome_type == 'UNKNOWN':
                    confidence = 'HIGH'
                elif 'julgo' in texto_lower or 'provimento' in texto_lower:
                    confidence = 'HIGH'
                else:
                    confidence = 'MEDIUM'

                return {
                    'outcome_normalized': outcome_type,
                    'confidence': confidence,
                    'outcome_phrase': phrase
                }

    # No pattern matched - mark as UNKNOWN with LOW confidence
    return {
        'outcome_normalized': 'UNKNOWN',
        'confidence': 'LOW',
        'outcome_phrase': 'Nenhum padrão claro de resultado identificado'
    }


def process_documents() -> Dict:
    """Process all 100 documents and extract outcomes"""

    print(f"🤖 Agent 8: Processing documents 701-800...")
    print(f"📊 Total documents: {len(MY_IDS)}")

    # Connect to database (read-only mode)
    db = duckdb.connect('/home/user/causaganha/data/causaganha_real.duckdb', read_only=True)

    documents = []
    stats = {
        'total_labeled': 0,
        'high_confidence': 0,
        'medium_confidence': 0,
        'low_confidence': 0,
        'outcome_distribution': {
            'WIN': 0,
            'LOSS': 0,
            'PARTIAL': 0,
            'UNKNOWN': 0
        }
    }

    # Process each document
    for idx, intimation_id in enumerate(MY_IDS, start=1):
        print(f"Processing {idx}/100: {intimation_id}...", end=' ')

        try:
            # Query database
            result = db.execute(
                "SELECT id, numero_processo, texto FROM intimations WHERE id = ?",
                [intimation_id]
            ).fetchone()

            if not result:
                print(f"❌ Not found!")
                continue

            doc_id, numero_processo, texto = result

            # Extract outcome
            outcome = extract_outcome(texto, intimation_id)

            # Build document entry
            doc_entry = {
                'intimation_id': intimation_id,
                'numero_processo': numero_processo,
                **outcome
            }

            documents.append(doc_entry)

            # Update statistics
            stats['total_labeled'] += 1
            stats[f'{outcome["confidence"].lower()}_confidence'] += 1
            stats['outcome_distribution'][outcome['outcome_normalized']] += 1

            print(f"✅ {outcome['outcome_normalized']} ({outcome['confidence']})")

        except Exception as e:
            print(f"❌ Error: {e}")
            continue

    db.close()

    # Build final output
    output = {
        'agent_id': 8,
        'docs_range': '701-800',
        'total_docs': 100,
        'labeling_date': datetime.now().strftime('%Y-%m-%d'),
        'method': 'OUTCOME_ONLY',
        'documents': documents,
        'summary': stats
    }

    return output


def main():
    """Main execution"""

    # Process documents
    result = process_documents()

    # Save to JSON
    output_path = '/home/user/causaganha/data/outcome_labels_agent_8.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Labeling complete!")
    print(f"📁 Output saved to: {output_path}")
    print(f"\n📊 Summary:")
    print(f"   Total labeled: {result['summary']['total_labeled']}/100")
    print(f"   High confidence: {result['summary']['high_confidence']}")
    print(f"   Medium confidence: {result['summary']['medium_confidence']}")
    print(f"   Low confidence: {result['summary']['low_confidence']}")
    print(f"\n🎯 Outcome Distribution:")
    for outcome, count in result['summary']['outcome_distribution'].items():
        print(f"   {outcome}: {count}")


if __name__ == '__main__':
    main()
