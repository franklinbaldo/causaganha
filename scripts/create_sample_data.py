#!/usr/bin/env python3
"""Create sample data for testing Parquet export system."""

import sys
from datetime import datetime, timedelta
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from causaganha.v2.storage.connection import get_connection


def create_sample_data():
    """Create sample intimations and decision_analysis data."""
    con = get_connection()

    # Create sample intimations for yesterday (3 tribunals)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    tribunals = ["TJRO", "TJSP", "TJAC"]

    for tribunal in tribunals:
        for i in range(10):  # 10 intimations per tribunal
            intimation_id = int(f"{hash(tribunal + str(i)) % 1000000}")

            # Insert intimation
            con.raw_sql(f"""
                INSERT INTO intimations (
                    id, numero_processo, data_disponibilizacao, sigla_tribunal,
                    tipo_comunicacao, nome_orgao, texto, link, tipo_documento,
                    nome_classe, codigo_classe, hash, status, analyzed
                ) VALUES (
                    {intimation_id},
                    '000{i:04d}-45.2025.8.22.0001',
                    '{yesterday}',
                    '{tribunal}',
                    'Intimacao',
                    '1ª Vara Cível',
                    'Fica V. Sa. intimado para tomar ciência da sentença proferida nos autos. Advogado autor venceu.',
                    'https://example.com/doc/{intimation_id}',
                    'Sentença',
                    'Procedimento Comum Cível',
                    '7',
                    'hash_{tribunal}_{i}',
                    'A',
                    true
                )
            """)

            # Insert decision analysis
            con.raw_sql(f"""
                INSERT INTO decision_analysis (
                    intimation_id,
                    winner_lawyer_oab, winner_lawyer_state, winner_party_name,
                    loser_lawyer_oab, loser_lawyer_state, loser_party_name,
                    decision_type, outcome, judge_name, decision_reasoning,
                    confidence_score, model_used, model_provider,
                    analysis_duration_seconds, analysis_method
                ) VALUES (
                    {intimation_id},
                    '12345{i}', 'RO', 'João da Silva',
                    '98765{i}', 'RO', 'Maria dos Santos',
                    'Sentença', 'Procedente', 'Dr. Judge {i}',
                    'Análise da decisão judicial',
                    0.{85 + i}, 'gemini-2.0-flash-exp', 'google',
                    0.5, 'hybrid'
                )
            """)

    print("✅ Created sample data:")
    print(f"   - Date: {yesterday}")
    print(f"   - Tribunals: {', '.join(tribunals)}")
    print("   - Intimations per tribunal: 10")
    print(f"   - Total intimations: {len(tribunals) * 10}")
    print(f"   - Total analyses: {len(tribunals) * 10}")

    # Verify
    result = con.raw_sql(f"""
        SELECT
            sigla_tribunal,
            COUNT(*) as count
        FROM intimations
        WHERE data_disponibilizacao = '{yesterday}'
        GROUP BY sigla_tribunal
    """).fetchall()

    print("\nVerification:")
    for row in result:
        print(f"   - {row[0]}: {row[1]} intimations")


if __name__ == "__main__":
    create_sample_data()
