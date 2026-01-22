#!/usr/bin/env python3
"""
Fix lawyer extraction in Agent 5 labeling
"""

import json
import re
from html import unescape

def clean_html(text: str) -> str:
    """Remove HTML tags and clean text"""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_lawyers_fixed(text: str) -> dict:
    """Extract lawyer information with improved regex"""
    lawyers_list = []

    # Much better pattern that captures full names and OAB
    # Matches: ADVOGADO(A) : RUAN CARLOS ROCHA SILVA (OAB PR094069)
    lawyer_pattern = r'ADVOGAD[OA](?:\(A\))?\s*:\s*([A-ZÀ-ÜÇ][A-ZÀ-ÜÇ\s\-\.]+?)(?:\s*\(\s*OAB\s+([A-Z]{2})\s*(\d+)\s*\))?(?=\s+(?:ADVOGAD|ATO|DESPACHO|</|$))'

    matches = re.finditer(lawyer_pattern, text, re.IGNORECASE | re.MULTILINE)
    seen_lawyers = set()

    for match in matches:
        name = match.group(1).strip().upper()
        name = re.sub(r'\s+', ' ', name)
        oab_uf = match.group(2).upper() if match.group(2) else None
        oab_numero = match.group(3) if match.group(3) else None

        # Skip if this is not actually a lawyer name (false positive)
        if len(name) < 5 or name.startswith('O PERITO') or name.startswith('PERITO'):
            continue

        # Create unique key
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

    # Check for public defenders
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

def main():
    """Fix lawyer extraction in existing labeling"""
    print("Fixing lawyer extraction...")

    # Load original documents
    with open('/tmp/agent_5_docs.json', 'r') as f:
        original_docs = json.load(f)

    # Load labeled data
    with open('/home/user/causaganha/data/ground_truth_rich_agent_5.json', 'r') as f:
        labeled_data = json.load(f)

    # Update lawyer information for each document
    fixed_count = 0
    for i, labeled_doc in enumerate(labeled_data['documents']):
        original_text = original_docs[i]['texto']
        clean_text = clean_html(original_text)

        # Re-extract lawyers with fixed pattern
        lawyers_fixed = extract_lawyers_fixed(clean_text)

        # Update only if we got better results
        old_lawyers_count = len(labeled_doc['lawyers']['lawyers'])
        new_lawyers_count = len(lawyers_fixed['lawyers'])

        # Always update to use the fixed extraction
        labeled_doc['lawyers'] = lawyers_fixed

        # Set representing field based on position (simple heuristic for procedural docs)
        author = labeled_doc['parties']['simplified']['author']
        defendant = labeled_doc['parties']['simplified']['defendant']

        for j, lawyer in enumerate(labeled_doc['lawyers']['lawyers']):
            if lawyer.get('representing') is None and not lawyer.get('is_public_defender'):
                # First lawyer represents author
                if j == 0 and author:
                    lawyer['representing'] = 'AUTOR'
                    lawyer['party_name'] = author
                elif defendant:
                    lawyer['representing'] = 'REU'
                    lawyer['party_name'] = defendant

        if new_lawyers_count >= old_lawyers_count:
            fixed_count += 1
            if new_lawyers_count > old_lawyers_count:
                print(f"  Doc {labeled_doc['doc_id']}: {old_lawyers_count} → {new_lawyers_count} lawyers")

    # Save fixed version
    output_file = '/home/user/causaganha/data/ground_truth_rich_agent_5.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(labeled_data, f, ensure_ascii=False, indent=2)

    print(f"\\nFixed {fixed_count}/50 documents")
    print(f"Saved to: {output_file}")

    # Show stats
    docs_with_lawyers = sum(1 for d in labeled_data['documents'] if len(d['lawyers']['lawyers']) > 0)
    docs_with_oab = sum(1 for d in labeled_data['documents'] if any(l.get('oab_numero') for l in d['lawyers']['lawyers']))

    print(f"\\nFinal stats:")
    print(f"  Documents with lawyers: {docs_with_lawyers}/50")
    print(f"  Documents with OAB numbers: {docs_with_oab}/50")

if __name__ == "__main__":
    main()
