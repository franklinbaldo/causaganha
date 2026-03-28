"""Test embedding storage with Ibis/DuckDB.

This script demonstrates:
1. Storing embeddings locally during processing
2. Loading cached embeddings
3. Exporting embeddings to Parquet for Internet Archive
"""

import asyncio
from pathlib import Path

import pandas as pd

from causaganha.analysis.embedding_models import JINA_V4_768, JINA_V4_1024
from causaganha.analysis.embedding_service_v2 import EmbeddingService
from causaganha.analysis.text_chunker import TextChunker
from causaganha.storage.connection import get_connection
from causaganha.storage.embedding_storage import EmbeddingStorage


async def test_embedding_storage() -> None:
    """Test the complete embedding storage workflow."""
    # Use in-memory database for testing
    con = get_connection(db_path=":memory:")

    # Create embedding storage
    storage = EmbeddingStorage(con=con)

    # Create embedding service with Jina v4

    service = await EmbeddingService.create(
        provider="jina",
        model=JINA_V4_1024,
    )

    # Simulate a legal decision (long text)
    sample_decision = (
        """
    ACÓRDÃO

    Vistos, relatados e discutidos os autos, acordam os Desembargadores da Turma Julgadora,
    por unanimidade, em DAR PROVIMENTO ao recurso de apelação interposto pela parte autora,
    para reformar a sentença de primeiro grau e julgar PROCEDENTE o pedido inicial.

    FUNDAMENTAÇÃO:

    A empresa ré deixou de cumprir com suas obrigações contratuais, causando danos materiais
    e morais ao autor. A prova dos autos demonstra inequivocamente o nexo causal entre a
    conduta da ré e os danos sofridos.

    Assim, condeno a ré ao pagamento de R$ 50.000,00 a título de danos materiais e
    R$ 30.000,00 a título de danos morais, com juros e correção monetária.

    São Paulo, 15 de janeiro de 2026.

    Desembargador João da Silva
    Relator
    """
        * 5
    )  # Repeat to make it longer

    # Generate embeddings with chunking
    embeddings = await service.embed_chunked_text(
        sample_decision,
        strategy="auto",
    )

    # Save to database

    intimation_id = 12345  # Simulated intimation ID

    # Split decision into chunks for text preview

    chunker = TextChunker(max_tokens=service.model.max_tokens)
    text_chunks = chunker.chunk_text(sample_decision, strategy="auto")

    storage.save_embeddings_batch(
        intimation_id=intimation_id,
        embeddings=embeddings,
        model=service.model,
        text_chunks=text_chunks,
    )

    # Save another intimation with different model (simulate mixed models)

    # Generate with 768D model
    service_768 = await EmbeddingService.create(
        provider="jina",
        model=JINA_V4_768,
    )

    embeddings_768 = await service_768.embed_text("Short decision text")

    storage.save_embedding(
        intimation_id=67890,
        chunk_index=0,
        embedding=embeddings_768,
        model=JINA_V4_768,
        text_preview="Short decision text",
    )

    # Load from database

    loaded = storage.load_embeddings(
        intimation_id=intimation_id,
        model=JINA_V4_1024,
    )

    if loaded:
        for _i, _emb_data in enumerate(loaded):
            pass
    else:
        pass

    # Get statistics

    stats = storage.get_stats()

    for _item in stats["by_provider"]:
        pass

    for _item in stats["by_model"]:
        pass

    # Export to Parquet

    output_dir = Path("data/exports")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export all Jina v4 1024D embeddings
    parquet_path = storage.export_to_parquet(
        output_path=output_dir / "embeddings_jina_v4_1024.parquet",
        provider="jina",
        model_name="jina-embeddings-v4",
    )

    # Read back the Parquet file to verify

    pd.read_parquet(parquet_path)

    # Example: Export for single intimation
    storage.export_to_parquet(
        output_path=output_dir / f"intimation_{intimation_id}_embeddings.parquet",
        intimation_id=intimation_id,
    )

    # Summary


if __name__ == "__main__":
    asyncio.run(test_embedding_storage())
