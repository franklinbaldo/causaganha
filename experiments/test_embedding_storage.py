"""Test embedding storage with Ibis/DuckDB.

This script demonstrates:
1. Storing embeddings locally during processing
2. Loading cached embeddings
3. Exporting embeddings to Parquet for Internet Archive
"""

import asyncio
from pathlib import Path

from causaganha.analysis.embedding_models import JINA_V4_1024
from causaganha.analysis.embedding_service_v2 import EmbeddingService
from causaganha.storage.connection import get_connection
from causaganha.storage.embedding_storage import EmbeddingStorage


async def test_embedding_storage():
    """Test the complete embedding storage workflow."""
    print("=" * 80)
    print("EMBEDDING STORAGE TEST - Ibis/DuckDB + Parquet Export")
    print("=" * 80)
    print()

    # Use in-memory database for testing
    con = get_connection(db_path=":memory:")

    # Create embedding storage
    storage = EmbeddingStorage(con=con)
    print("✅ Embedding storage initialized")
    print()

    # Create embedding service with Jina v4
    print("─" * 80)
    print("Step 1: Generate Embeddings")
    print("─" * 80)

    service = await EmbeddingService.create(
        provider="jina",
        model=JINA_V4_1024,
    )

    print(f"Provider: {service.provider_name}")
    print(f"Model: {service.model.name}")
    print(f"Dimension: {service.model.dimension}D")
    print(f"Max tokens: {service.model.max_tokens:,}")
    print()

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
    print("Generating embeddings for decision...")
    embeddings = await service.embed_chunked_text(
        sample_decision,
        strategy="auto",
    )

    print(f"✅ Generated {len(embeddings)} embedding(s)")
    print(f"   Dimension: {len(embeddings[0])}D")
    print()

    # Save to database
    print("─" * 80)
    print("Step 2: Save Embeddings to Database")
    print("─" * 80)

    intimation_id = 12345  # Simulated intimation ID

    # Split decision into chunks for text preview
    from causaganha.analysis.text_chunker import TextChunker

    chunker = TextChunker(max_tokens=service.model.max_tokens)
    text_chunks = chunker.chunk_text(sample_decision, strategy="auto")

    storage.save_embeddings_batch(
        intimation_id=intimation_id,
        embeddings=embeddings,
        model=service.model,
        text_chunks=text_chunks,
    )

    print(f"✅ Saved {len(embeddings)} embedding(s) for intimation {intimation_id}")
    print()

    # Save another intimation with different model (simulate mixed models)
    print("Saving embeddings for another decision with different dimension...")

    from causaganha.analysis.embedding_models import JINA_V4_768

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

    print("✅ Saved 768D embedding for intimation 67890")
    print()

    # Load from database
    print("─" * 80)
    print("Step 3: Load Cached Embeddings")
    print("─" * 80)

    loaded = storage.load_embeddings(
        intimation_id=intimation_id,
        model=JINA_V4_1024,
    )

    if loaded:
        print(f"✅ Loaded {len(loaded)} cached embedding(s)")
        for i, emb_data in enumerate(loaded):
            print(f"   Chunk {i}:")
            print(f"     - Dimension: {len(emb_data['embedding'])}D")
            print(f"     - Preview: {emb_data['text_preview'][:50]}...")
            print(f"     - Created: {emb_data['created_at']}")
        print()
    else:
        print("❌ Failed to load embeddings")
        print()

    # Get statistics
    print("─" * 80)
    print("Step 4: Database Statistics")
    print("─" * 80)

    stats = storage.get_stats()

    print(f"Total embeddings: {stats['total_embeddings']}")
    print(f"Unique intimations: {stats['unique_intimations']}")
    print()

    print("By provider:")
    for item in stats["by_provider"]:
        print(f"  - {item['provider']}: {item['count']} embeddings")
    print()

    print("By model:")
    for item in stats["by_model"]:
        print(
            f"  - {item['provider']}/{item['model_name']} "
            f"({item['dimension']}D): {item['count']} embeddings",
        )
    print()

    # Export to Parquet
    print("─" * 80)
    print("Step 5: Export to Parquet for Internet Archive")
    print("─" * 80)

    output_dir = Path("data/exports")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export all Jina v4 1024D embeddings
    parquet_path = storage.export_to_parquet(
        output_path=output_dir / "embeddings_jina_v4_1024.parquet",
        provider="jina",
        model_name="jina-embeddings-v4",
    )

    print(f"✅ Exported embeddings to: {parquet_path}")
    print(f"   File size: {parquet_path.stat().st_size:,} bytes")
    print()

    # Read back the Parquet file to verify
    import pandas as pd

    df = pd.read_parquet(parquet_path)
    print("Parquet file contents:")
    print(df.head())
    print()
    print(f"Columns: {list(df.columns)}")
    print(f"Rows: {len(df)}")
    print()

    # Example: Export for single intimation
    parquet_path_single = storage.export_to_parquet(
        output_path=output_dir / f"intimation_{intimation_id}_embeddings.parquet",
        intimation_id=intimation_id,
    )

    print(f"✅ Exported single intimation to: {parquet_path_single}")
    print()

    # Summary
    print("=" * 80)
    print("WORKFLOW SUMMARY")
    print("=" * 80)
    print()
    print("Complete embedding storage workflow:")
    print()
    print("1. ✅ Generate embeddings with EmbeddingService")
    print("2. ✅ Store embeddings in DuckDB via Ibis")
    print("3. ✅ Load cached embeddings (avoid regeneration)")
    print("4. ✅ Query statistics (by provider, model, dimension)")
    print("5. ✅ Export to Parquet for Internet Archive upload")
    print()
    print("Benefits:")
    print("  • Local caching reduces API costs")
    print("  • Parquet format optimized for archival storage")
    print("  • Easy to query and filter embeddings")
    print("  • Supports multiple models/dimensions in same database")
    print()


if __name__ == "__main__":
    asyncio.run(test_embedding_storage())
