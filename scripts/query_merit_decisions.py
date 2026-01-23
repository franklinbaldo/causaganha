#!/usr/bin/env python3
"""Query database for merit decisions using procedural filter patterns.

This script uses the procedural filter's patterns to build a SQL query
that targets merit decisions, avoiding the 85% procedural noise.
"""

import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from causaganha.config import settings


def main():
    """Query for merit decisions and count results."""
    db_path = settings.DATA_DIR / "causaganha_real.duckdb"
    db = duckdb.connect(str(db_path))

    print("🔍 Querying for Merit Decisions\n")
    print("=" * 70)

    # Query for merit decisions using filter patterns
    # Exclude: ATO ORDINATÓRIO, sealed, short procedural docs
    # Include: SENTENÇA, ACÓRDÃO, outcome phrases
    query = """
    SELECT
        id as intimation_id,
        numero_processo,
        LENGTH(texto) as text_length,
        CASE
            WHEN texto LIKE '%sigiloso%' OR texto LIKE '%segredo de justi%' THEN 'SEALED'
            WHEN texto LIKE '%ATO ORDINAT%' THEN 'PROCEDURAL'
            WHEN texto LIKE '%marcar per%cia%' OR texto LIKE '%agendar per%cia%' THEN 'PROCEDURAL'
            WHEN texto LIKE '%julgo procedente%' OR texto LIKE '%julgo improcedente%' THEN 'MERIT'
            WHEN texto LIKE '%SENTEN%A%' OR texto LIKE '%AC%RD%O%' THEN 'MERIT'
            WHEN texto LIKE '%dar provimento%' OR texto LIKE '%negar provimento%' THEN 'MERIT'
            WHEN LENGTH(texto) < 800 THEN 'PROCEDURAL_SHORT'
            ELSE 'UNKNOWN'
        END as doc_type
    FROM intimations
    WHERE texto IS NOT NULL
        AND texto NOT LIKE '%sigiloso%'
        AND texto NOT LIKE '%segredo de justi%'
        AND texto NOT LIKE '%ATO ORDINAT%'
        AND texto NOT LIKE '%marcar per%cia%'
        AND texto NOT LIKE '%agendar per%cia%'
        AND LENGTH(texto) >= 800
        AND (
            texto LIKE '%julgo procedente%'
            OR texto LIKE '%julgo improcedente%'
            OR texto LIKE '%SENTEN%A%'
            OR texto LIKE '%AC%RD%O%'
            OR texto LIKE '%dar provimento%'
            OR texto LIKE '%negar provimento%'
            OR texto LIKE '%condenar%'
            OR texto LIKE '%absolver%'
        )
    ORDER BY RANDOM()
    LIMIT 1000
    """

    print("Query filters:")
    print("  ✓ Exclude: sigiloso, ATO ORDINATÓRIO, perícia scheduling")
    print("  ✓ Exclude: Short docs (< 800 chars)")
    print("  ✓ Include: julgo procedente/improcedente")
    print("  ✓ Include: SENTENÇA, ACÓRDÃO")
    print("  ✓ Include: dar/negar provimento, condenar, absolver")
    print("  ✓ Order: RANDOM() for diversity")
    print("  ✓ Limit: 1000 documents")
    print()

    # Execute query
    print("Executing query...")
    result = db.execute(query).fetchall()

    print(f"\n✅ Found {len(result)} merit decisions\n")
    print("=" * 70)

    # Sample analysis
    if result:
        print("\n📊 Sample Results (first 10):\n")
        for i, row in enumerate(result[:10], 1):
            intimation_id, numero_processo, text_length, doc_type = row
            print(f"{i}. ID {intimation_id} - {numero_processo}")
            print(f"   Length: {text_length:,} chars | Type: {doc_type}")

        # Statistics
        avg_length = sum(r[2] for r in result) / len(result)
        print(f"\n📈 Statistics:")
        print(f"   Average length: {avg_length:,.0f} chars")
        print(f"   Min length: {min(r[2] for r in result):,} chars")
        print(f"   Max length: {max(r[2] for r in result):,} chars")

        # Save IDs for agent distribution
        output_file = settings.DATA_DIR / "merit_decision_ids.txt"
        with open(output_file, "w") as f:
            for row in result:
                f.write(f"{row[0]}\n")
        print(f"\n💾 Saved {len(result)} IDs to: {output_file}")

        # Distribution plan
        docs_per_agent = len(result) // 10
        print(f"\n📦 Distribution Plan (10 agents):")
        print(f"   Docs per agent: ~{docs_per_agent}")
        for agent_id in range(1, 11):
            start = (agent_id - 1) * docs_per_agent
            end = agent_id * docs_per_agent if agent_id < 10 else len(result)
            print(f"   Agent {agent_id}: Docs {start+1}-{end} ({end-start} docs)")

    db.close()


if __name__ == "__main__":
    main()
