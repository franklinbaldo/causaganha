#!/usr/bin/env python3
import duckdb
import json

# Connect to database
conn = duckdb.connect('/home/user/causaganha/data/causaganha_real.duckdb', read_only=True)

# Query documents 451-500
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
LIMIT 50 OFFSET 450
"""

results = conn.execute(query).fetchall()
columns = ['intimation_id', 'numero_processo', 'texto', 'data_disponibilizacao', 'sigla_tribunal', 'nome_orgao']

# Convert to list of dicts
documents = []
for row in results:
    doc = dict(zip(columns, row))
    # Convert date to string
    if doc.get('data_disponibilizacao'):
        doc['data_disponibilizacao'] = str(doc['data_disponibilizacao'])
    documents.append(doc)

# Save to JSON for processing
with open('/home/user/causaganha/data/agent_9_raw.json', 'w', encoding='utf-8') as f:
    json.dump(documents, f, ensure_ascii=False, indent=2)

print(f"Fetched {len(documents)} documents")
print(f"First doc ID: {documents[0]['intimation_id']}")
print(f"Last doc ID: {documents[-1]['intimation_id']}")
