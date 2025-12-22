#!/usr/bin/env python3
"""
Script to seed the test database with sample data.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import date
import structlog

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from causaganha.domain.models import Intimation, Lawyer, Party
from causaganha.storage.connection import get_connection
from causaganha.storage.repository import IntimationRepository
from causaganha.storage.schema import create_schema

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

async def main():
    parser = argparse.ArgumentParser(description="Seed Test Database")
    parser.add_argument("--db", type=str, default="test_collection.duckdb", help="Path to DuckDB file")
    args = parser.parse_args()

    db_path = Path(args.db)
    logger.info("setup", db=str(db_path))

    con = get_connection(str(db_path))
    create_schema(con)
    repository = IntimationRepository(con)

    # Sample Data
    intimations = [
        Intimation(
            id=1001,
            numero_processo="0001001-00.2024.8.22.0001",
            data_disponibilizacao=date(2024, 1, 1),
            sigla_tribunal="TJRO",
            tipo_comunicacao="INTIMAÇÃO",
            nome_orgao="1ª Vara Cível de Porto Velho",
            texto="Intimação para manifestação sobre laudo pericial.",
            link="https://example.com/doc1.pdf", # Dummy link
            tipo_documento="Despacho",
            nome_classe="Procedimento Comum",
            hash="hash1001",
            status="ATIVO",
            advogados=[
                Lawyer(id=1, nome="Advogado A", numero_oab="1234", uf_oab="RO"),
                Lawyer(id=2, nome="Advogado B", numero_oab="5678", uf_oab="RO")
            ],
            partes=[
                Party(nome="Autor X", polo="A"),
                Party(nome="Réu Y", polo="P")
            ]
        ),
        Intimation(
            id=1002,
            numero_processo="0001002-00.2024.8.22.0001",
            data_disponibilizacao=date(2024, 1, 2),
            sigla_tribunal="TJRO",
            tipo_comunicacao="INTIMAÇÃO DE ACÓRDÃO",
            nome_orgao="2ª Câmara Cível",
            texto="Acórdão negando provimento ao recurso.",
            link="https://example.com/doc2.pdf", # Dummy link
            tipo_documento="Acórdão",
            nome_classe="Apelação",
            hash="hash1002",
            status="ATIVO",
            advogados=[
                Lawyer(id=1, nome="Advogado A", numero_oab="1234", uf_oab="RO"),
                Lawyer(id=3, nome="Advogado C", numero_oab="9012", uf_oab="RO")
            ],
            partes=[
                Party(nome="Autor X", polo="A"),
                Party(nome="Réu Z", polo="P")
            ]
        ),
        Intimation(
            id=1003,
            numero_processo="0001003-00.2024.8.22.0001",
            data_disponibilizacao=date(2024, 1, 3),
            sigla_tribunal="TJRO",
            tipo_comunicacao="INTIMAÇÃO",
            nome_orgao="Juizado Especial",
            texto="Sentença de improcedência.",
            link=None, # No link
            tipo_documento="Sentença",
            nome_classe="Procedimento do Juizado",
            hash="hash1003",
            status="ATIVO",
            advogados=[
                Lawyer(id=4, nome="Advogado D", numero_oab="3456", uf_oab="RO")
            ],
            partes=[]
        )
    ]

    logger.info("seeding", count=len(intimations))
    await repository.store_intimations(intimations)
    logger.info("seed_complete")

    # Verify
    t = con.table("intimations")
    count = t.count().execute()
    logger.info("verification", count=count)

if __name__ == "__main__":
    asyncio.run(main())
