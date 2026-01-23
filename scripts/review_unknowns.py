#!/usr/bin/env python3
"""Review UNKNOWN cases to find missing patterns"""

import duckdb
import json
import re

# Load results
with open('/home/user/causaganha/data/outcome_labels_agent_5.json') as f:
    results = json.load(f)

# Get UNKNOWN docs
unknowns = [doc for doc in results['documents'] if doc['outcome_normalized'] == 'UNKNOWN']
print(f"Found {len(unknowns)} UNKNOWN cases\n")

# Connect to database
db = duckdb.connect('/home/user/causaganha/data/causaganha_real.duckdb', read_only=True)

# Check first 5 unknowns
for i, doc in enumerate(unknowns[:10], 1):
    intimation_id = doc['intimation_id']

    result = db.execute(
        "SELECT texto FROM intimations WHERE id = ?",
        [intimation_id]
    ).fetchone()

    if result:
        texto = result[0]

        print(f"="*80)
        print(f"UNKNOWN #{i}: {intimation_id}")
        print(f"="*80)

        # Look for outcome-related keywords
        keywords = [
            'julgo', 'procedente', 'improcedente', 'parcialmente',
            'provimento', 'negar', 'dar', 'acordam', 'decide',
            'condenar', 'absolver', 'extinguir', 'conhecer'
        ]

        texto_lower = texto.lower()
        for keyword in keywords:
            if keyword in texto_lower:
                # Find context
                idx = texto_lower.find(keyword)
                start = max(0, idx - 50)
                end = min(len(texto), idx + 150)
                snippet = texto[start:end]
                snippet = re.sub(r'\s+', ' ', snippet)
                print(f"  [{keyword}]: ...{snippet}...")

        print()

db.close()
