#!/usr/bin/env python3
"""Generate synthetic test data for embedding quality benchmark.

Creates realistic Portuguese legal text for testing when real PJe data is not available.
"""

import random
from pathlib import Path

import duckdb
import structlog

from causaganha.config import settings


logger = structlog.get_logger()

# Sample legal text templates (Brazilian Portuguese)
DECISION_TEMPLATES = {
    "procedente": [
        "Vistos, relatados e discutidos estes autos, ACORDA a Câmara, por unanimidade, em DAR PROVIMENTO ao recurso para JULGAR PROCEDENTE o pedido inicial, condenando o réu ao pagamento de danos morais no valor de R$ {valor}, corrigido monetariamente.",
        "Trata-se de apelação interposta contra sentença que julgou procedente o pedido. Razão assiste ao apelado. A sentença merece ser mantida por seus próprios fundamentos. NEGO PROVIMENTO ao recurso.",
        "O juiz a quo julgou PROCEDENTE o pedido inicial, condenando a ré ao pagamento de indenização por danos materiais. Mantenho a sentença. Recurso improvido.",
    ],
    "improcedente": [
        "Vistos. JULGO IMPROCEDENTE o pedido inicial, com resolução de mérito nos termos do art. 487, I do CPC. Condeno o autor ao pagamento de custas e honorários advocatícios.",
        "Trata-se de ação de indenização por danos morais. Não restou demonstrado o nexo causal. JULGO IMPROCEDENTE o pedido, extinguindo o processo com resolução de mérito.",
        "A pretensão autoral não merece acolhimento. Ausentes os requisitos da responsabilidade civil. Sentença de IMPROCEDÊNCIA mantida. Recurso desprovido.",
    ],
    "parcial": [
        "JULGO PARCIALMENTE PROCEDENTE o pedido para condenar o réu ao pagamento de R$ {valor}, inferior ao pleiteado. Honorários reciprocamente compensados.",
        "A ação é PARCIALMENTE PROCEDENTE. Defiro o pedido de danos materiais mas nego os danos morais por ausência de provas. Sucumbência recíproca.",
    ],
}

OUTCOME_TEMPLATES = {
    "provido": [
        "DOU PROVIMENTO ao recurso de apelação para reformar a sentença e julgar procedente o pedido inicial.",
        "Recurso PROVIDO. Sentença reformada por seus próprios fundamentos.",
        "PROVEJO o recurso para restabelecer a sentença de primeiro grau.",
    ],
    "improvido": [
        "NEGO PROVIMENTO ao recurso. Sentença mantida por seus próprios fundamentos.",
        "Recurso IMPROVIDO. A decisão recorrida não merece reforma.",
        "NEGO PROVIMENTO à apelação. Mantenho a sentença pelos fundamentos já expostos.",
    ],
    "parcial_provimento": [
        "DOU PARCIAL PROVIMENTO ao recurso para reduzir o valor da indenização.",
        "Recurso PARCIALMENTE PROVIDO. Reforma parcial da sentença.",
    ],
}

DOCUMENT_CLASSES = [
    "Apelação Cível",
    "Recurso Inominado",
    "Agravo de Instrumento",
    "Embargos de Declaração",
    "Recurso Especial",
]

TRIBUNALS = ["TJRO", "TJSP", "TJRJ", "TJMG", "TJAC"]


def generate_legal_text(
    decision_type: str,
    outcome: str | None = None,
) -> str:
    """Generate realistic legal text.

    Args:
        decision_type: Type of decision (procedente, improcedente, parcial)
        outcome: Outcome if appeal (provido, improvido, parcial_provimento)

    Returns:
        Legal text in Portuguese.
    """
    base_template = random.choice(DECISION_TEMPLATES[decision_type])

    # Add valor if template has placeholder
    if "{valor}" in base_template:
        valor = random.randint(5000, 100000)
        base_template = base_template.format(valor=f"{valor:,.2f}")

    # Add outcome text if provided
    if outcome and outcome in OUTCOME_TEMPLATES:
        outcome_text = random.choice(OUTCOME_TEMPLATES[outcome])
        text = f"{base_template} {outcome_text}"
    else:
        text = base_template

    # Add some case context
    context = [
        f"Processo nº {random.randint(1000000, 9999999)}-{random.randint(10,99)}.{random.randint(2020,2025)}.8.22.0001",
        f"Relator: Des. {random.choice(['José Silva', 'Maria Santos', 'João Oliveira', 'Ana Costa'])}",
        "Ementa: " + text[:100] + "...",
    ]

    full_text = "\n\n".join(context) + "\n\n" + text

    return full_text


def create_test_database(
    db_path: Path,
    num_documents: int = 200,
) -> None:
    """Create test database with synthetic legal documents.

    Args:
        db_path: Path to DuckDB database file.
        num_documents: Number of documents to generate.
    """
    logger.info("creating_test_database", path=str(db_path), num_documents=num_documents)

    # Create database directory if needed
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(db_path))

    # Read schema file
    schema_file = Path(__file__).parent.parent / "src/causaganha/v2/storage/schema.sql"
    if schema_file.exists():
        with schema_file.open() as f:
            schema_sql = f.read()
        conn.execute(schema_sql)
        logger.info("schema_created")

    # Generate documents with balanced distribution
    documents = []
    analyses = []

    # Distribution: 40% procedente, 30% improcedente, 30% parcial
    decision_distribution = ["procedente"] * 80 + ["improcedente"] * 60 + ["parcial"] * 60

    for i in range(num_documents):
        intimation_id = i + 1
        decision_type = random.choice(decision_distribution)

        # Randomly decide if it's an appeal (50% chance)
        is_appeal = random.random() < 0.5

        if is_appeal:
            if decision_type == "procedente":
                outcome = random.choice(["provido", "improvido"])
            elif decision_type == "improcedente":
                outcome = random.choice(["provido", "improvido"])
            else:
                outcome = "parcial_provimento"
        else:
            outcome = None

        texto = generate_legal_text(decision_type, outcome)

        # Create intimation record
        documents.append(
            (
                intimation_id,
                f"0000{intimation_id}-00.2024.8.22.0001",  # numero_processo
                f"0000{intimation_id}-00.2024.8.22.0001",  # numeroprocessocommascara
                f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",  # data_disponibilizacao
                random.choice(TRIBUNALS),  # sigla_tribunal
                random.randint(100, 999),  # id_orgao
                "Intimação Eletrônica",  # tipo_comunicacao
                "Vara Cível",  # nome_orgao
                texto,  # texto
                f"https://example.com/doc/{intimation_id}",  # link
                "Sentença" if not is_appeal else "Acórdão",  # tipo_documento
                random.choice(DOCUMENT_CLASSES),  # nome_classe
                "100",  # codigo_classe
                f"hash_{intimation_id}",  # hash
                "A",  # status
                None,  # ia_url
                True,  # analyzed
                None,  # analysis_attempted_at
                None,  # analysis_error
                "2024-01-01 00:00:00",  # analyzed_at
                "2024-01-01 00:00:00",  # created_at
                "2024-01-01 00:00:00",  # updated_at
            )
        )

        # Create analysis record (gen_random_uuid() will generate id automatically)
        analyses.append(
            (
                intimation_id,  # intimation_id
                f"{random.randint(100000,999999)}",  # winner_lawyer_oab
                random.choice(["RO", "SP", "RJ", "MG"]),  # winner_lawyer_state
                random.choice(["João Silva", "Maria Santos", "José Oliveira"]),  # winner_party_name
                f"{random.randint(100000,999999)}",  # loser_lawyer_oab
                random.choice(["RO", "SP", "RJ", "MG"]),  # loser_lawyer_state
                random.choice(["Pedro Costa", "Ana Lima", "Carlos Souza"]),  # loser_party_name
                decision_type,  # decision_type
                outcome,  # outcome
                random.choice(["José Silva", "Maria Santos", "João Oliveira"]),  # judge_name
                "Fundamentação da decisão...",  # decision_reasoning
                random.uniform(0.7, 0.95),  # confidence_score
                "gemini-1.5-flash",  # model_used
                "google",  # model_provider
                random.uniform(1.0, 5.0),  # analysis_duration_seconds
                "llm",  # analysis_method
                None,  # rag_confidence
                None,  # rag_votes_json
                "2024-01-01 00:00:00",  # created_at
                False,  # rated
                None,  # rated_at
            )
        )

    # Insert data
    conn.executemany(
        """
        INSERT INTO intimations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        documents,
    )

    conn.executemany(
        """
        INSERT INTO decision_analysis (
            intimation_id, winner_lawyer_oab, winner_lawyer_state, winner_party_name,
            loser_lawyer_oab, loser_lawyer_state, loser_party_name, decision_type,
            outcome, judge_name, decision_reasoning, confidence_score, model_used,
            model_provider, analysis_duration_seconds, analysis_method, rag_confidence,
            rag_votes_json, created_at, rated, rated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        analyses,
    )

    conn.close()

    logger.info(
        "test_database_created",
        documents=len(documents),
        analyses=len(analyses),
    )


if __name__ == "__main__":
    import sys

    num_docs = int(sys.argv[1]) if len(sys.argv) > 1 else 200

    db_path = settings.DATA_DIR / "causaganha_test.duckdb"

    print(f"Creating test database with {num_docs} documents...")
    print(f"Database: {db_path}")

    create_test_database(db_path, num_docs)

    print(f"✓ Test database created: {db_path}")
    print(f"\nRun quality benchmark with:")
    print(f"  uv run python scripts/benchmark_embedding_quality.py --db {db_path}")
