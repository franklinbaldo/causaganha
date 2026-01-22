#!/usr/bin/env python3
"""Query database for documents 251-300"""

import duckdb
import json

# Connect to database
conn = duckdb.connect('/home/user/causaganha/data/causaganha_real.duckdb', read_only=True)

# Query for documents 251-300 (OFFSET 250)
query = """
SELECT
    id as intimation_id,
    numero_processo,
    texto,
    data_disponibilizacao,
    sigla_tribunal,
    nome_orgao
FROM intimations
WHERE texto IS NOT NULL
ORDER BY id
LIMIT 50 OFFSET 250
"""

results = conn.execute(query).fetchall()
columns = ['intimation_id', 'numero_processo', 'texto', 'data_disponibilizacao', 'sigla_tribunal', 'nome_orgao']

# Convert to list of dicts
documents = []
for row in results:
    doc = {}
    for col, val in zip(columns, row):
        # Convert date objects to strings
        if hasattr(val, 'isoformat'):
            doc[col] = val.isoformat()
        else:
            doc[col] = val
    documents.append(doc)

conn.close()

# Output as JSON
print(json.dumps(documents, ensure_ascii=False, indent=2))
